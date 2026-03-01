from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler, filters
from app.database.models import Models
from app.utils.keyboards import main_menu_keyboard
from app.handlers.forward_list_handler import check_permissions
from app.utils.templates import get_schedule_prompt_text

SET_SCHEDULE = range(1)

async def start_schedule_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await check_permissions(query): return ConversationHandler.END
    
    fw_id = int(query.data.split(":")[1])
    text = get_schedule_prompt_text(fw_id)
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]),
        parse_mode='Markdown'
    )
    context.user_data['schedule_fw_id'] = fw_id
    return SET_SCHEDULE

async def set_schedule_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    fw_id = context.user_data.get('schedule_fw_id')
    
    if not fw_id:
        await update.message.reply_text("Error: Forward ID lost. Please try again.")
        return ConversationHandler.END
        
    if text.lower() == 'off':
        await Models().forwards.set_schedule_time(fw_id, None)
        await update.message.reply_text("✅ Scheduling disabled.", reply_markup=main_menu_keyboard(False))
    else:
        # Validate HH:MM
        try:
            import time
            time.strptime(text, '%H:%M')
            await Models().forwards.set_schedule_time(fw_id, text)
            await update.message.reply_text(f"✅ Schedule set to {text} daily.", reply_markup=main_menu_keyboard(False))
        except ValueError:
            await update.message.reply_text("❌ Invalid format. Please use HH:MM (e.g., 14:30). Try again or /cancel.")
            return SET_SCHEDULE
            
    return ConversationHandler.END

async def cancel_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Cancelled.", reply_markup=main_menu_keyboard(False))
    else:
        await update.message.reply_text("Cancelled.", reply_markup=main_menu_keyboard(False))
    return ConversationHandler.END

schedule_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_schedule_flow, pattern="^fw_schedule:")],
    states={
        SET_SCHEDULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_schedule_time)]
    },
    fallbacks=[
        CommandHandler("cancel", cancel_schedule),
        CallbackQueryHandler(cancel_schedule, pattern="^cancel_conv$")
    ]
)
