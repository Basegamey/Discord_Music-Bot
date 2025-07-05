import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import yt_dlp
import json
CONFIG_FILE = "bot.config"
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            print("Config could not be loaded.")
    print("Welcome to the Discord Music Bot Setup")
    config = {
        "token": input("Bot Token: ").strip(),
        "client_id": input("Client ID: ").strip(),
        "guild_id": input("Guild ID (or leave blank for global): ").strip()
    }
    if input("Save this info to bot.config? (y/n): ").lower() == "y":
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
        print("Config saved to bot.config")
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
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree
queues = {}
loops = {}
current_voice_clients = {}
YDL_OPTIONS = {
    'format': 'bestaudio',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto'
}
async def ensure_connected(interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        return None
    voice_channel = interaction.user.voice.channel
    if not isinstance(voice_channel, discord.VoiceChannel):
        return None
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_connected():
        return voice_client
    try:
        return await voice_channel.connect()
    except Exception as e:
        print(f"[CONNECT ERROR] {e}")
        return None
async def play_next(guild_id):
    if guild_id not in queues or not queues[guild_id]:
        await asyncio.sleep(2)
        if guild_id in current_voice_clients:
            await current_voice_clients[guild_id].disconnect()
            del current_voice_clients[guild_id]
        print(f"Queue empty for Guild {guild_id}, bot disconnected.")
        return
    url, interaction, loop_count = queues[guild_id].pop(0)
    voice_client = await ensure_connected(interaction)
    if not voice_client:
        await interaction.followup.send("Reconnected and all reset. Ready for new action.", ephemeral=True)
        return
    current_voice_clients[guild_id] = voice_client
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            data = ydl.extract_info(url, download=False)
            if 'entries' in data:
                data = data['entries'][0]
            audio_url = data['url']
            title = data.get('title', 'Unknow')
            print(f"Playing: {title}")
    except Exception as e:
        await interaction.followup.send("Error retrieving audio stream.")
        print(f"[YDL ERROR] {e}")
        return
    try:
        source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        audio = discord.PCMVolumeTransformer(source, volume=0.5)
        voice_client.play(
            audio,
            after=lambda e: asyncio.run_coroutine_threadsafe(after_play(guild_id, (url, interaction, loop_count)), bot.loop)
        )
        await interaction.followup.send(f" **{title}** is played.")
    except Exception as e:
        await interaction.followup.send("Error starting playback.")
        print(f"[PLAY ERROR] {e}")

async def after_play(guild_id, entry):
    _, interaction, loop_count = entry
    if loop_count == "x" or (isinstance(loop_count, int) and loop_count > 1):
        if loop_count != "x":
            loop_count -= 1
        queues[guild_id].insert(0, (entry[0], interaction, loop_count))
    await play_next(guild_id)
@tree.command(name="play", description="Play music via YouTube link or search term")
@app_commands.describe(query="YouTube link, MP3 link or search term")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    guild_id = interaction.guild.id
    queues.setdefault(guild_id, []).append((query, interaction, 1))
    if not current_voice_clients.get(guild_id) or not current_voice_clients[guild_id].is_playing():
        await play_next(guild_id)
    else:
        await interaction.followup.send("Added to playlist.")

@tree.command(name="loop", description="Play something multiple times or endlessly")
@app_commands.describe(times="Zahl oder 'x' für unendlich", query="YouTube link or search term")
async def loop(interaction: discord.Interaction, times: str, query: str):
    await interaction.response.defer()
    guild_id = interaction.guild.id
    try:
        count = "x" if times.lower() == "x" else int(times)
        queues.setdefault(guild_id, []).append((query, interaction, count))
        if not current_voice_clients.get(guild_id) or not current_voice_clients[guild_id].is_playing():
            await play_next(guild_id)
        else:
            await interaction.followup.send(f"Loop playback added ({times}x).")
    except ValueError:
        await interaction.followup.send("Invalid repetition value.")
@tree.command(name="skip", description="Skips the current track")
async def skip(interaction: discord.Interaction):
    await interaction.response.defer()
    guild_id = interaction.guild.id
    vc = current_voice_clients.get(guild_id)
    if vc:
        vc.stop()
        await play_next(guild_id)
        await interaction.followup.send("Skipped.")
    else:
        await interaction.followup.send("Nothing is going on.")
@tree.command(name="skip_all", description="Skips everything and stops")
async def skip_all(interaction: discord.Interaction):
    await interaction.response.defer()
    guild_id = interaction.guild.id
    queues[guild_id] = []
    vc = current_voice_clients.get(guild_id)
    if vc:
        vc.stop()
    await interaction.followup.send("All playback stopped and playlist deleted.")
@tree.command(name="stop", description="Pauses playback")
async def stop(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if vc := current_voice_clients.get(guild_id):
        vc.pause()
        await interaction.response.send_message("Playback paused.")
@tree.command(name="off", description="Bot leaves the voice channel")
async def off(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    queues[guild_id] = []
    if vc := current_voice_clients.get(guild_id):
        await vc.disconnect()
        del current_voice_clients[guild_id]
    await interaction.response.send_message("Bot stopped and disconnected.")
@tree.command(name="end_loop", description="End all loop")
async def end_loop(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if vc := current_voice_clients.get(guild_id):
        await vc.disconnect()
    await ensure_connected(interaction)
    await interaction.response.send_message("loop stopped")
@bot.event
async def on_ready():
    print(f"Bot is ready! {bot.user}")
    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        await tree.sync(guild=guild)
        print(f"Commands synced to Guild {GUILD_ID}")
    else:
        await tree.sync()
        print("Synced global commands.")
    invite_url = f"https://discord.com/oauth2/authorize?client_id={config['client_id']}&scope=bot%20applications.commands&permissions=2213873984"
    print(f"Invite your bot with this link:\n{invite_url}")
@bot.event
async def on_command_error(ctx, error):
    print(f"[COMMAND ERROR] {error}")
    if hasattr(ctx, "followup"):
        await ctx.followup.send("An error has occurred.")

bot.run(TOKEN)
