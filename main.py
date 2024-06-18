import asyncio
import os
import time
from uuid import uuid4

import telethon
import redis
from telethon import TelegramClient, events
from telethon.tl.functions.messages import ForwardMessagesRequest
from telethon.tl.types import UpdateNewMessage

from plans import plans_command  # Import the new feature file
from cansend import CanSend
from config import *
from terabox import get_data
from tools import (
    convert_seconds,
    download_file,
    download_image_to_bytesio,
    extract_code_from_url,
    get_formatted_size,
    get_urls_from_string,
    is_user_on_chat,
)

# Initialize Telegram client
bot = TelegramClient("tele", API_ID, API_HASH)

# Initialize Redis database connection
db = redis.Redis(
    host=HOST,
    port=PORT,
    password=PASSWORD,
    decode_responses=True,
)

# Event handler for /start command
@bot.on(events.NewMessage(pattern="/start$", incoming=True, outgoing=False))
async def start(event: UpdateNewMessage):
    reply_text = """
𝐇𝐞𝐥𝐥𝐨! 𝐈 𝐚𝐦 𝐓𝐞𝐫𝐚𝐛𝐨𝐱 𝐕𝐢𝐝𝐞𝐨 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐞𝐫 𝐁𝐨𝐭.
𝐒𝐞𝐧𝐝 𝐦𝐞 𝐭𝐞𝐫𝐚𝐛𝐨𝐱 𝐯𝐢𝐝𝐞𝐨 𝐥𝐢𝐧𝐤 & 𝐈 𝐰𝐢𝐥𝐥 𝐬𝐞𝐧𝐝 𝐕𝐢𝐝𝐞𝐨.

𝐏𝐋𝐀𝐍'𝐒 : /plans"""

    channel1 = "@SK_MoviesOffl"
    channel2 = "@VillageTv"

    # Check if user is in required channels
    if not await is_user_on_chat(bot, channel1, event.sender_id) or not await is_user_on_chat(bot, channel2, event.sender_id):
        return await event.reply("𝐏𝐥𝐞𝐚𝐬𝐞 𝐣𝐨𝐢𝐧 @SK_MoviesOffl 𝐚𝐧𝐝 @VillageTv 𝐛𝐞𝐟𝐨𝐫𝐞 𝐮𝐬𝐢𝐧𝐠 𝐭𝐡𝐞 𝐛𝐨𝐭.")

    await event.reply(reply_text, link_preview=False, parse_mode="markdown")

# Event handler for /start with parameter
@bot.on(events.NewMessage(pattern="/start (.*)", incoming=True, outgoing=False))
async def start_with_param(event: UpdateNewMessage):
    text = event.pattern_match.group(1)
    fileid = db.get(str(text))

    channel1 = "@SK_MoviesOffl"
    channel2 = "@VillageTv"

    # Check if user is in required channels
    check_channel1 = await is_user_on_chat(bot, channel1, event.sender_id)
    check_channel2 = await is_user_on_chat(bot, channel2, event.sender_id)

    if not check_channel1 or not check_channel2:
        return await event.reply("𝐏𝐥𝐞𝐚𝐬𝐞 𝐣𝐨𝐢𝐧 @SK_MoviesOffl 𝐚𝐧𝐝 @VillageTv 𝐛𝐞𝐟𝐨𝐫𝐞 𝐮𝐬𝐢𝐧𝐠 𝐭𝐡𝐞 𝐛𝐨𝐭.")

    try:
        if fileid:
            await bot(ForwardMessagesRequest(
                from_peer=PRIVATE_CHAT_ID,
                id=[int(fileid)],
                to_peer=event.chat_id,
                drop_author=True,
                noforwards=False,
                background=True,
                drop_media_captions=False,
                with_my_score=True,
            ))
        else:
            await event.reply("No file ID found for the given parameter.")
    except telethon.errors.rpcerrorlist.MessageIdInvalidError as e:
        await event.reply(f"The specified message ID is invalid or you can't do that operation on such message: {e}")
    except telethon.errors.rpcerrorlist.FloodWaitError as e:
        await event.reply(f"Flood wait error: {e}")
    except telethon.errors.rpcerrorlist.RPCError as e:
        await event.reply(f"An RPC error occurred: {e}")
    except Exception as e:
        await event.reply(f"An unexpected error occurred: {e}")

# Event handler for /plans command
@bot.on(events.NewMessage(pattern="/plans$", incoming=True, outgoing=False))
async def plans_command_wrapper(event):
    await plans_command(event)

# Event handler for /adduser command (only accessible by ADMINS)
@bot.on(events.NewMessage(pattern="/adduser (\d+)$", incoming=True, outgoing=False, from_users=ADMINS))
async def add_user_command(event: UpdateNewMessage):
    user_id_to_add = int(event.pattern_match.group(1))

    if user_id_to_add not in ADMINS:
        ADMINS.append(user_id_to_add)
        update_config_file()
        await event.reply(f"User ID {user_id_to_add} added to ADMINS list.")
    else:
        await event.reply(f"User ID {user_id_to_add} is already in the ADMINS list.")

# Update config file with new ADMINS list
def update_config_file():
    with open('config.py', 'r') as config_file:
        lines = config_file.readlines()

    for i, line in enumerate(lines):
        if line.startswith("ADMINS = "):
            lines[i] = f"ADMINS = {ADMINS}\n"
            break

    with open('config.py', 'w') as config_file:
        config_file.writelines(lines)

# Event handler for /remove command (only accessible by ADMINS)
@bot.on(events.NewMessage(pattern="/remove (.*)", incoming=True, outgoing=False, from_users=ADMINS))
async def remove(event: UpdateNewMessage):
    user_id = event.pattern_match.group(1)
    if db.get(f"check_{user_id}"):
        db.delete(f"check_{user_id}")
        await event.reply(f"Removed {user_id} from the list.")
    else:
        await event.reply(f"{user_id} is not in the list.")

# Event handler for handling messages with URLs
@bot.on(events.NewMessage(incoming=True, outgoing=False, func=lambda message: message.text and get_urls_from_string(message.text) and message.is_private))
async def get_message(event: UpdateNewMessage):
    asyncio.create_task(handle_message(event))

