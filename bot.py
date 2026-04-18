from pyrogram import Client
from pyrogram.errors import FloodWait
import asyncio
import os
import json
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

# 🔥 SOURCE CHANNELS (9 TOTAL)
SOURCES = [
    -1001714047949,   # purana 1
    -1001404064358,   # purana 2
    -1001659536566,   # purana 3
    -1001153554563,   # purana 4
    -1001677474141,   # purana 5
    -1001686703979,   # naya 1 ✅
    -1001315464303,   # naya 3 ✅
    -1001707571730,   # naya 4 ✅
    -1001312563683    # naya 5 ✅
]

# 🎯 TARGET CHANNEL
TARGET = -1003817655107

# 💾 /tmp — Render compatible
LAST_IDS_FILE = "/tmp/last_ids.json"

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

    try:
        while True:
            for source in SOURCES:
                key = str(source)
                try:
                    # ✅ List me collect karo phir reverse — correct order!
                    messages = []
                    async for msg in app.get_chat_history(source, limit=5):
                        messages.append(msg)

                    for msg in reversed(messages):  # old → new order
                        # First run — sirf ID save karo
                        if last_ids[key] == 0:
                            last_ids[key] = msg.id
                            save_last_ids(last_ids)
                            continue

                        # Duplicate skip
                        if msg.id <= last_ids[key]:
                            continue

                        last_ids[key] = msg.id
                        save_last_ids(last_ids)

                        try:
                            await app.copy_message(TARGET, source, msg.id)
                            print(f"📩 {source} → {msg.id}")
                        except FloodWait as e:
                            print(f"⏳ FloodWait: {e.value} sec...")
                            await asyncio.sleep(e.value)
                        except Exception as e:
                            print(f"❌ Send error: {e}")

                except Exception as e:
                    if "CHANNEL_PRIVATE" in str(e):
                        print(f"🚫 Not joined: {source}")
                    else:
                        print(f"❌ Source error {source}: {e}")

                # ✅ Har channel ke baad 1 sec
                await asyncio.sleep(1)

            print("👀 Bot running...")
            await asyncio.sleep(10)

    finally:
        # ✅ Graceful shutdown
        print("🛑 Bot stop ho raha hai...")
        await app.stop()

# ✅ AUTO RESTART — crash pe khud restart
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
