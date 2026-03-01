from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from app.database.models import Models
from app.utils.keyboards import chat_selection_keyboard, main_menu_keyboard
from app.logger import system_logger
import math

# States
SELECT_SOURCE, SELECT_DEST, INPUT_NAME, SETUP_RULES = range(4)

async def start_new_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.callback_query:
        query = update.callback_query
        await query.answer("Starting new forward setup...")
    
    chats = await Models().chats.get_user_chats(user_id)
    
    if not chats:
        text = (
            "You haven't added me to any chats yet.\n"
            "Please add me to the source and destination chats first."
        )
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=main_menu_keyboard(False))
        else:
            await update.message.reply_text(text, reply_markup=main_menu_keyboard(False))
        return ConversationHandler.END

    context.user_data['setup_page'] = 0
    await show_source_selection(update, context)
    return SELECT_SOURCE

async def show_source_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chats = await Models().chats.get_user_chats(user_id)
    page = context.user_data.get('setup_page', 0)
    per_page = 5
    total_pages = math.ceil(len(chats) / per_page)
    
    start = page * per_page
    end = start + per_page
    current_chats = chats[start:end]
    
    keyboard = chat_selection_keyboard(current_chats, page, total_pages, "sel_src")
    
    text = "*Step 1/3: Select Source Chat*\n\nChoose the chat you want to forward messages FROM:"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def source_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Select source channel or group...")
    data = query.data
    
    if data == "cancel_setup":
        await query.edit_message_text("Setup cancelled.", reply_markup=main_menu_keyboard(False))
        return ConversationHandler.END
        
    if "_page:" in data:
        page = int(data.split(":")[1])
        context.user_data['setup_page'] = page
        await show_source_selection(update, context)
        return SELECT_SOURCE
        
    chat_id = int(data.split(":")[1])
    context.user_data['new_forward_source'] = chat_id
    context.user_data['setup_page'] = 0 # Reset for dest
    
    await show_dest_selection(update, context)
    return SELECT_DEST

async def show_dest_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chats = await Models().chats.get_user_chats(user_id)
    # Filter out source chat from destination options
    source_id = context.user_data.get('new_forward_source')
    chats = [c for c in chats if c['id'] != source_id]
    
    page = context.user_data.get('setup_page', 0)
    per_page = 5
    total_pages = math.ceil(len(chats) / per_page)
    
    start = page * per_page
    end = start + per_page
    current_chats = chats[start:end]
    
    keyboard = chat_selection_keyboard(current_chats, page, total_pages, "sel_dest")
    
    text = "*Step 2/3: Select Destination Chat*\n\nChoose the chat you want to forward messages TO:"
    await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def dest_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Select first destination...")
    data = query.data
    
    if data == "cancel_setup":
        await query.edit_message_text("Setup cancelled.", reply_markup=main_menu_keyboard(False))
        return ConversationHandler.END

    if "_page:" in data:
        page = int(data.split(":")[1])
        context.user_data['setup_page'] = page
        await show_dest_selection(update, context)
        return SELECT_DEST
        
    chat_id = int(data.split(":")[1])
    context.user_data['new_forward_dest'] = chat_id
    
    # Ask for Name
    await query.edit_message_text(
        "*Step 3/3: Name this Forward*\n\n"
        "Please enter a name for this rule (e.g., 'My Channel -> Group').",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]),
        parse_mode='Markdown'
    )
    return INPUT_NAME

async def save_forward_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    user_id = update.effective_user.id
    source_id = context.user_data['new_forward_source']
    dest_id = context.user_data['new_forward_dest']
    
    from telegram.helpers import escape_markdown
    name_sanitized = escape_markdown(name, version=2)
    
    # Create Forward
    fw_id = await Models().forwards.create_forward(user_id, source_id, name_sanitized, ["text","image","video","audio","document","sticker"])
    await Models().forwards.add_destination(fw_id, dest_id, 1)
    context.user_data['new_fw_id'] = fw_id
    
    system_logger.info(f"User {user_id} created new forward rule '{name}' from {source_id} to {dest_id}")
    
    # Proceed to Rules Setup
    await show_setup_rules(update, context)
    return SETUP_RULES

async def show_setup_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fw_id = context.user_data.get('new_fw_id')
    details, dests = await Models().forwards.get_forward_details(fw_id)
    import json
    filters = json.loads(details['filters'])
    
    # Content types
    content_types = ["text", "image", "video", "audio", "document", "sticker"]
    
    keyboard = []
    
    # Grid of content types (2 per row)
    row = []
    for ct in content_types:
        status = "✅" if ct in filters else "❌"
        row.append(InlineKeyboardButton(f"{status} {ct.title()}", callback_data=f"setup_rule:{ct}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    # Sender Toggle
    sender_status = "✅ Show Sender" if "sender" in filters else "❌ Show Sender"
    keyboard.append([InlineKeyboardButton(sender_status, callback_data=f"setup_rule:sender")])
    
    # Done Button
    keyboard.append([InlineKeyboardButton("✔ Save", callback_data="setup_done")])
    
    text = (
        f"*Step 4/4: Configure Rules*\n\n"
        "Forward created! Now customize what to forward.\n"
        "Tap to toggle:"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def setup_rule_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Select second destination (optional)...")
    data = query.data
    
    fw_id = context.user_data.get('new_fw_id')
    rule_type = data.split(":")[1]
    
    details, dests = await Models().forwards.get_forward_details(fw_id)
    import json
    filters = json.loads(details['filters'])
    
    if rule_type == "sender":
        if "sender" in filters: filters.remove("sender")
        else: filters.append("sender")
    else:
        if rule_type in filters: filters.remove(rule_type)
        else: filters.append(rule_type)
    
    await Models().db.execute('UPDATE forwards SET filters = ? WHERE id = ?', (json.dumps(filters), fw_id))
    
    await show_setup_rules(update, context)
    return SETUP_RULES

async def setup_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Configure content filters...")
    
    await query.edit_message_text(
        "✅ *Forward Setup Complete!*\n\n"
        "Your new forward rule is active and saved.",
        reply_markup=main_menu_keyboard(False),
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.edit_message_text("Cancelled.", reply_markup=main_menu_keyboard(False))
    else:
        await update.message.reply_text("Cancelled.", reply_markup=main_menu_keyboard(False))
    return ConversationHandler.END

from telegram.ext import MessageHandler, filters

new_forward_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_new_forward, pattern="^menu_new$"),
        CommandHandler("newforward", start_new_forward)
    ],
    states={
        SELECT_SOURCE: [CallbackQueryHandler(source_selected, pattern="^sel_src")],
        SELECT_DEST: [CallbackQueryHandler(dest_selected, pattern="^sel_dest")],
        INPUT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_forward_name)],
        SETUP_RULES: [
            CallbackQueryHandler(setup_rule_action, pattern="^setup_rule:"),
            CallbackQueryHandler(setup_done, pattern="^setup_done$")
        ]
    },
    fallbacks=[
        CallbackQueryHandler(source_selected, pattern="^cancel_setup$"), # Back/Cancel
        CallbackQueryHandler(cancel, pattern="^cancel_conv$"),
        CommandHandler("cancel", cancel)
    ]
)
