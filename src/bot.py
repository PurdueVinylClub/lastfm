import formatter
import os
import sys

import discord
import dotenv
from apscheduler.schedulers.background import BackgroundScheduler

import database as db
import main

dotenv.load_dotenv()
token = os.environ.get("DISCORD_TOKEN")

# use discord.py to create frontend interface through discord
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

def scheduled_feature():
    """Wrapper for scheduled job that handles the full feature flow."""
    (featured_album, print_buffer) = main.main()
    if featured_album is None:
        print("Scheduled run: Failed to feature an album", file=sys.stderr)
        return

    print(print_buffer)

    db.set_featured_album(
        featured_album["member_l"],
        featured_album["artist_name"],
        featured_album["artist_url"],
        featured_album["album"],
        featured_album["album_url"],
        featured_album["cover_url"],
    )


def start_track():
    scheduler = BackgroundScheduler()

    # Run every hour at xx:00:00
    scheduler.add_job(scheduled_feature, "cron", hour="*")

    # TODO change bot pfp to album art automatically

    scheduler.start()


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")
    await client.change_presence(activity=discord.Game(name="Featuring albums"))

    start_track()
    print("Scheduler started...")

    (featured_album, print_buffer) = main.main()
    if featured_album is None:
        print("Warning: Failed to feature an album on startup", file=sys.stderr)
        return

    print(print_buffer)

    db.set_featured_album(
        featured_album["member_l"],
        featured_album["artist_name"],
        featured_album["artist_url"],
        featured_album["album"],
        featured_album["album_url"],
        featured_album["cover_url"],
    )


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!connect"):
        if db.get_lastfm_user(message.author.id):
            await message.channel.send(
                "You are already connected to a Last.fm account. Please disconnect your account with `!disconnect` and try again."
            )
            return

        parts = message.content.split()
        if len(parts) < 2:
            await message.channel.send(
                "Please provide a Last.fm username. Usage: `!connect <lastfm_username>`"
            )
            return

        lastfm_user = parts[1].strip()

        if db.set_lfm_discord_connection(message.author.id, lastfm_user):
            await message.channel.send("Connected to Last.fm account: " + lastfm_user + ".")
        else:
            await message.channel.send(
                "Failed to connect to Last.fm account. Please ping Avery and/or try again later."
            )

    elif message.content.startswith("!dues"):
        preferences = db.get_preferences(message.author.id)

        if preferences is None:
            await message.channel.send(
                "You are not currently connected to a Last.fm account. Please connect your account with `!connect <lastfm_username>` and try again."
            )
            return

        if not db.get_is_special(message.author.id):
            await message.channel.send(
                "You must be a dues payer to use this command. If you have paid dues, please ping Avery to add you to the database."
            )
            return

        if message.content == "!dues":
            if not preferences["double_track"]:
                await message.channel.send(
                    "You aren't being tracked on dues payer Sunday. Run `!dues on` to start tracking."
                )
            else:
                await message.channel.send(
                    "You are currently being tracked on dues payer Sunday. Run `!dues off` to stop tracking."
                )
            return

        if message.content == "!dues on":
            preferences["double_track"] = True
            await message.channel.send("You are now eligible to be featured extra.")

        if message.content == "!dues off":
            preferences["double_track"] = False
            await message.channel.send("You are no longer eligible to be featured extra.")

        db.set_preferences(message.author.id, preferences)

    elif message.content.startswith("!disconnect"):
        if not db.get_lastfm_user(message.author.id):
            await message.channel.send(
                "You are not currently connected to a Last.fm account. Please connect your account with `!connect <lastfm_username>`"
            )
            return

        if db.delete_user(message.author.id):
            await message.channel.send("Disconnected from Last.fm account.")
        else:
            await message.channel.send(
                "Failed to disconnect from Last.fm account. Please ping Avery and try again later."
            )

    elif message.content.startswith("!help"):
        help_text = """**PVC Last.fm Bot Commands**

**Connection:**
`!connect <lastfm_username>` - Connect your Discord account to your Last.fm account
`!disconnect` - Disconnect your Last.fm account

**Settings:**
`!settings` - View your current settings
`!track [on/off]` - Toggle whether you're eligible to be featured
`!notify [on/off]` - Toggle whether you get notified when featured
`!dues [on/off]` - Toggle eligibility for extra featuring on Sundays (dues payers only)

**Information:**
`!f` - Show the most recently featured album
`!featuredlog [username]` - View your featured album history (or someone else's)
`!help` - Show this help message

**How it works:**
The bot randomly features albums from users' Last.fm top albums every hour and scrobbles a random track from the selected album."""
        await message.channel.send(help_text)

    elif message.content.startswith("!featuredlog"):
        parts = message.content.split()
        if len(parts) > 1:
            lastfm_user = parts[1].strip()
            nickname = lastfm_user
        else:
            lastfm_user = db.get_lastfm_user(message.author.id)
            nickname = message.author.display_name

        if not lastfm_user:
            await message.channel.send(
                "You are not currently connected to a Last.fm account. Please connect your account with `!connect <lastfm_username>` and try again."
            )
            return

        featured_log = db.get_featured_log(lastfm_user)

        await message.channel.send(embed=formatter.featurelog_embed(nickname, featured_log or []))

    elif message.content.startswith("!f"):  # most recent featured
        album_details = db.get_featured_album()
        if not album_details:
            await message.channel.send("No featured album found.")
            return

        # format album_details as embed
        await message.channel.send(embed=formatter.featured_embed(album_details))

    elif message.content.startswith("!settings"):
        preferences = db.get_preferences(message.author.id)

        if preferences is None:
            await message.channel.send(
                "You are not currently connected to a Last.fm account. Please connect your account with `!connect <lastfm_username>` and try again."
            )
            return

        await message.channel.send(embed=formatter.settings_embed(preferences))

    elif message.content.startswith("!track"):
        preferences = db.get_preferences(message.author.id)

        if preferences is None:
            await message.channel.send(
                "You are not currently connected to a Last.fm account. Please connect your account with `!connect <lastfm_username>` and try again."
            )
            return

        if message.content == "!track":
            if not preferences["track"]:
                await message.channel.send(
                    "You are not currently eligible to be featured. Run `!track on` to start tracking."
                )
            else:
                await message.channel.send(
                    "You are currently eligible to be featured. Run `!track off` to stop tracking."
                )
            return

        if message.content == "!track on":
            preferences["track"] = True
            await message.channel.send("You are now eligible to be featured.")

        if message.content == "!track off":
            preferences["track"] = False
            await message.channel.send("You are no longer eligible to be featured.")

        db.set_preferences(message.author.id, preferences)

    elif message.content.startswith("!noti"):
        preferences = db.get_preferences(message.author.id)

        if preferences is None:
            await message.channel.send(
                "You are not currently connected to a Last.fm account. Please connect your account with `!connect <lastfm_username>` and try again."
            )
            return

        if message.content == "!notify":
            if not preferences["notify"]:
                await message.channel.send(
                    "You are not currently notified if you are featured. Run `!notify on` to start notifying."
                )
            else:
                await message.channel.send(
                    "You are currently notified when you are featured. Run `!notify off` to stop notifying."
                )
            return

        if message.content == "!notify on":
            preferences["notify"] = True
            await message.channel.send("You will now be notified when you are featured.")

        if message.content == "!notify off":
            preferences["notify"] = False
            await message.channel.send("You will no longer be notified when you are featured.")

        db.set_preferences(message.author.id, preferences)


if not token:
    print("Error: no token found in .env")
else:
    client.run(token)
