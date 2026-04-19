from pyrogram import Client, filters
from pyrogram.errors import FloodWait, ChannelPrivate, ChatAdminRequired
from collections import deque
import asyncio
import os
import json
import time
from flask import Flask
from threading import Thread

print("🚀 BOT STARTING...")

# ─────────────────────────────────────────
# 🔐 ENV
# ─────────────────────────────────────────
api_id       = os.getenv("API_ID")
api_hash     = os.getenv("API_HASH")
string_session = os.getenv("STRING_SESSION")

if not all([api_id, api_hash, string_session]):
    print("❌ ENV VARIABLES MISSING"); exit()

api_id = int(api_id)

# ─────────────────────────────────────────
# ⚙️ CONFIG — sab ek jagah
# ─────────────────────────────────────────
SOURCES = [
    -1001714047949,
    -1001404064358,
    -1001659536566,
    -1001153554563,
    -1001677474141,
    -1001686703979,
    -1001387115878,
    -1001315464303,
    -1001707571730,
    -1001312563683,
]
TARGET          = -1003817655107
LAST_IDS_FILE   = "/tmp/last_ids.json"
FWD_IDS_FILE    = "/tmp/forwarded_ids.json"
POLL_INTERVAL   = 15    # sec between full cycles
POLL_LIMIT      = 20    # msgs fetched per channel
MAX_FLOOD_WAIT  = 60    # FloodWait cap (sec)
MAX_ERRORS      = 5     # errors before pause
PAUSE_DURATION  = 60    # pause length (sec)
SAVE_EVERY      = 5     # batch: save after N forwards
CH_SLEEP        = 0.8   # sec between channels in poll
DEQUE_SIZE      = 2000  # forwarded IDs memory

# ─────────────────────────────────────────
# 📦 STATE
# ─────────────────────────────────────────
app = Client("my_account", api_id=api_id,
             api_hash=api_hash, session_string=string_session)

channel_status  = {str(s): "🟡 Wait"   for s in SOURCES}
error_count     = {str(s): 0           for s in SOURCES}
disabled_until: dict = {}
last_ids: dict       = {}

fwd_deque: deque = deque(maxlen=DEQUE_SIZE)
fwd_set:   set   = set()

forward_lock  = asyncio.Lock()
pending_saves = 0          # unsaved forward counter

# ─────────────────────────────────────────
# 🌐 FLASK
# ─────────────────────────────────────────
web = Flask(__name__)

@web.route("/")
def home(): return "✅ Bot running"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web.run(host="0.0.0.0", port=port, use_reloader=False)

# ─────────────────────────────────────────
# 💾 DISK HELPERS
# ─────────────────────────────────────────
def load_last_ids() -> dict:
    if os.path.exists(LAST_IDS_FILE):
        with open(LAST_IDS_FILE) as f:
            data = json.load(f)
        for s in SOURCES:
            data.setdefault(str(s), 0)
        return data
    return {str(s): 0 for s in SOURCES}

def _write_last_ids():
    with open(LAST_IDS_FILE, "w") as f:
        json.dump(last_ids, f)

def _write_fwd_ids():
    with open(FWD_IDS_FILE, "w") as f:
        json.dump(list(fwd_deque), f)

def save_all():
    _write_last_ids()
    _write_fwd_ids()

def load_fwd_ids():
    if os.path.exists(FWD_IDS_FILE):
        with open(FWD_IDS_FILE) as f:
            data = json.load(f)
        d = deque(data, maxlen=DEQUE_SIZE)
        return d, set(d)
    return deque(maxlen=DEQUE_SIZE), set()

# ─────────────────────────────────────────
# 🔖 TRACK HELPERS
# ─────────────────────────────────────────
def track(key: str):
    """Deque+set sync. Auto-evicts oldest when full."""
    if len(fwd_deque) == fwd_deque.maxlen:
        fwd_set.discard(fwd_deque[0])
    fwd_deque.append(key)
    fwd_set.add(key)

def seen(key: str) -> bool:
    return key in fwd_set

def maybe_save():
    """Batch disk writes — save every SAVE_EVERY forwards."""
    global pending_saves
    pending_saves += 1
    if pending_saves >= SAVE_EVERY:
        save_all()
        pending_saves = 0

# ─────────────────────────────────────────
# 📤 SAFE FORWARD
# ─────────────────────────────────────────
async def safe_forward(source: int, msg_id: int) -> bool:
    for attempt in range(3):
        try:
            await app.copy_message(TARGET, source, msg_id)
            return True
        except FloodWait as e:
            if e.value > MAX_FLOOD_WAIT:
                print(f"⚠️ FloodWait {e.value}s > cap — skip {msg_id}")
                return False
            print(f"⏳ FloodWait {e.value}s...")
            await asyncio.sleep(e.value)
        except (ChannelPrivate, ChatAdminRequired) as e:
            print(f"🚫 {source}: {e}")
            return False
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
            else:
                print(f"❌ Forward failed {source}→{msg_id}: {e}")
    return False

