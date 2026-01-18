import formatter
import os
import sys

import discord
import dotenv
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database as db
import main

dotenv.load_dotenv()
token = os.environ.get("DISCORD_TOKEN")
notify_channel_id = os.environ.get("NOTIFY_CHANNEL_ID")
dues_payer_role_id = os.environ.get("DUES_PAYER_ROLE_ID")

# use discord.py to create frontend interface through discord
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)


def is_special_member(member: discord.Member | None) -> bool:
    """Check if a Discord member qualifies as a special (dues payer) user."""
    if not member:
        return False
    if member.guild_permissions.administrator:
        return True
    if dues_payer_role_id:
        return any(str(role.id) == dues_payer_role_id for role in member.roles)
    return False


async def send_notifications(featured_album: dict):
    """Send notification to the configured channel when a user's album is featured."""
    if not notify_channel_id:
        return

    discord_id = db.get_discord_id(featured_album["member_l"])
    if not discord_id:
        return

    # Check if user wants notifications
    preferences = db.get_preferences(discord_id)
    if not preferences or not preferences.get("notify"):
        return

    channel = client.get_channel(int(notify_channel_id))
    if channel is None or isinstance(channel, discord.abc.PrivateChannel):
        print(f"Notification channel {notify_channel_id} not found or invalid", file=sys.stderr)
        return

    embed = formatter.featured_embed(featured_album)

    try:
        await channel.send(
            content=f"<@{discord_id}> Your album has been featured!",
            embed=embed,
        )
    except Exception as e:
        print(f"Failed to send notification: {e}", file=sys.stderr)


async def scheduled_feature():
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

    # download art
    response = requests.get(featured_album["cover_url"])

    with open("album_art.jpg", "wb") as f:
        f.write(response.content)

    with open("album_art.jpg", "rb") as f:
        await client.user.edit(avatar=f.read())

    # Update bot status to show currently featured album
    status_text = f'Featuring "{featured_album["album"]}" from {featured_album["member_l"]}'
    await client.change_presence(activity=discord.Game(name=status_text))

    await send_notifications(featured_album)


def start_track():
    scheduler = AsyncIOScheduler()

    # Run every hour at xx:00:00
    scheduler.add_job(scheduled_feature, "cron", hour="*")

    scheduler.start()


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")
    await client.change_presence(activity=discord.Game(name="Featuring albums"))

    start_track()
    print("Scheduler started...")

    await scheduled_feature()


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
            # Check if user qualifies as a special (dues payer) user
            member = message.guild.get_member(message.author.id) if message.guild else None
            if is_special_member(member):
                db.set_is_special(message.author.id, True)
                preferences = db.get_preferences(message.author.id)
                if preferences:
                    preferences["double_track"] = True
                    db.set_preferences(message.author.id, preferences)
                await message.channel.send(
                    f"Connected to Last.fm account: {lastfm_user}. You've been automatically registered as a dues payer! Tip: if you want to be notified every time you're featured, run `!notify on`."
                )
            else:
                await message.channel.send(
                    f"Connected to Last.fm account: {lastfm_user}. Tip: if you want to be notified every time you're featured, run `!notify on`."
                )
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

        if message.content == "!dues on":
            # Check if user has admin permissions or the dues payer role
            member = message.guild.get_member(message.author.id) if message.guild else None
            if not is_special_member(member):
                await message.channel.send(
                    "You don't have the required role to mark yourself as a dues payer."
                )
                return

            db.set_is_special(message.author.id, True)
            preferences["double_track"] = True
            db.set_preferences(message.author.id, preferences)
            await message.channel.send(
                "You are now marked as a dues payer and eligible to be featured extra on Sundays."
            )
            return

        # For other dues commands, require being a dues payer
        if not db.get_is_special(message.author.id):
            await message.channel.send(
                "You must be a dues payer to use this command. If you have paid dues, run `!dues on` to register."
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

        if message.content == "!dues off":
            preferences["double_track"] = False
            db.set_preferences(message.author.id, preferences)
            await message.channel.send("You are no longer eligible to be featured extra.")

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
The bot randomly features albums from users' Last.fm top albums every hour and scrobbles a random track from the selected album.

**View all featured albums:**
Check out the complete history of all featured albums at https://last.fm/user/purduevinylclub"""
        await message.channel.send(help_text)

    elif message.content.startswith("!featuredlog"):
        if message.mentions:
            mentioned_user = message.mentions[0]
            lastfm_user = db.get_lastfm_user(mentioned_user.id)
            nickname = mentioned_user.display_name
            if not lastfm_user:
                await message.channel.send(f"{nickname} is not connected to a Last.fm account.")
                return
        else:
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
