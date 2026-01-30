#!/usr/bin/env python3
"""
Telegram Bot for Editing Music Tags
Supports: MP3, FLAC, M4A, OGG, OPUS
Features: Edit artist, title, album, year, genre, album art
"""

import os
import logging
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from mutagen.mp3 import MP3
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, APIC
from PIL import Image
import io

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
WAITING_FILE, SELECTING_TAG, EDITING_TAG, UPLOADING_COVER = range(4)

# User data keys
CURRENT_FILE = "current_file"
CURRENT_TAG = "current_tag"
FILE_FORMAT = "file_format"
MENU_MESSAGE_ID = "menu_message_id"


class MusicTagEditor:
    """Handler for music tag editing operations"""
    
    @staticmethod
    def get_tags(filepath):
        """Extract tags from audio file"""
        ext = os.path.splitext(filepath)[1].lower()
        tags = {}
        
        try:
            if ext == ".mp3":
                audio = MP3(filepath, ID3=ID3)
                tags["title"] = str(audio.get("TIT2", "Not set"))
                tags["artist"] = str(audio.get("TPE1", "Not set"))
                tags["album"] = str(audio.get("TALB", "Not set"))
                tags["year"] = str(audio.get("TDRC", "Not set"))
                tags["genre"] = str(audio.get("TCON", "Not set"))
                tags["has_cover"] = "APIC:" in audio.tags if audio.tags else False
                
            elif ext == ".flac":
                audio = FLAC(filepath)
                tags["title"] = audio.get("title", ["Not set"])[0]
                tags["artist"] = audio.get("artist", ["Not set"])[0]
                tags["album"] = audio.get("album", ["Not set"])[0]
                tags["year"] = audio.get("date", ["Not set"])[0]
                tags["genre"] = audio.get("genre", ["Not set"])[0]
                tags["has_cover"] = len(audio.pictures) > 0
                
            elif ext == ".m4a":
                audio = MP4(filepath)
                tags["title"] = audio.get("\xa9nam", ["Not set"])[0]
                tags["artist"] = audio.get("\xa9ART", ["Not set"])[0]
                tags["album"] = audio.get("\xa9alb", ["Not set"])[0]
                tags["year"] = audio.get("\xa9day", ["Not set"])[0]
                tags["genre"] = audio.get("\xa9gen", ["Not set"])[0]
                tags["has_cover"] = "covr" in audio
                
            elif ext in [".ogg", ".opus"]:
                audio = OggVorbis(filepath) if ext == ".ogg" else OggOpus(filepath)
                tags["title"] = audio.get("title", ["Not set"])[0]
                tags["artist"] = audio.get("artist", ["Not set"])[0]
                tags["album"] = audio.get("album", ["Not set"])[0]
                tags["year"] = audio.get("date", ["Not set"])[0]
                tags["genre"] = audio.get("genre", ["Not set"])[0]
                # OGG/OPUS store cover in metadata field
                tags["has_cover"] = "metadata_block_picture" in audio or "coverart" in audio
                
        except Exception as e:
            logger.error(f"Error reading tags: {e}")
            return None
            
        return tags
    
    @staticmethod
    def set_tag(filepath, tag_name, value):
        """Set a specific tag in the audio file"""
        ext = os.path.splitext(filepath)[1].lower()
        
        try:
            if ext == ".mp3":
                audio = MP3(filepath, ID3=ID3)
                if audio.tags is None:
                    audio.add_tags()
                
                if tag_name == "title":
                    audio.tags["TIT2"] = TIT2(encoding=3, text=value)
                elif tag_name == "artist":
                    audio.tags["TPE1"] = TPE1(encoding=3, text=value)
                elif tag_name == "album":
                    audio.tags["TALB"] = TALB(encoding=3, text=value)
                elif tag_name == "year":
                    audio.tags["TDRC"] = TDRC(encoding=3, text=value)
                elif tag_name == "genre":
                    audio.tags["TCON"] = TCON(encoding=3, text=value)
                    
                audio.save()
                
            elif ext == ".flac":
                audio = FLAC(filepath)
                if tag_name in ["title", "artist", "album", "genre"]:
                    audio[tag_name] = value
                elif tag_name == "year":
                    audio["date"] = value
                audio.save()
                
            elif ext == ".m4a":
                audio = MP4(filepath)
                tag_map = {
                    "title": "\xa9nam",
                    "artist": "\xa9ART",
                    "album": "\xa9alb",
                    "year": "\xa9day",
                    "genre": "\xa9gen"
                }
                audio[tag_map[tag_name]] = value
                audio.save()
                
            elif ext in [".ogg", ".opus"]:
                audio = OggVorbis(filepath) if ext == ".ogg" else OggOpus(filepath)
                if tag_name == "year":
                    audio["date"] = value
                else:
                    audio[tag_name] = value
                audio.save()
                
            return True
        except Exception as e:
            logger.error(f"Error setting tag: {e}")
            return False
    
    @staticmethod
    def set_cover(filepath, image_data):
        """Set album cover art"""
        ext = os.path.splitext(filepath)[1].lower()
        
        try:
            # Validate and optimize image
            img = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            
            # Resize if too large (max 1000x1000)
            if img.width > 1000 or img.height > 1000:
                img.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
            
            # Save optimized image
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=90)
            image_data = output.getvalue()
            
            if ext == ".mp3":
                audio = MP3(filepath, ID3=ID3)
                if audio.tags is None:
                    audio.add_tags()
                
                # Remove existing covers
                audio.tags.delall("APIC")
                
                # Add new cover
                audio.tags["APIC"] = APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,  # Cover (front)
                    desc="Cover",
                    data=image_data
                )
                audio.save()
                
            elif ext == ".flac":
                audio = FLAC(filepath)
                
                # Remove existing pictures
                audio.clear_pictures()
                
                # Add new picture
                picture = Picture()
                picture.type = 3  # Cover (front)
                picture.mime = "image/jpeg"
                picture.desc = "Cover"
                picture.data = image_data
                audio.add_picture(picture)
                audio.save()
                
            elif ext == ".m4a":
                audio = MP4(filepath)
                audio["covr"] = [MP4Cover(image_data, imageformat=MP4Cover.FORMAT_JPEG)]
                audio.save()
                
            elif ext in [".ogg", ".opus"]:
                audio = OggVorbis(filepath) if ext == ".ogg" else OggOpus(filepath)
                
                # For OGG/OPUS, we need to encode the image as base64 in a Picture
                picture = Picture()
                picture.type = 3
                picture.mime = "image/jpeg"
                picture.desc = "Cover"
                picture.data = image_data
                
                # Encode picture to base64
                import base64
                picture_data = base64.b64encode(picture.write()).decode("ascii")
                audio["metadata_block_picture"] = picture_data
                audio.save()
                
            return True
        except Exception as e:
            logger.error(f"Error setting cover: {e}")
            return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    welcome_text = (
        "🎵 <b>Music Tag Editor Bot</b>\n\n"
        "Send me an audio file (MP3, FLAC, M4A, OGG, OPUS) and I'll help you edit its tags!\n\n"
        "<b>Supported tags:</b>\n"
        "• Title\n"
        "• Artist\n"
        "• Album\n"
        "• Year\n"
        "• Genre\n"
        "• Album Cover\n\n"
        "Just send me a file to get started!"
    )
    await update.message.reply_text(welcome_text, parse_mode="HTML")
    return WAITING_FILE


