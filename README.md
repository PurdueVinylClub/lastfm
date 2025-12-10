# PVC Last.fm Discord Bot

A Discord bot that randomly features Last.fm albums from community members, scrobbles tracks, and maintains a featured album log.

## Features

- **Random Album Selection**: Automatically features albums from users' Last.fm top albums
- **User Preferences**: Users can opt-in/out of being featured
- **Notifications**: (Optional) discord notifications when you're featured
- **Sunday Special**: Dues payers get higher selection chances on Sundays
- **Featured Log**: Track history of all featured albums

## Discord Bot Commands

### Connection Commands
- `!connect <lastfm_username>` - Connect your Discord account to your Last.fm account
- `!disconnect` - Disconnect your Last.fm account

### Settings Commands
- `!settings` - View your current settings
- `!track [on/off]` - Toggle whether you're eligible to be featured
- `!notify [on/off]` - Toggle whether you get notified when featured
- `!dues [on/off]` - Toggle eligibility for extra featuring on Sundays

### Information Commands
- `!f` - Show the most recently featured album
- `!featuredlog [username]` - View your featured album history (or someone else's)
- `!help` - Show help message with all commands

## Development

### Project Structure

```
pvc_lastfm/
├── src/
│   ├── __init__.py       # Package initialization
│   ├── bot.py            # Discord bot frontend
│   ├── main.py           # Core album selection logic
│   ├── database.py       # Database operations
│   └── formatter.py      # Discord embed formatting
├── scripts/
│   ├── fetch_session.py  # Get Last.fm session key
│   └── combine_usernames.py # Utility script
├── data/                 # Data directory (created automatically)
├── run_bot.py            # Entry point script
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
└── README.md             # This file
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Acknowledgments

- Built with [discord.py](https://github.com/Rapptz/discord.py)
- Uses the [Last.fm API](https://www.last.fm/api)
