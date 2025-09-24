from apscheduler.schedulers.blocking import BlockingScheduler
import discord
import database as db
import formatter
import os
import dotenv
import time
import main

dotenv.load_dotenv()
token = os.environ.get('DISCORD_TOKEN')

# use discord.py to create frontend interface through discord
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

def start_track():
    scheduler = BlockingScheduler()

    # Run every 15 minutes, at second 30 (xx:00:30, xx:15:30, xx:30:30, xx:45:30)
    scheduler.add_job(
        main.main,
        'cron',
        minute='0,15,30,45',
        second=30
    )

    print("Scheduler started...")
    scheduler.start()

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    await client.change_presence(activity=discord.Game(name="Featuring NULL"))

    # start_track()

    (featured_album, print_buffer) = main.main()
    assert featured_album is not None

    print(print_buffer)

    db.init()
    db.set_featured_album(featured_album['member_l'], featured_album['artist_name'], featured_album['artist_url'], featured_album['album'], featured_album['album_url'], featured_album['cover_url'])

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content.startswith('!connect'):
        if db.get_lastfm_user(message.author.id):
            await message.channel.send('You are already connected to a Last.fm account. Please disconnect your account with `!disconnect` and try again.')
            return
        
        if len(message.content.split(' ')) < 2:
            await message.channel.send('Please provide a Last.fm username. Usage: `!connect <lastfm_username>`')
            return

        lastfm_user = message.content.split(' ')[1]
        if db.set_lfm_discord_connection(message.author.id, lastfm_user):
            await message.channel.send('Connected to Last.fm account: ' + lastfm_user + '.')
        else:
            await message.channel.send('Failed to connect to Last.fm account. Please ping Avery and try again later.')

    if message.content.startswith('!disconnect'):
        if not db.get_lastfm_user(message.author.id):
            await message.channel.send('You are not currently connected to a Last.fm account. Please connect your account with `!connect <lastfm_username>`') 
            return

        if db.delete_user(message.author.id):
            await message.channel.send('Disconnected from Last.fm account.')
        else:
            await message.channel.send('Failed to disconnect from Last.fm account. Please ping Avery and try again later.')

    elif message.content.startswith('!help'):
        await message.channel.send('TODO')

    elif message.content.startswith('!featuredlog'):
        lastfm_user = db.get_lastfm_user(message.author.id)

        if not lastfm_user:
            await message.channel.send('You are not currently connected to a Last.fm account. Please connect your account with `!connect <lastfm_username>` and try again.')
            return

        featured_log = db.get_featured_log(lastfm_user)

        await message.channel.send(embed=formatter.featurelog_embed(featured_log))

    elif message.content.startswith('!f'): # most recent featured
        album_details = db.get_featured_album()
        if not album_details:
            await message.channel.send('No featured album found.')
            return
        
        # format album_details as embed
        await message.channel.send(embed=formatter.featured_embed(album_details))

    elif message.content.startswith('!settings'):
        preferences = db.get_preferences(message.author.id)
    
        await message.channel.send(embed=formatter.settings_embed(preferences))

    elif message.content.startswith('!track'):
        preferences = db.get_preferences(message.author.id)

        if preferences is None:
            await message.channel.send('You are not currently connected to a Last.fm account. Please connect your account with `!connect <lastfm_username>` and try again.')
            return

        if message.content == '!track':
            if not preferences['track']:
                await message.channel.send('You are not currently eligible to be featured. Run `!track on` to start tracking.')
            else:
                await message.channel.send('You are currently eligible to be featured. Run `!track off` to stop tracking.')

        if message.content == '!track on':
            preferences['track'] = True
            db.set_preferences(message.author.id, preferences)
            await message.channel.send('You are now eligible to be featured.')

        if message.content == '!track off':
            preferences['track'] = False
            db.set_preferences(message.author.id, preferences)
            await message.channel.send('You are no longer eligible to be featured.')

        # TODO special roles stuff
    
    elif message.content.startswith('!noti'):
        preferences = db.get_preferences(message.author.id)

        if preferences is None:
            await message.channel.send('You are not currently connected to a Last.fm account. Please connect your account with `!connect <lastfm_username>` and try again.')
            return

        if message.content == '!notify':
            if not preferences['notify']:
                await message.channel.send('You are not currently notified if you are featured. Run `!notify on` to start notifying.')
            else:
                await message.channel.send('You are currently notified when you are featured. Run `!notify off` to stop notifying.')

        if message.content == '!notify on':
            preferences['notify'] = True
            db.set_preferences(message.author.id, preferences)
            await message.channel.send('You will now be notified when you are featured.')

        if message.content == '!notify off':
            preferences['notify'] = False
            db.set_preferences(message.author.id, preferences)
            await message.channel.send('You will no longer be notified when you are featured.')

client.run(token)