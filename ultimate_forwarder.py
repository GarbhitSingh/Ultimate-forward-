import asyncio
import logging
import hashlib
import sys
import time
from collections import deque
from telethon import TelegramClient, events, errors

# ==========================
# CONFIGURATION
# ==========================

API_ID = 30800275  # <-- replace
API_HASH = "fb908c050c1d8eb1d37e8120567b915f"  # <-- replace

# PRIVATE BOT (optional)
SOURCE_BOT = "sheinnewproductsbot"  # without @
ENABLE_BOT = True

# MULTIPLE SOURCE CHANNELS
# Add unlimited here
SOURCE_CHANNELS = [
    "Frozen_CC",
    "ArifAnsar",
    "Rishavtechnical",
   # "ChannelFourUsername",
   # "ChannelFiveUsername",
    # Add more if needed
    # -1001987654321  (private channel example)
]

# TARGET CHANNEL
TARGET_CHANNEL = "ghost_loots"

# Branding (optional)
ADD_BRANDING = False
BRAND_TEXT = "\n\n📊 Powered by Ghost"

# ==========================
# ANTI-SPAM THROTTLE SETTINGS
# ==========================

MAX_MESSAGES_PER_WINDOW = 10      # max messages
WINDOW_SECONDS = 60               # per 60 seconds
FORCE_DELAY_BETWEEN_POSTS = 3     # seconds between each post

# ==========================
# LOGGING
# ==========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ==========================
# GLOBAL STATE
# ==========================

processed_hashes = set()
MAX_HASH_CACHE = 2000

message_timestamps = deque()

client = TelegramClient("ultimate_forward_session", API_ID, API_HASH)

# ==========================
# DUPLICATE FILTER
# ==========================

def is_duplicate(content):
    if not content:
        return False

    h = hashlib.sha256(content.encode()).hexdigest()

    if h in processed_hashes:
        return True

    processed_hashes.add(h)

    if len(processed_hashes) > MAX_HASH_CACHE:
        processed_hashes.pop()

    return False

# ==========================
# THROTTLE LOGIC
# ==========================

async def throttle():
    now = time.time()

    # Remove old timestamps
    while message_timestamps and now - message_timestamps[0] > WINDOW_SECONDS:
        message_timestamps.popleft()

    if len(message_timestamps) >= MAX_MESSAGES_PER_WINDOW:
        sleep_time = WINDOW_SECONDS - (now - message_timestamps[0])
        logging.warning(f"Rate limit reached. Sleeping {int(sleep_time)}s")
        await asyncio.sleep(sleep_time)

    await asyncio.sleep(FORCE_DELAY_BETWEEN_POSTS)

    message_timestamps.append(time.time())

# ==========================
# FORWARD FUNCTION
# ==========================

async def forward_message(message):
    try:
        text = message.text or ""
        caption = text

        if is_duplicate(text):
            logging.info("Duplicate skipped.")
            return

        await throttle()

        if ADD_BRANDING and caption:
            caption += BRAND_TEXT

        if message.media:
            await client.send_file(
                TARGET_CHANNEL,
                file=message.media,
                caption=caption if caption else None
            )
        else:
            if caption:
                await client.send_message(
                    TARGET_CHANNEL,
                    caption
                )

        logging.info("Forwarded successfully.")

    except errors.FloodWaitError as e:
        logging.warning(f"FloodWait {e.seconds}s")
        await asyncio.sleep(e.seconds)

    except Exception as e:
        logging.error(f"Error: {e}")

# ==========================
# EVENT LISTENERS
# ==========================

if ENABLE_BOT:
    @client.on(events.NewMessage(from_users=SOURCE_BOT))
    async def bot_listener(event):
        await forward_message(event.message)

@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def channel_listener(event):
    await forward_message(event.message)

# ==========================
# AUTO RECONNECT LOOP
# ==========================

async def main():
    while True:
        try:
            logging.info("Starting client...")
            await client.start()
            logging.info("Running multi-source forwarder...")
            await client.run_until_disconnected()
        except Exception as e:
            logging.error(f"Disconnected: {e}")
            await asyncio.sleep(5)

# ==========================
# ENTRY POINT
# ==========================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit()