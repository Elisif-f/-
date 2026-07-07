import discord
import os
from dotenv import load_dotenv
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta, timezone

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

LOG_CHANNEL_ID = #id канала для логов
YOUR_USER_ID = #id админов, которым разрешено

SPAM_WINDOW_SECONDS = 10
MIN_CHANNELS_FOR_BAN = 3

user_channels = defaultdict(dict)

async def delete_recent_messages(user, channel, minutes=3):
    deleted = 0
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=minutes)
    async for message in channel.history(limit=200):
        if message.author == user and message.created_at > cutoff:
            try:
                await message.delete()
                deleted += 1
            except:
                pass
    return deleted

@client.event
async def on_ready():
    print(f" Бот {client.user} запущен!")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.author.bot:
        return
    if not (message.author.guild_permissions.administrator or message.author.id == YOUR_USER_ID):
        now = datetime.now(timezone.utc)
        uid = message.author.id
        cid = message.channel.id

        user_channels[uid][cid] = now

        old_channels = [
            ch for ch, ts in user_channels[uid].items()
            if now - ts > timedelta(seconds=SPAM_WINDOW_SECONDS)
        ]
        for ch in old_channels:
            del user_channels[uid][ch]

        if len(user_channels[uid]) >= MIN_CHANNELS_FOR_BAN:
            try:
                channel_list = list(user_channels[uid].keys())
                timestamps = [user_channels[uid][ch] for ch in channel_list]
                first_time = min(timestamps)
                last_time = max(timestamps)
                time_diff = (last_time - first_time).total_seconds()

                channel_names = []
                for ch_id in channel_list:
                    ch = client.get_channel(ch_id)
                    channel_names.append(f"#{ch.name}" if ch else str(ch_id))

                await message.author.ban(
                    reason=f"Спам-атака: {len(channel_list)} каналов за {time_diff:.0f} сек",
                    delete_message_days=1
                )
                print(f" Бот забанил {message.author}")

                total_deleted = 0
                for channel_id in channel_list:
                    channel = client.get_channel(channel_id)
                    if channel:
                        deleted = await delete_recent_messages(message.author, channel, minutes=3)
                        total_deleted += deleted

                log_channel = client.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    await log_channel.send(
                        f" **{message.author}** забанен за спам-атаку.\n"
                        f" Каналы: {len(channel_names)} канала ({', '.join(channel_names)})\n"
                        f" Временной разброс: с {first_time.strftime('%H:%M:%S')} до {last_time.strftime('%H:%M:%S')} ({time_diff:.0f} сек)\n"
                        f" Сообщений: {len(timestamps)}\n"
                        f" Удалено сообщений: {total_deleted}\n"
                        f" Время бана: {now.strftime('%H:%M:%S')}"
                    )
                    print(" Подробный лог отправлен")

            except Exception as e:
                print(f"❌ Ошибка при бане: {e}")

            del user_channels[uid]
            return

    content = message.content.lower()


TOKEN = os.getenv("DISCORD_TOKEN")
client.run(TOKEN)
