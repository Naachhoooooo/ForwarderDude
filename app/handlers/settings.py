from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters, CommandHandler
from app.database.models import Models
from app.utils.keyboards import main_menu_keyboard
from app.logger import get_logger

logger = get_logger(__name__)




# States
SET_HEADER, SET_FOOTER = range(2)

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    
    if query:
        await query.answer()
    
    header = await Models().system.get_setting(f"user:{user_id}:header", "None")
    footer = await Models().system.get_setting(f"user:{user_id}:footer", "None")
    
    text = (
        "**Settings**\n\n"
        f"Header: {header}\n"
        f"Footer: {footer}\n\n"
        "Select an option to change:"
    )
    # We are parsing with MarkdownV2 for safety, but existing legacy code used Markdown.
    # Since header/footer are now escaped with version=2, we need to enforce that here or simply escape the hardcoded parts.
    # Let's switch the whole menu to MarkdownV2 to properly handle escaped user inputs.
    text_v2 = (
        "*Settings*\n\n"
        f"Header: {header}\n"
        f"Footer: {footer}\n\n"
        "Select an option to change:"
    )
    
    keyboard = [
        [InlineKeyboardButton("Set Header", callback_data="set_header")],
        [InlineKeyboardButton("Set Footer", callback_data="set_footer")],
        [InlineKeyboardButton("⏎ Back", callback_data="main_menu")]
    ]
    
    if query:
        await query.edit_message_text(text_v2, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')
    else:
        await update.message.reply_text(text_v2, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')

async def start_set_header(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Send the new Header text (or 'none' to clear).",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]])
    )
    return SET_HEADER

async def save_header(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    from telegram.helpers import escape_markdown
    
    value = "" if text.lower() == 'none' else escape_markdown(text, version=2)
    await Models().system.set_setting(f"user:{user_id}:header", value)
    logger.info(f"User {user_id} updated header setting")
    
    await update.message.reply_text("Header saved.", reply_markup=main_menu_keyboard(False))
    return ConversationHandler.END

async def start_set_footer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Send the new Footer text (or 'none' to clear).",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]])
    )
    return SET_FOOTER

async def save_footer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    from telegram.helpers import escape_markdown
    
    value = "" if text.lower() == 'none' else escape_markdown(text, version=2)
    await Models().system.set_setting(f"user:{user_id}:footer", value)
    logger.info(f"User {user_id} updated footer setting")
    
    await update.message.reply_text("Footer saved.", reply_markup=main_menu_keyboard(False))
    return ConversationHandler.END

async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer("✅ Settings Saved")
        await query.edit_message_text("Cancelled.", reply_markup=main_menu_keyboard(False))
    else:
        await update.message.reply_text("Cancelled.", reply_markup=main_menu_keyboard(False))
    return ConversationHandler.END

settings_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_set_header, pattern="^set_header$"),
        CallbackQueryHandler(start_set_footer, pattern="^set_footer$"),
        CallbackQueryHandler(settings_menu, pattern="^menu_settings$"),
        CommandHandler("settings", settings_menu)
    ],
    states={
        SET_HEADER: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_header)],
        SET_FOOTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_footer)]
    },
    fallbacks=[
        CommandHandler("cancel", cancel_settings),
        CallbackQueryHandler(cancel_settings, pattern="^cancel_conv$")
    ]
)
