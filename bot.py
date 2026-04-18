from pyrogram import Client
from pyrogram.errors import FloodWait
import asyncio
import os
import json
import time
from flask import Flask
from threading import Thread

print("🚀 FILE STARTED")

# 🔐 ENV VARIABLES
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
string_session = os.getenv("STRING_SESSION")

if not api_id or not api_hash or not string_session:
    print("❌ ENV VARIABLES MISSING")
    exit()

api_id = int(api_id)

# 🤖 TELEGRAM CLIENT
app = Client(
    "my_account",
    api_id=api_id,
    api_hash=api_hash,
    session_string=string_session
)

# 🌐 FLASK SERVER
web = Flask(__name__)

@web.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    print("🌐 Flask started on port", port)
    web.run(host="0.0.0.0", port=port)

# 🔥 SOURCE CHANNELS (10 TOTAL)
SOURCES = [
    -1001714047949,   # purana 1
    -1001404064358,   # purana 2
    -1001659536566,   # purana 3
    -1001153554563,   # purana 4
    -1001677474141,   # purana 5
    -1001686703979,   # naya 1 ✅
    -1001387115878,   # naya 2 ✅
    -1001315464303,   # naya 3 ✅
    -1001707571730,   # naya 4 ✅
    -1001312563683    # naya 5 ✅
]

# 🎯 TARGET CHANNEL
TARGET = -1003817655107

# 💾 /tmp — Render compatible
LAST_IDS_FILE = "/tmp/last_ids.json"

# 📊 HEALTH TRACKER
channel_status = {str(source): "🟡 Waiting" for source in SOURCES}

# ✅ DUPLICATE TRACKER
forwarded_ids = set()

# 🔴 ERROR COUNTER
error_count = {}

# ⏰ SMART DISABLED TRACKER
disabled_until = {}

# 💾 Disk write counter
save_counter = 0

def load_last_ids():
    if os.path.exists(LAST_IDS_FILE):
        with open(LAST_IDS_FILE, "r") as f:
            data = json.load(f)
            for source in SOURCES:
                if str(source) not in data:
                    data[str(source)] = 0
            return data
    return {str(source): 0 for source in SOURCES}

def save_last_ids(last_ids):
    with open(LAST_IDS_FILE, "w") as f:
        json.dump(last_ids, f)

# 🚀 BOT FUNCTION
async def run_bot():
    global forwarded_ids, save_counter, error_count, disabled_until

    forwarded_ids.clear()
    error_count.clear()
    disabled_until.clear()
    save_counter = 0

    print("🔥 Starting bot...")
    try:
        await app.start()
        print("✅ Bot login success")
    except Exception as e:
        print("❌ BOT LOGIN ERROR:", e)
        return

    try:
        await app.send_message("me", "✅ BOT STARTED")
    except Exception as e:
        print("❌ SELF MSG ERROR:", e)

    last_ids = load_last_ids()

    # ✅ Startup pe turant save — crash se bachao
    save_last_ids(last_ids)

    print("\n🔍 Checking all channels...")
    for source in SOURCES:
        key = str(source)
        try:
            await app.get_chat(source)
            channel_status[key] = "✅ Accessible"
            print(f"✅ {source} → OK")
        except Exception as e:
            channel_status[key] = "🔴 Error"
            print(f"❌ {source} → {e}")
        await asyncio.sleep(1)

    try:
        while True:
            for source in SOURCES:
                key = str(source)

                # ✅ Smart disabled — 60 sec baad auto retry
                if error_count.get(key, 0) > 5:
                    if key not in disabled_until:
                        disabled_until[key] = time.time() + 60
                        channel_status[key] = "⛔ Disabled (auto retry 60s)"
                        print(f"⛔ {source} disabled — 60s baad retry")

                if key in disabled_until:
                    if time.time() < disabled_until[key]:
                        continue
                    else:
                        del disabled_until[key]
                        error_count[key] = 0
                        channel_status[key] = "🟡 Retrying..."
                        print(f"🔄 {source} retry ho raha hai...")

                try:
                    messages = []
                    async for msg in app.get_chat_history(source, limit=5):
                        messages.append(msg)

                    await asyncio.sleep(0.5)

                    if not messages:
                        channel_status[key] = "🟡 No recent msg"
                        continue

                    error_count[key] = 0

                    for msg in reversed(messages):
                        if last_ids[key] == 0:
                            last_ids[key] = msg.id
                            save_counter += 1
                            continue

                        if msg.id <= last_ids[key]:
                            continue

                        msg_key = f"{source}_{msg.id}"
                        if msg_key in forwarded_ids:
                            continue

                        try:
                            await app.copy_message(TARGET, source, msg.id)

                            last_ids[key] = msg.id
                            forwarded_ids.add(msg_key)

                            # ✅ Simple safe clear — set unordered hota hai
                            if len(forwarded_ids) > 500:
                                forwarded_ids.clear()

                            channel_status[key] = f"🟢 Active @ {time.strftime('%H:%M:%S')}"
                            print(f"📩 {source} → {msg.id}")

                            save_counter += 1
                            if save_counter >= 5:
                                save_last_ids(last_ids)
                                save_counter = 0

                        except FloodWait as e:
                            print(f"⏳ FloodWait: {e.value} sec...")
                            await asyncio.sleep(e.value)

                            try:
                                await app.copy_message(TARGET, source, msg.id)

                                last_ids[key] = msg.id
                                forwarded_ids.add(msg_key)

                                channel_status[key] = f"🟢 Active @ {time.strftime('%H:%M:%S')}"
                                print(f"📩 RETRY SUCCESS {source} → {msg.id}")

                                save_counter += 1
                                if save_counter >= 5:
                                    save_last_ids(last_ids)
                                    save_counter = 0

                            except Exception as retry_e:
                                print(f"❌ Retry failed: {retry_e}")

                        except Exception as e:
                            channel_status[key] = "🔴 Send Error"
                            print(f"❌ Send error: {e}")

                except Exception as e:
                    if "CHANNEL_PRIVATE" in str(e):
                        channel_status[key] = "🚫 Private"
                        print(f"🚫 Not joined: {source}")
                    else:
                        error_count[key] = error_count.get(key, 0) + 1
                        channel_status[key] = f"🔴 Error ({error_count[key]}/5)"
                        print(f"❌ Source error {source}: {e}")

                await asyncio.sleep(1.5)

            save_last_ids(last_ids)
            save_counter = 0

            print("\n📊 CHANNEL STATUS:")
            for src, status in channel_status.items():
                print(f"  {src} → {status}")
            print(f"  🕐 Time: {time.strftime('%H:%M:%S')}\n")

            await asyncio.sleep(15)

    finally:
        save_last_ids(last_ids)
        print("🛑 Bot stop ho raha hai...")
        await app.stop()

# ✅ AUTO RESTART
async def main():
    while True:
        try:
            await run_bot()
        except Exception as e:
            print(f"❌ BOT CRASH: {e}")
            print("🔄 5 sec baad restart...")
            await asyncio.sleep(5)

# 🚀 START
if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
