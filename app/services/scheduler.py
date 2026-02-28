import logging
from telegram.ext import ContextTypes
from app.database.models import Models
from app.services.message_queue import get_message_queue
from datetime import datetime
import json

logger = logging.getLogger(__name__)



async def check_schedules(context: ContextTypes.DEFAULT_TYPE):
    """Job to check for scheduled forwards and process buffer."""
    models = Models()
    now_str = datetime.now().strftime("%H:%M")
    
    forwards = await models.forwards.get_scheduled_forwards(now_str)
    if not forwards:
        return

    for fw in forwards:
        logger.info(f"Processing schedule for forward {fw['id']} at {now_str}")
        
        # Get buffered messages
        messages = await models.forwards.get_buffered_messages(fw['id'])
        if not messages:
            continue
            
        # Get destinations
        details, dests = await models.forwards.get_forward_details(fw_id=fw['id'])
        dest_ids = [d['dest_id'] for d in dests]
        
        # Get settings
        header_text = await models.system.get_setting(f"user:{fw['user_id']}:header", "") if fw['header_enabled'] else ""
        footer_text = await models.system.get_setting(f"user:{fw['user_id']}:footer", "") if fw['footer_enabled'] else ""
        
        filters = json.loads(fw['filters'])

        for msg in messages:
            # Reconstruct content
            text = msg['text']
            caption = msg['caption']
            msg_type = msg['msg_type']
            
            final_text = text
            if header_text: final_text = f"{header_text}\n\n{final_text}"
            if footer_text: final_text = f"{final_text}\n\n{footer_text}"
            
            final_caption = caption
            if header_text: final_caption = f"{header_text}\n\n{final_caption}"
            if footer_text: final_caption = f"{final_caption}\n\n{footer_text}"

            for dest_id in dest_ids:
                try:
                    forward_mode = "sender" in filters
                    message_data = {
                        'text': final_text,
                        'caption': final_caption,
                        'forward_mode': forward_mode
                    }
                    
                    message_queue = get_message_queue()
                    await message_queue.enqueue(
                        forward_id=fw['id'],
                        dest_chat_id=dest_id,
                        source_chat_id=msg['source_chat_id'],
                        source_message_id=msg['source_message_id'],
                        message_type=msg_type,
                        message_data=message_data,
                        priority=0
                    )
                except Exception as e:
                    logger.error(f"Failed to enqueue buffered message to {dest_id}: {e}")
        
        # Clear buffer after processing
        await models.forwards.clear_buffer(fw['id'])
