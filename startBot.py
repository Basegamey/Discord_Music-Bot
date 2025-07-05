import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import yt_dlp
import json
import logging
CONFIG_FILE = "bot.config"
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Config could not be loaded: {e}")
    logging.info("Welcome to the Discord Music Bot Setup")
    config = {
        "token": input("Bot Token: ").strip(),
        "client_id": input("Client ID: ").strip(),
        "guild_id": input("Guild ID (or leave blank for global): ").strip()
    }
    if input("Save this info to bot.config? (y/n): ").lower() == "y":
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
        logging.info("Config saved to bot.config")
    return config
config = load_config()
TOKEN = config["token"]
GUILD_ID = int(config["guild_id"]) if config["guild_id"] else None
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_PATH = os.path.join(BASE_DIR, "ffmpeg-7.1.1-essentials_build", "bin", "ffmpeg.exe")
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
    'executable': FFMPEG_PATH
}
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree
queues = {}
loop_disabled = set()
current_voice_clients = {}
playing_tasks = {}
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}
async def ensure_connected(interaction):
    voice_channel = interaction.user.voice.channel if interaction.user.voice else None
    if not voice_channel:
        await interaction.followup.send("You must be in a voice channel to play music.", ephemeral=True)
        return None
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_connected():
        if voice_client.channel.id != voice_channel.id:
            logging.info(f"Moving voice client to channel {voice_channel.name}")
            await voice_client.move_to(voice_channel)
        return voice_client
    try:
        voice_client = await voice_channel.connect()
        return voice_client
    except Exception as e:
        logging.error(f"[CONNECT ERROR] {e}")
        await interaction.followup.send("Error connecting to the voice channel.", ephemeral=True)
        return None
async def play_next(guild_id):
    if playing_tasks.get(guild_id, False):
        return
    playing_tasks[guild_id] = True
    try:
        queue = queues.get(guild_id, [])
        if not queue:
            vc = current_voice_clients.get(guild_id)
            if vc and vc.is_connected():
                await asyncio.sleep(2)
                if not queues.get(guild_id):
                    await vc.disconnect()
                    del current_voice_clients[guild_id]
                    logging.info(f"Queue empty, bot has left Guild {guild_id}.")
            return
        url, interaction, loop_count = queue.pop(0)
        voice_client = await ensure_connected(interaction)
        if not voice_client:
            await interaction.followup.send("Could not connect to the voice channel.", ephemeral=True)
            return
        current_voice_clients[guild_id] = voice_client
        try:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                data = ydl.extract_info(url, download=False)
                if 'entries' in data:
                    data = data['entries'][0]
                audio_url = data['url']
                title = data.get('title', 'Unbekannt')
                logging.info(f"Spiele: {title}")
        except Exception as e:
            await interaction.followup.send("Error retrieving audio stream.", ephemeral=True)
            logging.error(f"[YDL ERROR] {e}")
            return
        source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        audio = discord.PCMVolumeTransformer(source, volume=0.5)
        def after_play(error):
            if error:
                logging.error(f"Playback error: {error}")
            fut = asyncio.run_coroutine_threadsafe(after_play_callback(guild_id, (url, interaction, loop_count)), bot.loop)
            try:
                fut.result()
            except Exception as e:
                logging.error(f"Error in after_play callback: {e}")
        voice_client.play(audio, after=after_play)
        await interaction.followup.send(f"**{title}** is played.", ephemeral=False)
    finally:
        playing_tasks[guild_id] = False
async def after_play_callback(guild_id, entry):
    url, interaction, loop_count = entry
    if guild_id not in loop_disabled:
        if loop_count == "x" or (isinstance(loop_count, int) and loop_count > 1):
            if loop_count != "x":
                loop_count -= 1
            queues.setdefault(guild_id, []).insert(0, (url, interaction, loop_count))
    else:
        logging.info(f"Loop is disabled for Guild {guild_id}")
        loop_disabled.discard(guild_id)
    await play_next(guild_id)
@tree.command(name="play", description="Play music via YouTube link or search term")
@app_commands.describe(query="YouTube link or search term")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    guild_id = interaction.guild.id
    queues.setdefault(guild_id, []).append((query, interaction, 1))
    vc = current_voice_clients.get(guild_id)
    if not vc or not vc.is_playing():
        await play_next(guild_id)
    else:
        await interaction.followup.send("Added to playlist.", ephemeral=True)
@tree.command(name="loop", description="Repeats a song multiple times or endlessly")
@app_commands.describe(times="Number or 'x' for endless", query="YouTube link or search term")
async def loop(interaction: discord.Interaction, times: str, query: str):
    await interaction.response.defer()
    guild_id = interaction.guild.id
    try:
        count = "x" if times.lower() == "x" else int(times)
    except ValueError:
        await interaction.followup.send("Invalid repetition value.", ephemeral=True)
        return
    queues.setdefault(guild_id, []).append((query, interaction, count))
    vc = current_voice_clients.get(guild_id)
    if not vc or not vc.is_playing():
        await play_next(guild_id)
    else:
        await interaction.followup.send(f"Repeat playback added ({times}x).", ephemeral=True)
@tree.command(name="skip", description="Skips the current track")
async def skip(interaction: discord.Interaction):
    await interaction.response.defer()
    guild_id = interaction.guild.id
    vc = current_voice_clients.get(guild_id)
    if vc and vc.is_playing():
        vc.stop()
        await interaction.followup.send("Skipped.", ephemeral=True)
    else:
        await interaction.followup.send("Nothing is happening right now.", ephemeral=True)
