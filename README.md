# PVC Last.fm Discord Bot

A Discord bot that randomly features Last.fm albums from community members, scrobbles tracks, and maintains a featured album log.

## Features

- 🎵 **Random Album Selection**: Automatically features albums from users' Last.fm top albums
- 📊 **User Preferences**: Users can opt-in/out of being featured
- 🔔 **Notifications**: Optional notifications when you're featured
- 📅 **Sunday Special**: Dues payers get higher selection chances on Sundays
- 📜 **Featured Log**: Track history of all featured albums
- 💾 **Database Persistence**: SQLite database for user data and preferences

## Prerequisites

- Python 3.9 or higher
- A Discord bot token ([Get one here](https://discord.com/developers/applications))
- Last.fm API credentials ([Get them here](https://www.last.fm/api/account/create))

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd pvc_lastfm
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and fill in your credentials:
   - `DISCORD_TOKEN`: Your Discord bot token
   - `LASTFM_API_KEY`: Your Last.fm API key
   - `LASTFM_SECRET`: Your Last.fm API secret
   - `LASTFM_SESSION_KEY`: Your Last.fm session key (see below)

5. **Get your Last.fm session key**

   a. Get an authentication token from Last.fm:
   ```
   https://www.last.fm/api/auth/?api_key=YOUR_API_KEY
   ```

   b. Run the session key script:
   ```bash
   python scripts/fetch_session.py
   ```

   c. Paste the auth token when prompted

   d. Copy the session key from the output and add it to your `.env` file

## Running the Bot

**Run the bot:**
```bash
python run_bot.py
```

**Or run the standalone main script:**
```bash
python -m src.main
```

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

## Configuration

### Environment Variables

- **DISCORD_TOKEN** (required): Your Discord bot token
- **LASTFM_API_KEY** (required): Your Last.fm API key
- **LASTFM_SECRET** (required): Your Last.fm API secret
- **LASTFM_SESSION_KEY** (required): Your Last.fm session key
- **PVC_DATA_DIR** (optional): Directory for data files (default: `./data`)

### Data Directory

The bot stores data in the `data/` directory by default:
- `data/pvc.db` - SQLite database with users, preferences, and featured albums
- `data/album_art.jpg` - Downloaded album art for featured albums

You can change the data directory by setting the `PVC_DATA_DIR` environment variable.

## Database Schema

The bot uses SQLite with three main tables:

### `users`
- `discord_id` (PRIMARY KEY): Discord user ID
- `lastfm_username`: Last.fm username
- `created_at`: Account creation timestamp
- `is_active`: Whether the account is active
- `is_special`: Special user status (for Sunday featuring)

### `user_preferences`
- `user_id` (PRIMARY KEY): Links to users table
- `track`: Eligible to be featured (default: true)
- `notify`: Receive notifications when featured (default: false)
- `double_track`: Eligible for Sunday special featuring (default: false)

### `featured_albums`
- `id`: Auto-increment ID
- `lastfm_username`: User whose album was featured
- `artist_name`, `artist_url`: Artist information
- `album_name`, `album_url`: Album information
- `cover_url`: Album cover image URL
- `featured_at`: Timestamp
- `is_current`: Whether this is the current featured album

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

### Running Tests

(Tests not yet implemented)

## Troubleshooting

### Bot won't start
- Check that all environment variables are set in `.env`
- Verify your Discord token is valid
- Ensure your Last.fm API credentials are correct

### "Failed to feature an album" error
- Make sure at least one user is connected with `!connect`
- Check that the Last.fm username exists and has listening history
- Verify your Last.fm session key is valid

### Database errors
- Ensure the `data/` directory exists and is writable
- Try deleting `data/pvc.db` to recreate the database (this will delete all data)

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

(Add your license information here)

## Acknowledgments

- Built with [discord.py](https://github.com/Rapptz/discord.py)
- Uses the [Last.fm API](https://www.last.fm/api)