# Handle message with URL, download and forward
async def handle_message(event: UpdateNewMessage):
    channel1 = "@SK_MoviesOffl"
    channel2 = "@VillageTv"

    check_channel1 = await is_user_on_chat(bot, channel1, event.sender_id)
    check_channel2 = await is_user_on_chat(bot, channel2, event.sender_id)

    if not check_channel1 or not check_channel2:
        return await event.reply(f"Please join {channel1} and {channel2} then send link.")

    url = get_urls_from_string(event.text)
    if not url:
        return await event.reply("Please enter a valid URL.")

    hm = await event.reply("Sending you the media, please wait...")

    count = db.get(f"check_{event.sender_id}")
    if count and int(count) > 10:
        return await hm.edit("You are limited now. Please come back after 30 minutes or use another account.")

    shorturl = extract_code_from_url(url)
    if not shorturl:
        return await hm.edit("Seems like your link is invalid.")

    fileid = db.get(shorturl)
    if fileid:
        try:
            await hm.delete()
        except:
            pass

        try:
            await bot(ForwardMessagesRequest(
                from_peer=PRIVATE_CHAT_ID,
                id=[int(fileid)],
                to_peer=event.chat_id,
                drop_author=True,
                noforwards=False,
                background=True,
                drop_media_captions=False,
                with_my_score=True,
            ))
        except telethon.errors.rpcerrorlist.MessageIdInvalidError as e:
            await event.reply(f"The specified message ID is invalid or you can't do that operation on such message: {e}")
        except Exception as e:
            await event.reply(f"An error occurred: {e}")

        return

    data = get_data(url)
    if not data:
        return await hm.edit("Sorry! API is dead or maybe your link is broken.")

    db.set(event.sender_id, time.monotonic(), ex=60)
    if not data["file_name"].endswith((".mp4", ".mkv", ".webm", ".png", ".jpg", ".jpeg")):
        return await hm.edit("Sorry! File is not supported for now. I can download only .mp4, .mkv, and .webm files.")

    if int(data["sizebytes"]) > 500000000 and event.sender_id not in ADMINS:
        return await hm.edit(f"Sorry! File is too big. I can download only 500 MB and this file is {data['size']}.")

    start_time = time.time()
    cansend = CanSend()

    async def progress_bar(current_downloaded, total_downloaded, state="Sending"):
        if not cansend.can_send():
            return
        bar_length = 20
        percent = current_downloaded / total_downloaded
        arrow = "◉" * int(percent * bar_length)
        spaces = "◯" * (bar_length - len(arrow))

        elapsed_time = time.time() - start_time
        speed_line = f"Speed: {get_formatted_size(current_downloaded / elapsed_time)}/s"

        time_remaining = (
            (total_downloaded - current_downloaded) / (current_downloaded / elapsed_time)
            if current_downloaded > 0 else 0
        )
        time_line = f"Time Remaining: {convert_seconds(time_remaining)}"

        size_line = f"Size: {get_formatted_size(current_downloaded)} / {get_formatted_size(total_downloaded)}"

        await hm.edit(
            f"{state} `{data['file_name']}`\n\n"
            f"[{arrow + spaces}] {percent:.2%}\n\n"
            f"{speed_line}\n\n"
            f"{time_line}\n\n"
            f"{size_line}",
            parse_mode="markdown",
        )

    uuid = str(uuid4())
    thumbnail = download_image_to_bytesio(data["thumb"], "thumbnail.png")

    try:
        file = await bot.send_file(
            PRIVATE_CHAT_ID,
            file=data["direct_link"],
            thumb=thumbnail if thumbnail else None,
            progress_callback=progress_bar,
            caption=f"""
File Name: `{data['file_name']}`
Size: {data["size"]} 
Direct Link: [Click Here](https://t.me/Links_Bypasss_bot?start={uuid})

@SK_MoviesOffl
""",
            supports_streaming=True,
            spoiler=True,
        )
    except telethon.errors.rpcerrorlist.WebpageCurlFailedError:
        download = await download_file(
            data["direct_link"], data["file_name"], progress_bar
        )
        if not download:
            return await hm.edit(
                f"Sorry! Download Failed but you can download it from [here]({data['direct_link']}).",
                parse_mode="markdown",
            )
        file = await bot.send_file(
            PRIVATE_CHAT_ID,
            download,
            caption=f"""
File Name: `{data['file_name']}`
Size: {data["size"]} 
Direct Link: [Click Here](https://t.me/Links_Bypasss_bot?start={uuid})

@SK_MoviesOffl
""",
            progress_callback=progress_bar,
            thumb=thumbnail if thumbnail else None,
            supports_streaming=True,
            spoiler=True,
        )
        try:
            os.unlink(download)
        except Exception as e:
            print(e)
    except Exception as e:
        return await hm.edit(
            f"An error occurred while sending the file: {e}",
            parse_mode="markdown",
        )

    try:
        await hm.delete()
    except Exception as e:
        print(e)

    if shorturl:
        db.set(shorturl, file.id)
    if file:
        db.set(uuid, file.id)

        await bot(
            ForwardMessagesRequest(
                from_peer=PRIVATE_CHAT_ID,
                id=[file.id],
                to_peer=event.chat_id,
                top_msg_id=event.id,
                drop_author=True,
                noforwards=False,
                background=True,
                drop_media_captions=False,
                with_my_score=True,
            )
        )

# Start the bot with the specified token
bot.start(bot_token=BOT_TOKEN)
bot.run_until_disconnected()
                