@tree.command(name="skip_all", description="Skips everything and stops playback")
async def skip_all(interaction: discord.Interaction):
    await interaction.response.defer()
    guild_id = interaction.guild.id
    queues[guild_id] = []
    vc = current_voice_clients.get(guild_id)
    if vc:
        vc.stop()
    await interaction.followup.send("All playback stopped and playlist deleted.", ephemeral=True)
@tree.command(name="stop", description="Pauses playback")
async def stop(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    vc = current_voice_clients.get(guild_id)
    if vc and vc.is_playing():
        vc.pause()
        await interaction.response.send_message("Playback paused.", ephemeral=True)
    else:
        await interaction.response.send_message("Nothing is played.", ephemeral=True)
@tree.command(name="resume", description="Resumes playback")
async def resume(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    vc = current_voice_clients.get(guild_id)
    if vc and vc.is_paused():
        vc.resume()
        await interaction.response.send_message("Playback continued.", ephemeral=True)
    else:
        await interaction.response.send_message("Nothing is paused.", ephemeral=True)
@tree.command(name="off", description="Bot leaves the voice channel")
async def off(interaction: discord.Interaction):
    await interaction.response.defer()
    guild_id = interaction.guild.id
    queues[guild_id] = []
    vc = current_voice_clients.get(guild_id)
    if vc:
        await vc.disconnect()
        del current_voice_clients[guild_id]
    await interaction.followup.send("Bot stopped and voice channel left.", ephemeral=True)
@tree.command(name="end_loop", description="Ends all loops and resumes playback")
async def end_loop(interaction: discord.Interaction):
    await interaction.response.defer()
    guild_id = interaction.guild.id
    loop_disabled.add(guild_id)
    if guild_id in queues:
        new_queue = []
        for entry in queues[guild_id]:
            url, inter, loop_count = entry
            new_queue.append((url, inter, 1))
        queues[guild_id] = new_queue
    await interaction.followup.send("All loops are ended. The current songs are played once.", ephemeral=True)
@bot.event
@bot.event
async def on_ready():
    logging.info(f"Bot is ready! Logged in as {bot.user}")
    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        await tree.sync(guild=guild)
        logging.info(f"Commands for Guild {GUILD_ID} synchronized")
    else:
        await tree.sync()
        logging.info("Global commands synchronized.")
    app_info = await bot.application_info()
    client_id = app_info.id
    invite_url = f"https://discord.com/oauth2/authorize?client_id={client_id}&permissions=277083450688&scope=bot+applications.commands"
    logging.info(f"Invite the bot using this link:\n{invite_url}")
@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user:
        guild_id = member.guild.id
        vc = current_voice_clients.get(guild_id)
        if vc is None or not vc.is_connected():
            await asyncio.sleep(1)
            logging.info(f"Bot was disconnected in Guild {guild_id}, try reconnecting.")
            voice_channel = after.channel or before.channel
            if voice_channel:
                try:
                    new_vc = await voice_channel.connect()
                    current_voice_clients[guild_id] = new_vc
                    if queues.get(guild_id):
                        await play_next(guild_id)
                except Exception as e:
                    logging.error(f"Reconnect error in Guild {guild_id}: {e}")
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if not message.content.startswith("B;"):
        return
    try:
        command_body = message.content[2:].strip()
        if command_body.lower().startswith("play "):
            query = command_body[5:].strip()
            class DummyInteraction:
                def __init__(self, message):
                    self.guild = message.guild
                    self.user = message.author
                    self.followup = type('FollowUp', (), {'send': lambda self, content, ephemeral=False: message.channel.send(content)})
            interaction = DummyInteraction(message)
            queues.setdefault(message.guild.id, []).append((query, interaction, 1))
            vc = current_voice_clients.get(message.guild.id)
            if not vc or not vc.is_playing():
                await play_next(message.guild.id)
            else:
                await message.channel.send("Added to playlist.")
        elif command_body.lower().startswith("loop "):
            parts = command_body.split(maxsplit=2)
            if len(parts) < 3:
                await message.channel.send("Usage: B;loop [times|'x'] [query]")
                return
            times, query = parts[1], parts[2]
            count = "x" if times.lower() == "x" else int(times)
            class DummyInteraction:
                def __init__(self, message):
                    self.guild = message.guild
                    self.user = message.author
                    self.followup = type('FollowUp', (), {'send': lambda self, content, ephemeral=False: message.channel.send(content)})
            interaction = DummyInteraction(message)
            queues.setdefault(message.guild.id, []).append((query, interaction, count))
            vc = current_voice_clients.get(message.guild.id)
            if not vc or not vc.is_playing():
                await play_next(message.guild.id)
            else:
                await message.channel.send(f"Repeat playback added ({times}x).")
        elif command_body.lower() == "skip":
            ctx = await bot.get_context(message)
            await skip(ctx)
        elif command_body.lower() == "skip_all":
            ctx = await bot.get_context(message)
            await skip_all(ctx)
        elif command_body.lower() == "stop":
            ctx = await bot.get_context(message)
            await stop(ctx)
        elif command_body.lower() == "resume":
            ctx = await bot.get_context(message)
            await resume(ctx)
        elif command_body.lower() == "off":
            ctx = await bot.get_context(message)
            await off(ctx)
        elif command_body.lower() == "end_loop":
            ctx = await bot.get_context(message)
            await end_loop(ctx)
        else:
            await message.channel.send("Unknown command.")
    except Exception as e:
        logging.error(f"[B;-Handler ERROR] {e}")
    await bot.process_commands(message)
@bot.event
async def on_command_error(ctx, error):
    logging.error(f"[COMMAND ERROR] {error}")
    if hasattr(ctx, "followup"):
        await ctx.followup.send("An error has occurred.", ephemeral=True)
bot.run(TOKEN)
