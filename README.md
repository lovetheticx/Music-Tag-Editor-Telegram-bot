# Music Tag Editor Telegram Bot

A fully functional Telegram bot that allows users to edit music file tags including artist, title, album, year, genre, and album cover art.

## Features

✅ **Supported Audio Formats:**
- MP3
- FLAC
- M4A (AAC)
- OGG Vorbis
- OPUS

✅ **Editable Tags:**
- Title
- Artist
- Album
- Year
- Genre
- Album Cover (artwork)

✅ **User-Friendly Interface:**
- Interactive buttons for easy navigation
- Real-time tag display
- Automatic image optimization for covers
- Returns edited file to user

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the API token you receive

### 3. Set Environment Variable

**Linux/Mac:**
```bash
export TELEGRAM_BOT_TOKEN='your_token_here'
```

**Windows (CMD):**
```cmd
set TELEGRAM_BOT_TOKEN=your_token_here
```

**Windows (PowerShell):**
```powershell
$env:TELEGRAM_BOT_TOKEN='your_token_here'
```

Alternatively, you can modify the bot code to hardcode your token (not recommended for production):

```python
# In music_tag_bot.py, replace this line:
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# With:
TOKEN = "your_token_here"
```

## Usage

### Start the Bot

```bash
python music_tag_bot.py
```

You should see: `Bot started! Send audio files to edit their tags.`

### Using the Bot in Telegram

1. **Start conversation:** Send `/start` to your bot
2. **Upload audio file:** Send any supported audio file (MP3, FLAC, M4A, OGG, OPUS)
3. **View current tags:** The bot will display all current metadata
4. **Edit tags:** Click buttons to edit specific tags:
   - Click tag button (e.g., "📝 Title")
   - Send new value as text
   - Repeat for other tags
5. **Upload album cover:**
   - Click "🖼 Album Cover" button
   - Send image file (JPG, PNG, WEBP)
   - Image will be automatically optimized
6. **Get edited file:** Click "✅ Done" to receive your edited file

### Commands

- `/start` - Show welcome message and instructions
- `/cancel` - Cancel current editing session

## How It Works

### Tag Editing
The bot uses the `mutagen` library to read and write metadata tags. Each audio format has specific tag fields:

- **MP3:** Uses ID3v2 tags (TIT2, TPE1, TALB, etc.)
- **FLAC:** Uses Vorbis comments
- **M4A:** Uses iTunes-style atoms
- **OGG/OPUS:** Uses Vorbis comments

### Album Cover
- Images are automatically validated and converted to JPEG
- Large images are resized to max 1000×1000 pixels
- Quality is optimized for file size
- Covers are embedded directly in audio files

### File Processing Flow

1. User uploads audio file
2. Bot downloads file to system temp directory (Windows: `%TEMP%`, Linux/Mac: `/tmp/`)
3. Tags are read using appropriate mutagen class
4. User edits tags through interactive menu
5. Changes are saved to the file
6. Edited file is sent back to user
7. Temporary file is deleted

## Technical Details

### Dependencies

- **python-telegram-bot:** Telegram Bot API wrapper
- **mutagen:** Audio metadata handling
- **Pillow:** Image processing for album covers

### File Structure

```
music_tag_bot.py      # Main bot code
requirements.txt      # Python dependencies
README.md            # This file
```

### Conversation States

The bot uses a ConversationHandler with these states:
- `WAITING_FILE` - Waiting for audio file upload
- `SELECTING_TAG` - User selecting which tag to edit
- `EDITING_TAG` - User entering new tag value
- `UPLOADING_COVER` - User uploading cover image

## Troubleshooting

### Bot doesn't start
- Check that `TELEGRAM_BOT_TOKEN` environment variable is set
- Verify token is correct from BotFather
- Ensure all dependencies are installed

### File upload fails
- Make sure file format is supported (MP3, FLAC, M4A, OGG, OPUS)
- Check file isn't corrupted
- Verify file size is under Telegram's limit (50MB for bots)

### Cover image not working
- Ensure image format is JPG, PNG, or WEBP
- Try a different image
- Check image file isn't corrupted

### Tags not saving
- Verify audio file isn't write-protected
- Make sure file format is supported
- Check console for error messages

## Security Notes

- Bot token should be kept secret
- Don't hardcode tokens in production code
- Use environment variables or secure credential storage
- Files are temporarily stored in system temp directory and deleted after processing
- Works cross-platform (Windows, Linux, macOS)

## Example Usage

```
User: /start
Bot: Welcome message with instructions

User: [Uploads song.mp3]
Bot: Shows current tags with edit buttons

User: [Clicks "👤 Artist"]
Bot: "Send me the new Artist:"

User: The Beatles
Bot: "✅ Artist updated successfully!"
     [Shows updated tags]

User: [Clicks "🖼 Album Cover"]
Bot: "Send me an image file for the album cover"

User: [Uploads cover.jpg]
Bot: "✅ Album cover updated successfully!"
     [Shows updated tags]

User: [Clicks "✅ Done"]
Bot: [Sends edited file back]
```

## License

This code is provided as-is for educational and personal use.

## Support

For issues or questions, check:
- Mutagen documentation: https://mutagen.readthedocs.io/
- python-telegram-bot documentation: https://docs.python-telegram-bot.org/
