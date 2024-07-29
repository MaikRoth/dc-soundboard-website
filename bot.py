import asyncio
import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import json
from werkzeug.utils import secure_filename
from moviepy.editor import VideoFileClip
import ffmpeg

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
SOUNDS_DIR = 'uploads'  # Directory where sound files are stored
SOUND_FILES_JSON = 'sound_files.json'

# Intents
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

# Create bot
bot = commands.Bot(command_prefix='!', intents=intents)

# Flag to track if the bot was explicitly joined
explicitly_joined = False

# Get list of sound files available
def get_sound_files():
    if os.path.exists(SOUND_FILES_JSON):
        with open(SOUND_FILES_JSON, 'r') as f:
            return json.load(f)["sounds"]
    return []

# Function to convert various formats to MP3
def convert_to_mp3(input_path, output_path):
    if input_path.endswith('.mp4'):
        video = VideoFileClip(input_path)
        video.audio.write_audiofile(output_path)
        video.close()
    else:
        ffmpeg.input(input_path).output(output_path).run()

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('/upload'):
        parts = message.content.split(' ', 1)
        if len(parts) != 2 or not parts[1].strip():
            await message.channel.send("Please provide a name for the sound.")
            return
        
        sound_name = parts[1].strip()

        sound_files = get_sound_files()
        if any(sound['name'] == sound_name for sound in sound_files):
            await message.channel.send("A sound with this name already exists. Please choose a different name.")
            return

        if len(message.attachments) != 1:
            await message.channel.send("Please attach exactly one MP3, MP4, or OGG file.")
            return

        attachment = message.attachments[0]
        if not (attachment.filename.endswith('.mp3') or attachment.filename.endswith('.mp4') or attachment.filename.endswith('.ogg')):
            await message.channel.send("Please upload an MP3, MP4, or OGG file.")
            return

        sanitized_filename = secure_filename(sound_name)
        if not sanitized_filename:
            await message.channel.send("The sound name cannot be empty or contain only special characters.")
            return

        if attachment.filename.endswith('.mp4'):
            # Download the file temporarily to check its duration
            temp_path = os.path.join(SOUNDS_DIR, 'temp_' + sanitized_filename + '.mp4')
            await attachment.save(temp_path)

            clip = VideoFileClip(temp_path)
            if clip.duration > 15:
                os.remove(temp_path)
                await message.channel.send("The video cannot be longer than 15 seconds.")
                return

            mp4_path = os.path.join(SOUNDS_DIR, sanitized_filename + '.mp4')
            os.rename(temp_path, mp4_path)
            file_path = os.path.join(SOUNDS_DIR, sanitized_filename + '.mp3')
            convert_to_mp3(mp4_path, file_path)
            os.remove(mp4_path)
        elif attachment.filename.endswith('.ogg'):
            temp_path = os.path.join(SOUNDS_DIR, 'temp_' + sanitized_filename + '.ogg')
            await attachment.save(temp_path)
            
            file_path = os.path.join(SOUNDS_DIR, sanitized_filename + '.mp3')
            convert_to_mp3(temp_path, file_path)
            os.remove(temp_path)
        else:
            # Save the MP3 file
            file_path = os.path.join(SOUNDS_DIR, sanitized_filename + '.mp3')
            await attachment.save(file_path)

        # Update the sound files JSON
        sound_files.append({"name": sound_name, "filename": sanitized_filename})
        with open(SOUND_FILES_JSON, 'w') as f:
            json.dump({"sounds": sound_files}, f)

        await message.channel.send(f'Sound "{sound_name}" successfully uploaded.')

async def sound_name_autocomplete(interaction: discord.Interaction, current: str):
    sound_files = get_sound_files()
    return [
        app_commands.Choice(name=sound['name'], value=sound['name'])
        for sound in sound_files if current.lower() in sound['name'].lower()
    ][:25]