async def handle_audio_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle received audio file"""
    message = update.message
    
    # Get file
    if message.audio:
        file = message.audio
    elif message.document:
        file = message.document
    else:
        await message.reply_text("Please send an audio file.")
        return WAITING_FILE
    
    # Check file extension
    filename = file.file_name
    ext = os.path.splitext(filename)[1].lower()
    
    if ext not in [".mp3", ".flac", ".m4a", ".ogg", ".opus"]:
        await message.reply_text(
            "❌ Unsupported file format. Please send MP3, FLAC, M4A, OGG, or OPUS files."
        )
        return WAITING_FILE
    
    # Download file
    status_msg = await message.reply_text("⏳ Downloading file...")
    
    try:
        file_obj = await file.get_file()
        
        # Create temp directory if it doesn't exist
        temp_dir = tempfile.gettempdir()
        filepath = os.path.join(temp_dir, f"{file.file_unique_id}{ext}")
        
        await file_obj.download_to_drive(filepath)
        
        # Store file info
        context.user_data[CURRENT_FILE] = filepath
        context.user_data[FILE_FORMAT] = ext
        
        # Read current tags
        tags = MusicTagEditor.get_tags(filepath)
        
        if tags is None:
            await status_msg.edit_text("❌ Error reading file tags. Please try another file.")
            return WAITING_FILE
        
        # Create keyboard
        keyboard = [
            [InlineKeyboardButton("📝 Title", callback_data="edit_title")],
            [InlineKeyboardButton("👤 Artist", callback_data="edit_artist")],
            [InlineKeyboardButton("💿 Album", callback_data="edit_album")],
            [InlineKeyboardButton("📅 Year", callback_data="edit_year")],
            [InlineKeyboardButton("🎭 Genre", callback_data="edit_genre")],
            [InlineKeyboardButton("🖼 Album Cover", callback_data="edit_cover")],
            [InlineKeyboardButton("✅ Done", callback_data="done")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Show current tags
        cover_status = "✓ Set" if tags["has_cover"] else "✗ Not set"
        info_text = (
            f"<b>Current Tags:</b>\n\n"
            f"📝 Title: {tags['title']}\n"
            f"👤 Artist: {tags['artist']}\n"
            f"💿 Album: {tags['album']}\n"
            f"📅 Year: {tags['year']}\n"
            f"🎭 Genre: {tags['genre']}\n"
            f"🖼 Cover: {cover_status}\n\n"
            f"Select what you want to edit:"
        )
        
        await status_msg.edit_text(info_text, reply_markup=reply_markup, parse_mode="HTML")
        
        # Store menu message ID for later editing
        context.user_data[MENU_MESSAGE_ID] = status_msg.message_id
        
        return SELECTING_TAG
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        await status_msg.edit_text("❌ Error processing file. Please try again.")
        return WAITING_FILE


async def tag_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tag selection"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "edit_more":
        # Delete the choice message
        try:
            await query.message.delete()
        except:
            pass
        
        # Show full menu again
        filepath = context.user_data.get(CURRENT_FILE)
        
        if not filepath or not os.path.exists(filepath):
            await query.message.reply_text("❌ File not found. Please send a new file.")
            return WAITING_FILE
        
        tags = MusicTagEditor.get_tags(filepath)
        
        keyboard = [
            [InlineKeyboardButton("📝 Title", callback_data="edit_title")],
            [InlineKeyboardButton("👤 Artist", callback_data="edit_artist")],
            [InlineKeyboardButton("💿 Album", callback_data="edit_album")],
            [InlineKeyboardButton("📅 Year", callback_data="edit_year")],
            [InlineKeyboardButton("🎭 Genre", callback_data="edit_genre")],
            [InlineKeyboardButton("🖼 Album Cover", callback_data="edit_cover")],
            [InlineKeyboardButton("✅ Done", callback_data="done")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        cover_status = "✓ Set" if tags["has_cover"] else "✗ Not set"
        info_text = (
            f"<b>Current Tags:</b>\n\n"
            f"📝 Title: {tags['title']}\n"
            f"👤 Artist: {tags['artist']}\n"
            f"💿 Album: {tags['album']}\n"
            f"📅 Year: {tags['year']}\n"
            f"🎭 Genre: {tags['genre']}\n"
            f"🖼 Cover: {cover_status}\n\n"
            f"Select what you want to edit:"
        )
        
        await query.message.reply_text(info_text, reply_markup=reply_markup, parse_mode="HTML")
        return SELECTING_TAG
    
    elif query.data == "done":
        filepath = context.user_data.get(CURRENT_FILE)
        
        if filepath and os.path.exists(filepath):
            # Delete the menu message
            try:
                await query.message.delete()
            except:
                pass
            
            # Send edited file back
            status_msg = await query.message.reply_text("⏳ Preparing your edited file...")
            
            with open(filepath, "rb") as f:
                await query.message.reply_document(
                    document=f,
                    filename=os.path.basename(filepath),
                    caption="✅ Here's your edited file!"
                )
            
            # Delete status message
            try:
                await status_msg.delete()
            except:
                pass
            
            # Cleanup
            os.remove(filepath)
            context.user_data.clear()
            
            await query.message.reply_text(
                "Send me another file to edit, or use /start to see instructions."
            )
        
        return WAITING_FILE
    
    elif query.data == "edit_cover":
        # Delete the menu message
        try:
            await query.message.delete()
        except:
            pass
        
        await query.message.reply_text(
            "🖼 Send me an image file for the album cover.\n"
            "Supported formats: JPG, PNG, WEBP"
        )
        context.user_data[CURRENT_TAG] = "cover"
        return UPLOADING_COVER
    
    else:
        # Delete the menu message
        try:
            await query.message.delete()
        except:
            pass
        
        # Extract tag name from callback data
        tag_name = query.data.replace("edit_", "")
        context.user_data[CURRENT_TAG] = tag_name
        
        tag_labels = {
            "title": "Title",
            "artist": "Artist",
            "album": "Album",
            "year": "Year",
            "genre": "Genre"
        }
        
        await query.message.reply_text(
            f"✏️ Send me the new <b>{tag_labels[tag_name]}</b>:",
            parse_mode="HTML"
        )
        return EDITING_TAG


async def handle_tag_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tag value input"""
    new_value = update.message.text.strip()
    tag_name = context.user_data.get(CURRENT_TAG)
    filepath = context.user_data.get(CURRENT_FILE)
    
    if not filepath or not os.path.exists(filepath):
        await update.message.reply_text("❌ File not found. Please send a new file.")
        return WAITING_FILE
    
    # Update tag
    success = MusicTagEditor.set_tag(filepath, tag_name, new_value)
    
    if success:
        await update.message.reply_text(f"✅ {tag_name.capitalize()} updated successfully!")
    else:
        await update.message.reply_text(f"❌ Failed to update {tag_name}.")
    
    # Ask if user wants to edit more or finish
    keyboard = [
        [InlineKeyboardButton("📝 Edit More Tags", callback_data="edit_more")],
        [InlineKeyboardButton("✅ Done - Get File", callback_data="done")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "What would you like to do?",
        reply_markup=reply_markup
    )
    return SELECTING_TAG


async def handle_cover_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle album cover image upload"""
    message = update.message
    filepath = context.user_data.get(CURRENT_FILE)
    
    if not filepath or not os.path.exists(filepath):
        await message.reply_text("❌ File not found. Please send a new audio file.")
        return WAITING_FILE
    
    # Get photo
    if message.photo:
        photo = message.photo[-1]  # Get largest size
    elif message.document:
        photo = message.document
    else:
        await message.reply_text("Please send an image file (JPG, PNG, WEBP).")
        return UPLOADING_COVER
    
    try:
        # Download image
        status_msg = await message.reply_text("⏳ Processing image...")
        photo_file = await photo.get_file()
        image_bytes = await photo_file.download_as_bytearray()
        
        # Set cover
        success = MusicTagEditor.set_cover(filepath, bytes(image_bytes))
        
        # Re-read tags to get updated cover status
        tags = MusicTagEditor.get_tags(filepath)
        cover_status = "✓ Set" if tags and tags.get("has_cover") else "✗ Not set"
        
        if success:
            await status_msg.edit_text(f"✅ Album cover updated successfully!\n🖼 Cover: {cover_status}")
        else:
            await status_msg.edit_text("❌ Failed to update album cover.")
        
        # Ask if user wants to edit more or finish
        keyboard = [
            [InlineKeyboardButton("📝 Edit More Tags", callback_data="edit_more")],
            [InlineKeyboardButton("✅ Done - Get File", callback_data="done")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            "What would you like to do?",
            reply_markup=reply_markup
        )
        return SELECTING_TAG
        
    except Exception as e:
        logger.error(f"Error processing cover: {e}")
        await message.reply_text("❌ Error processing image. Please try another image.")
        return UPLOADING_COVER


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    filepath = context.user_data.get(CURRENT_FILE)
    if filepath and os.path.exists(filepath):
        os.remove(filepath)
    
    context.user_data.clear()
    await update.message.reply_text(
        "Operation cancelled. Send me a file to start editing, or use /start for help."
    )
    return WAITING_FILE


def main():
    """Start the bot"""
    # Get token from environment variable
    #TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TOKEN = '8481447861:AAH_jOifqkwxoTF6CMxawATJ4oCYz1R4fqE'
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set!")
        print("\nTo run this bot:")
        print("1. Get a token from @BotFather on Telegram")
        print("2. Set environment variable: export TELEGRAM_BOT_TOKEN='your_token_here'")
        print("3. Run this script again")
        return
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Setup conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.ATTACHMENT, handle_audio_file),
        ],
        states={
            WAITING_FILE: [
                MessageHandler(filters.ATTACHMENT, handle_audio_file),
            ],
            SELECTING_TAG: [
                CallbackQueryHandler(tag_selection),
            ],
            EDITING_TAG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tag_edit),
            ],
            UPLOADING_COVER: [
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_cover_upload),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    
    # Start bot
    print("Bot started! Send audio files to edit their tags.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
