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

class FeaturedListing:
    def update(self, member: str, artist: str, album: str, track: str):
        self.member = member
        self.artist = artist
        self.album = album
        self.track = track
    
    def format_embed(self):
        pass


client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    await client.change_presence(activity=discord.Game(name="Featuring NULL"))

    # scheduler = BlockingScheduler()

    # # Run every 15 minutes, at second 30 (xx:00:30, xx:15:30, xx:30:30, xx:45:30)
    # scheduler.add_job(
    #     fetch_recent_album,
    #     'cron',
    #     minute='0,15,30,45',
    #     second=30
    # )

    #print("Scheduler started...")
    # scheduler.start()

    (success, featured_album) = main.main()
    assert success

    print(featured_album)
    # TODO
    db.set_featured_album()

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('!help'):
        await message.channel.send('TODO')

    elif message.content.startswith('!featuredlog'):
        await message.channel.send('TODO')

    elif message.content.startswith('!f'): # most recent featured
        album_details = db.get_featured_album()
        
        # format album_details as embed
        await message.channel.send(embed=formatter.featured_embed(album_details))

    elif message.content.startswith('!settings'):
        await message.channel.send('TODO')

    elif message.content.startswith('!track'):
        if message.content == '!track':
            await message.channel.send('You are not currently tracking. Run `!track on` to start tracking.')
            await message.channel.send('You are currently tracking. Run `!track off` to stop tracking.')

        special_roles = db.get_special_roles()

        await message.channel.send('You are not currently tracking, what is your Last.fm username?')
        response = await client.wait_for('message')
        print(response.content)

        is_special = False

        for role in message.author.roles:
            if role.id in special_roles:
                is_special = True
                break
    
    elif message.content.startswith('!noti'):
        await message.channel.send('TODO')



client.run(token)