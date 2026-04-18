from pyrogram import Client
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

# 🔥 SOURCE CHANNELS (10 TOTAL)
SOURCES = [
    -1001714047949,   # purana 1
    -1001404064358,   # purana 2
    -1001659536566,   # purana 3
    -1001153554563,   # purana 4
    -1001677474141,   # purana 5
    -1001686703979,   # naya 1 ✅
    -1001377627085,   # naya 2 ✅
    -1001315464303,   # naya 3 ✅
    -1001707571730,   # naya 4 ✅
    -1001312563683    # naya 5 ✅
]

# 🎯 TARGET CHANNEL
TARGET = -1003817655107

# 💾 LAST IDs FILE (restart ke baad bhi yaad rahega)
LAST_IDS_FILE = "last_ids.json"

def load_last_ids():
    if os.path.exists(LAST_IDS_FILE):
        with open(LAST_IDS_FILE, "r") as f:
            data = json.load(f)
            # Naye channels ke liye 0 set karo
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

    # 💾 Load saved IDs
    last_ids = load_last_ids()

    while True:
        for source in SOURCES:
            key = str(source)
            try:
                messages = []
                async for msg in app.get_chat_history(source, limit=5):
                    messages.append(msg)

                for msg in reversed(messages):
                    # First run — sirf ID save karo, forward mat karo
                    if last_ids[key] == 0:
                        last_ids[key] = msg.id
                        save_last_ids(last_ids)
                        continue

                    if msg.id > last_ids[key]:
                        last_ids[key] = msg.id
                        save_last_ids(last_ids)  # 💾 Turant save karo
                        try:
                            if msg.text:
                                await app.send_message(TARGET, msg.text)
                            elif msg.photo:
                                await app.send_photo(
                                    TARGET,
                                    msg.photo.file_id,
                                    caption=msg.caption or ""
                                )
                            elif msg.document:
                                await app.send_document(
                                    TARGET,
                                    msg.document.file_id,
                                    caption=msg.caption or ""
                                )
                            print(f"✅ Sent from {source}")
                        except Exception as e:
                            print("❌ Send error:", e)

            except Exception as e:
                print(f"❌ Source error {source}:", e)

        print("👀 Bot running...")
        await asyncio.sleep(5)

# 🚀 START BOTH
if __name__ == "__main__":
    Thread(target=run_web).start()
    asyncio.run(run_bot())
