from pyrogram import Client
import asyncio
import os
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

# 🔥 SOURCE CHANNELS (OLD WORKING)
SOURCES = [
    -1001714047949,
    -1001404064358,
    -1001659536566,
    -1001153554563,
    -1001677474141
]

# 🎯 TARGET CHANNEL
TARGET = -1003817655107

# 🔁 TRACKER
last_ids = {source: 0 for source in SOURCES}

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

    while True:
        for source in SOURCES:
            try:
                messages = []
                async for msg in app.get_chat_history(source, limit=5):
                    messages.append(msg)

                for msg in reversed(messages):

                    # skip old msgs first run
                    if last_ids[source] == 0:
                        last_ids[source] = msg.id
                        continue

                    if msg.id > last_ids[source]:
                        last_ids[source] = msg.id

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
    Thread(target=run_web).start()   # 🔥 daemon हटाया
    asyncio.run(run_bot())
