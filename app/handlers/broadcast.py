from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters, CommandHandler
from app.database.models import Models
from app.config import Config
import asyncio

# States
BROADCAST_MESSAGE, BROADCAST_CONFIRM = range(2)




async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in Config.ADMIN_IDS:
        await query.answer("⚠️ Access Denied", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    
    text = (
        "**Broadcast Message** 📢\n\n"
        "Please send the message you want to broadcast to all users.\n"
        "Supported content: Text, Photo, Video, Document.\n\n"
        "Type /cancel to abort."
    )
    
    # Ask for message content
    await query.edit_message_text(text, parse_mode='Markdown')
    return BROADCAST_MESSAGE

async def broadcast_receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Save the message object to context to copy it later
    context.user_data['broadcast_message'] = update.message
    
    # Preview
    text = (
        "**Broadcast Preview** 👁️\n\n"
        "The message above will be sent to all active and restricted users.\n"
        "Are you sure you want to proceed?"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Send Broadcast", callback_data="broadcast_send")],
        [InlineKeyboardButton("❌ Cancel", callback_data="broadcast_cancel")]
    ]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return BROADCAST_CONFIRM

async def broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data
    
    if action == "broadcast_cancel":
        await query.edit_message_text("Broadcast cancelled.")
        # Return to admin menu logic could go here, or just stop.
        # Let's show the admin menu again for convenience.
        from app.handlers.admin import admin_maintenance
        # We need to trick admin_maintenance or just call a helper. 
        # Easier to just say cancelled and let them use /start or menu.
        # Or we can manually trigger the admin menu.
        return ConversationHandler.END
        
    if action == "broadcast_send":
        await query.edit_message_text("🚀 Sending broadcast... This may take a while.")
        
        message = context.user_data.get('broadcast_message')
        if not message:
            await query.edit_message_text("Error: Message expired.")
            return ConversationHandler.END
            
        users = await Models().users.get_all_users()
        # Filter for active/restricted
        targets = [u for u in users if u['status'] in ['active', 'restricted']]
        
        success_count = 0
        fail_count = 0
        
        import time
        
        batch_size = 5
        
        # Process in batches
        for i in range(0, len(targets), batch_size):
            batch = targets[i:i + batch_size]
            start_time = time.time()
            
            for user in batch:
                try:
                    await message.copy(chat_id=user['id'])
                    success_count += 1
                except Exception as e:
                    fail_count += 1
                    # Optional: Log failure
            
            # Ensure we don't exceed rate limit (1 second per batch of 5)
            elapsed = time.time() - start_time
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)
            
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=f"**Broadcast Complete** ✅\n\nSent: {success_count}\nFailed: {fail_count}",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def broadcast_cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Broadcast cancelled.")
    return ConversationHandler.END

broadcast_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(broadcast_start, pattern="^admin_maint_notify$")],
    states={
        BROADCAST_MESSAGE: [
            MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_receive_message)
        ],
        BROADCAST_CONFIRM: [
            CallbackQueryHandler(broadcast_confirm, pattern="^broadcast_(send|cancel)$")
        ]
    },
    fallbacks=[CommandHandler("cancel", broadcast_cancel_command)]
)