@bot.tree.command(name="play", description="Play a sound")
@app_commands.describe(sound_name="Name of the sound to play")
@app_commands.autocomplete(sound_name=sound_name_autocomplete)
async def play(interaction: discord.Interaction, sound_name: str):
    await interaction.response.defer(ephemeral=False)

    sound_files = get_sound_files()
    sound_file = next((sound for sound in sound_files if sound['name'] == sound_name), None)
    if sound_file is None:
        await interaction.followup.send(f'Sound "{sound_name}" not found.')
        return

    sound_path = os.path.join(SOUNDS_DIR, f'{sound_file["filename"]}.mp3')

    if interaction.user.voice is None or interaction.user.voice.channel is None:
        await interaction.followup.send("You need to be in a voice channel to use this command.", ephemeral=True)
        return

    channel = interaction.user.voice.channel

    if interaction.guild.voice_client is None:
        voice_client = await channel.connect()
    else:
        voice_client = interaction.guild.voice_client

    if os.path.isfile(sound_path):
        if not voice_client.is_playing():
            voice_client.play(discord.FFmpegPCMAudio(sound_path))

            while voice_client.is_playing():
                await asyncio.sleep(1)
                
            if not explicitly_joined:
                await voice_client.disconnect()
            await interaction.followup.send(f'Played sound: {sound_name}')
        else:
            await interaction.followup.send("I'm already playing a sound, please wait until it finishes.")
    else:
        await interaction.followup.send(f'Sound "{sound_name}" not found.')

@bot.tree.command(name="join", description="Join a voice channel")
async def join(interaction: discord.Interaction):
    global explicitly_joined

    if interaction.user.voice is None or interaction.user.voice.channel is None:
        await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
        return

    channel = interaction.user.voice.channel

    # Check if the bot is already in the voice channel
    if interaction.guild.voice_client is not None:
        if interaction.guild.voice_client.channel == channel:
            await interaction.response.send_message("I am already in your voice channel.")
        else:
            await interaction.guild.voice_client.disconnect()
            await channel.connect()
            explicitly_joined = True
            await interaction.response.send_message(f"Joined the voice channel {channel.name}")
    else:
        await channel.connect()
        explicitly_joined = True
        await interaction.response.send_message(f"Joined the voice channel {channel.name}")


@bot.tree.command(name="leave", description="Leave the voice channel")
async def leave(interaction: discord.Interaction):
    global explicitly_joined
    if interaction.user.voice is None or interaction.user.voice.channel is None:
        await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
        return

    if interaction.guild.voice_client is not None:
        await interaction.guild.voice_client.disconnect()
        explicitly_joined = False
        await interaction.response.send_message("Left the voice channel.")
    else:
        await interaction.response.send_message("I am not in any voice channel.")

@bot.tree.command(name="help", description="Explain how to use this bot")
async def help(interaction: discord.Interaction):
    help_text = """
**Soundboard Bot Commands:**

1. **/play <sound_name>**: 
   - Description: Play a sound from the soundboard.
   - Usage: `/play <sound_name>`
   - Example: `/play laughing`
   - Autocomplete: As you type, it suggests available sound names.

2. **/join**:
   - Description: Join the voice channel you are currently in.
   - Usage: `/join`
   - Example: Type `/join` while you are in a voice channel, and the bot will join the channel.

3. **/leave**:
   - Description: Leave the voice channel the bot is currently in.
   - Usage: `/leave`
   - Example: Type `/leave` and the bot will leave the voice channel.

4. **/upload <sound_name>**:
   - Description: Upload an mp3, mp4, or ogg file to the soundboard. If it's an mp4 or ogg, it will be converted to mp3.
   - Usage: 
     1. Attach an mp3, mp4, or ogg file in your message.
     2. Type `/upload <sound_name>` to name the sound.
   - Example: Attach an mp3, mp4, or ogg file and type `/upload funny_sound`
   - Note: Ensure you attach exactly one mp3, mp4, or ogg file and provide a unique name for the sound.
    """
    await interaction.response.send_message(help_text, ephemeral=True)

bot.run(TOKEN)