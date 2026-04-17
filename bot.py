from pyrogram import Client
import time
from flask import Flask
from threading import Thread

# 🔑 API DETAILS
api_id = 39158778
api_hash = "d3e48eebf551f78540740492b3dca674"

app = Client("my_account", api_id=api_id, api_hash=api_hash)

# 🌐 KEEP ALIVE SERVER (IMPORTANT FOR RENDER)
web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot is running!"

def run():
    web_app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 🔥 MULTIPLE SOURCE CHANNELS
SOURCES = [
    -1001714047949,
    -1001404064358,
    -1001659536566,
    -1001153554563,
    -1001677474141
]

# 🎯 TARGET CHANNEL
TARGET = -1003817655107

# 🔁 Har source ka last_id store
last_ids = {source: 0 for source in SOURCES}

# 🚀 START
keep_alive()

with app:
    print("🚀 Bot started...")

    while True:
        for source in SOURCES:
            try:
                messages = app.get_chat_history(source, limit=5)

                for msg in messages:
                    if msg.id > last_ids[source]:
                        last_ids[source] = msg.id

                        try:
                            # ✅ TEXT
                            if msg.text:
                                app.send_message(TARGET, msg.text)

                            # ✅ PHOTO
                            elif msg.photo:
                                app.send_photo(
                                    TARGET,
                                    photo=msg.photo.file_id,
                                    caption=msg.caption or ""
                                )

                            # ✅ DOCUMENT
                            elif msg.document:
                                app.send_document(
                                    TARGET,
                                    document=msg.document.file_id,
                                    caption=msg.caption or ""
                                )

                            print(f"✅ Sent from {source}")

                            time.sleep(2)

                        except Exception as e:
                            print("❌ Send Error:", e)

            except Exception as e:
                print(f"❌ Source Error ({source}):", e)

        time.sleep(5)
