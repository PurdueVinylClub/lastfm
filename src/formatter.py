import discord

def featured_embed(album_details: dict) -> discord.Embed:
    embed = discord.Embed()
    embed.title = "Featured:"
    embed.description = f"[{album_details['album']}](<{album_details['album_url']}>)\n by [{album_details['artist_name']}](<{album_details['artist_url']}>)\n\nWeekly albums from {album_details['member_l']}"
    embed.set_thumbnail(url=album_details['cover_url'])
    embed.set_footer(text="View your featured history with '.featuredlog'")

    return embed

def featurelog_embed(featured_log: list) -> discord.Embed:
    pass