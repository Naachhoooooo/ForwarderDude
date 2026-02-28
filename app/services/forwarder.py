from telegram import Update
from telegram.ext import ContextTypes
from app.database.models import Models
from app.config import Config
from app.logger import get_logger
from app.services.message_queue import get_message_queue
import json

logger = get_logger('forwards')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle incoming messages and enqueue them for forwarding.
    Uses queue system for guaranteed delivery.
    """
    message = update.effective_message
    if not message:
        return

    # Ignore messages from the bot itself
    if message.from_user and message.from_user.id == context.bot.id:
        return

    models = Models()
    maintenance_mode = await models.system.get_setting("maintenance_mode", "off") 
    
    source_id = message.chat.id
    forwards = await models.forwards.get_forwards_by_source(source_id)
    
    if not forwards:
        return

    # Filter forwards based on maintenance mode
    if maintenance_mode == "on":
        forwards = [fw for fw in forwards if fw['user_id'] in Config.ADMIN_IDS]
        
    if not forwards:
        return
    
    # Determine message type
    msg_type = 'text'
    if message.photo:
        msg_type = 'image'
    elif message.video:
        msg_type = 'video'
    elif message.audio or message.voice:
        msg_type = 'audio'
    elif message.document:
        msg_type = 'document'
    elif message.sticker:
        msg_type = 'sticker'
    
    message_queue = get_message_queue()
    
    # Cache to prevent N+1 queries on user settings
    settings_cache = {}
    async def get_cached_setting(key, default=""):
        if key not in settings_cache:
            settings_cache[key] = await models.system.get_setting(key, default)
        return settings_cache[key]

    for fw in forwards:
        # Check if forward is paused
        if fw['paused']:
            continue
        
        # Apply content filters
        filters = json.loads(fw['filters'])
        if msg_type not in filters:
            continue

        # Get header/footer settings
        header_text = await get_cached_setting(
            f"user:{fw['user_id']}:header", ""
        ) if fw['header_enabled'] else ""
        
        footer_text = await get_cached_setting(
            f"user:{fw['user_id']}:footer", ""
        ) if fw['footer_enabled'] else ""
        
        # Prepare text and caption with header/footer
        caption = message.caption or ""
        text = message.text or ""
        
        final_text = text
        if header_text:
            final_text = f"{header_text}\n\n{final_text}"
        if footer_text:
            final_text = f"{final_text}\n\n{footer_text}"
        
        final_caption = caption
        if header_text:
            final_caption = f"{header_text}\n\n{final_caption}"
        if footer_text:
            final_caption = f"{final_caption}\n\n{footer_text}"

        # Handle scheduled forwards (buffered)
        if fw['schedule_time']:
            await models.forwards.add_to_buffer(
                fw['id'],
                message.message_id,
                source_id,
                msg_type,
                text,
                caption
            )
            logger.info(f"Buffered message {message.message_id} for scheduled forward {fw['id']}")
            continue

        # Enqueue for each destination
        for dest_id in fw['dest_ids']:
            try:
                # Determine if sender info should be shown
                forward_mode = "sender" in filters
                
                # Prepare message data
                message_data = {
                    'text': final_text,
                    'caption': final_caption,
                    'forward_mode': forward_mode
                }
                
                # Enqueue message for guaranteed delivery
                queue_id = await message_queue.enqueue(
                    forward_id=fw['id'],
                    dest_chat_id=dest_id,
                    source_chat_id=source_id,
                    source_message_id=message.message_id,
                    message_type=msg_type,
                    message_data=message_data,
                    priority=0  # Normal priority
                )
                
                logger.debug(
                    f"Enqueued message {message.message_id} "
                    f"from {source_id} to {dest_id} (queue_id: {queue_id})"
                )
                
            except Exception as e:
                logger.error(
                    f"Failed to enqueue message {message.message_id} "
                    f"from {source_id} to {dest_id}: {e}"
                )
