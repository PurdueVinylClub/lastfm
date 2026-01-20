from datetime import timezone

import discord
from dateutil.parser import parse


def featured_embed(album_details: dict) -> discord.Embed:
    embed = discord.Embed()
    embed.title = "Featured:"
    embed.description = f"[{album_details['album']}](<{album_details['album_url']}>)\n by [{album_details['artist_name']}](<{album_details['artist_url']}>)\n\nWeekly albums from {album_details['member_l']}"
    embed.set_thumbnail(url=album_details["cover_url"])
    embed.set_footer(text="View your featured history with '!featuredlog'")

    return embed


def featurelog_embed(name: str, featured_log: list) -> discord.Embed:
    embed = discord.Embed()
    embed.title = f"{name}'s featured history:"

    if featured_log:
        for album in featured_log[0:10]:  # maximum of 10
            embed.add_field(
                name=f"{album['artist_name']} - {album['album_name']}",
                value=f"Featured on <t:{int(parse(album['featured_at']).replace(tzinfo=timezone.utc).timestamp())}:s>",
                inline=False,
            )
    else:
        embed.description = """
        Sorry, you haven't been featured yet...

        Become a dues payer and get a higher chance every Sunday.
        """

    return embed


def settings_embed(preferences: dict) -> discord.Embed:
    embed = discord.Embed()
    embed.title = "Your settings:"
    embed.description = f"""
    **Tracking** (!track): {"yes" if preferences["track"] else "no"}
    **Notifications** (!notify): {"yes" if preferences["notify"] else "no"}
    **Double Chances (dues payer only)** (!dues): {"yes" if preferences["double_track"] else "no"}
    """

    return embed