# ─────────────────────────────────────────
# ⚡ EVENT HANDLER — primary (real-time)
# ─────────────────────────────────────────
@app.on_message(filters.chat(SOURCES))
async def on_new_message(client, message):
    source  = message.chat.id
    msg_key = f"{source}_{message.id}"

    async with forward_lock:
        if seen(msg_key):
            return

        ok = await safe_forward(source, message.id)

        if ok:
            track(msg_key)
            last_ids[str(source)] = max(last_ids.get(str(source), 0), message.id)
            maybe_save()
            channel_status[str(source)] = f"⚡ {time.strftime('%H:%M:%S')}"
            print(f"⚡ {source} → {message.id}")

# ─────────────────────────────────────────
# 🔄 POLL LOOP — backup (catches missed msgs)
# ─────────────────────────────────────────
async def poll_loop():
    global pending_saves
    print("🔄 Poll loop running")

    while True:
        cycle_start = time.time()

        for source in SOURCES:
            key = str(source)

            # ── Pause / resume ──
            if error_count[key] >= MAX_ERRORS:
                if key not in disabled_until:
                    disabled_until[key] = time.time() + PAUSE_DURATION
                    channel_status[key] = "⛔ Paused"
                    print(f"⛔ {source} paused {PAUSE_DURATION}s")

            if key in disabled_until:
                if time.time() < disabled_until[key]:
                    continue
                del disabled_until[key]
                error_count[key] = 0
                channel_status[key] = "🟡 Resumed"
                print(f"🔄 {source} resumed")

            # ── First run baseline ──
            if last_ids[key] == 0:
                try:
                    async for msg in app.get_chat_history(source, limit=1):
                        last_ids[key] = msg.id
                        track(f"{source}_{msg.id}")
                    save_all()
                    print(f"⏩ Baseline {source} → {last_ids[key]}")
                except Exception as e:
                    print(f"❌ Baseline {source}: {e}")
                continue

            # ── Fetch new messages ──
            try:
                new_msgs = []
                async for msg in app.get_chat_history(source, limit=POLL_LIMIT):
                    if msg.id <= last_ids[key]:
                        break           # newest-first — stop at first old msg
                    new_msgs.append(msg)

                error_count[key] = 0

                for msg in reversed(new_msgs):  # oldest → newest
                    msg_key = f"{source}_{msg.id}"

                    async with forward_lock:
                        if seen(msg_key):
                            last_ids[key] = max(last_ids[key], msg.id)
                            continue

                        ok = await safe_forward(source, msg.id)

                        if ok:
                            last_ids[key] = msg.id
                            track(msg_key)
                            maybe_save()
                            channel_status[key] = f"🟢 {time.strftime('%H:%M:%S')}"
                            print(f"🟢 {source} → {msg.id}")
                        else:
                            channel_status[key] = "🔴 Failed"

            except ChannelPrivate:
                channel_status[key] = "🚫 Private"
            except Exception as e:
                error_count[key] += 1
                channel_status[key] = f"🔴 Err {error_count[key]}/{MAX_ERRORS}"
                print(f"❌ {source} ({error_count[key]}): {e}")

            await asyncio.sleep(CH_SLEEP)

        # ── Cycle end ──
        save_all()
        pending_saves = 0

        elapsed = time.time() - cycle_start
        print(f"\n📊 [{time.strftime('%H:%M:%S')}] cycle={elapsed:.1f}s")
        for src, st in channel_status.items():
            print(f"  {src} → {st}")

        # Remaining wait — agar cycle ne time khaya toh less sleep
        wait = max(0, POLL_INTERVAL - elapsed)
        await asyncio.sleep(wait)

# ─────────────────────────────────────────
# 🚀 RUN BOT
# ─────────────────────────────────────────
async def run_bot():
    global fwd_deque, fwd_set, last_ids, pending_saves

    fwd_deque, fwd_set = load_fwd_ids()
    last_ids           = load_last_ids()
    pending_saves      = 0
    disabled_until.clear()
    for k in error_count: error_count[k] = 0

    print(f"📋 {len(fwd_deque)} IDs loaded from disk")

    await app.start()
    print("✅ Login OK")

    try:
        await app.send_message("me", "✅ BOT STARTED")
    except Exception:
        pass

    # Parallel channel access check (faster startup)
    async def check(source):
        key = str(source)
        try:
            await app.get_chat(source)
            channel_status[key] = "✅ OK"
        except Exception as e:
            channel_status[key] = "🔴 Error"
            print(f"❌ {source}: {e}")

    print("🔍 Checking channels...")
    await asyncio.gather(*[check(s) for s in SOURCES])
    print("✅ Channel check done\n")

    await poll_loop()

# ─────────────────────────────────────────
# ♻️ AUTO RESTART
# ─────────────────────────────────────────
async def main():
    while True:
        try:
            await run_bot()
        except Exception as e:
            print(f"❌ CRASH: {e}")
            try: await app.stop()
            except Exception: pass
            save_all()
            print("🔄 Restart in 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
