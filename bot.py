from pyrogram import Client
import asyncio
import os
from flask import Flask
from threading import Thread

# 🔐 ENV VARIABLES
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
string_session = os.getenv("STRING_SESSION")

# 🤖 TELEGRAM CLIENT
app = Client(
    "my_account",
    api_id=api_id,
    api_hash=api_hash,
    session_string=string_session
)

# 🌐 FLASK
web = Flask(__name__)

@web.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web.run(host="0.0.0.0", port=port)

# 🔥 UPDATED SOURCE CHANNELS
SOURCES = [
    -1001714047949,
    -1001404064358,
    -1001659536566,
    -1001153554563,
    -1001677474141,
    -1001387115878,
    -1002167725152,
    -1001302730016,
    -1002393042058,
    -1001312563683
]

# 🎯 TARGET CHANNEL
TARGET = -1003817655107

# 🔁 TRACKER
last_ids = {source: 0 for source in SOURCES}

# 🚀 BOT LOGIC
async def run_bot():
    print("🔥 Starting bot...")

    try:
        await app.start()
        print("✅ Bot login success")
    except Exception as e:
        print("❌ LOGIN ERROR:", e)
        return

    await app.send_message("me", "✅ BOT STARTED")

    while True:
        for source in SOURCES:
            try:
                messages = []
                async for msg in app.get_chat_history(source, limit=5):
                    messages.append(msg)

                for msg in reversed(messages):

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

        await asyncio.sleep(5)

# 🚀 START
if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    asyncio.run(run_bot())
