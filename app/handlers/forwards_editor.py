import math
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.error import TimedOut

from app.database.models import Models
from app.utils.keyboards import chat_selection_keyboard
from app.handlers.forwards_lister import check_permissions, forward_detail, list_forwards
from app.utils.templates import (
    get_clear_dest_text,
    get_edit_dest_text,
    get_edit_source_text,
    get_forward_rules_text
)
from app.logger import get_logger

logger = get_logger('forwards')

EDIT_DEST, EDIT_SOURCE = range(1, 3)

async def handle_fw_test(update: Update, context: ContextTypes.DEFAULT_TYPE, query, fw_id: int):
    details, dests = await Models().forwards.get_forward_details(fw_id)
    if not details: return
    
    success_count = 0
    for dest in dests:
        try:
            await context.bot.send_message(chat_id=dest['dest_id'], text="**Test - Forwarder Dude**", parse_mode='Markdown')
            success_count += 1
        except TimedOut:
             logger.warning(f"Test timed out for {dest['dest_id']}")
        except Exception as e:
             logger.error(f"Test failed for {dest['dest_id']}: {e}")
    
    logger.info(f"User {update.effective_user.id} initiated test for Forward {fw_id}")
    
    if success_count < len(dests):
         await query.answer(f"⚠️ Test finished with failures ({success_count}/{len(dests)} sent).", show_alert=True)
    else:
         await query.answer(f"✅ Test Sent to {success_count} Destinations", show_alert=False)

async def handle_fw_clear_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, query, fw_id: int):
    _, dests = await Models().forwards.get_forward_details(fw_id)
    keyboard = []
    if len(dests) > 0:
        keyboard.append([InlineKeyboardButton(f"Clear D1: {dests[0]['title']}", callback_data=f"fw_clear_dest:{fw_id}:1")])
    if len(dests) > 1:
        keyboard.append([InlineKeyboardButton(f"Clear D2: {dests[1]['title']}", callback_data=f"fw_clear_dest:{fw_id}:2")])
    if len(dests) > 1:
        keyboard.append([InlineKeyboardButton("🗑️ Clear Both", callback_data=f"fw_clear_dest:{fw_id}:0")])
    keyboard.append([InlineKeyboardButton("⏎ Back", callback_data=f"fw_detail:{fw_id}")])
    
    await query.edit_message_text(
        get_clear_dest_text(),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_fw_clear_dest(update: Update, context: ContextTypes.DEFAULT_TYPE, query, parts: list):
    fw_id = int(parts[1])
    pos = int(parts[2])
    
    if pos == 0:
        await Models().forwards.clear_destination(fw_id, 1)
        await Models().forwards.clear_destination(fw_id, 2)
        await query.answer("✅ Both destinations cleared", show_alert=False)
    else:
        await Models().forwards.clear_destination(fw_id, pos)
        await query.answer(f"✅ D{pos} cleared", show_alert=False)
    
    await forward_detail(update, context, fw_id=fw_id)

async def show_edit_dest_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chats = await Models().chats.get_user_chats(user_id)
    
    fw_id = context.user_data['edit_fw_id']
    details, _ = await Models().forwards.get_forward_details(fw_id)
    chats = [c for c in chats if c['id'] != details['source_id']]
    
    page = context.user_data.get('setup_page', 0)
    per_page = 5
    total_pages = math.ceil(len(chats) / per_page)
    start = page * per_page
    end = start + per_page
    current_chats = chats[start:end]
    
    keyboard = chat_selection_keyboard(current_chats, page, total_pages, "edit_dest")
    pos = context.user_data['edit_fw_pos']
    text = get_edit_dest_text(pos)
    await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def edit_dest_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer("Select destination chat...")
    except Exception: pass
    
    data = query.data
    if data == "cancel_setup":
        fw_id = context.user_data['edit_fw_id']
        await forward_detail(update, context, fw_id=fw_id)
        return ConversationHandler.END

    if "_page:" in data:
        page = int(data.split(":")[1])
        context.user_data['setup_page'] = page
        await show_edit_dest_selection(update, context)
        return EDIT_DEST
        
    chat_id = int(data.split(":")[1])
    fw_id = context.user_data['edit_fw_id']
    pos = context.user_data['edit_fw_pos']
    
    await Models().forwards.add_destination(fw_id, chat_id, pos)
    await query.answer("✅ Destination updated", show_alert=False)
    await forward_detail(update, context, fw_id=fw_id)
    return ConversationHandler.END

async def show_edit_source_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chats = await Models().chats.get_user_chats(user_id)
    
    page = context.user_data.get('setup_page', 0)
    per_page = 5
    total_pages = math.ceil(len(chats) / per_page)
    start = page * per_page
    end = start + per_page
    current_chats = chats[start:end]
    
    keyboard = chat_selection_keyboard(current_chats, page, total_pages, "edit_src")
    text = get_edit_source_text()
    await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def edit_source_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Select source chat...")
    data = query.data
    
    if data == "cancel_setup":
        fw_id = context.user_data['edit_fw_id']
        await forward_detail(update, context, fw_id=fw_id)
        return ConversationHandler.END

    if "_page:" in data:
        page = int(data.split(":")[1])
        context.user_data['setup_page'] = page
        await show_edit_source_selection(update, context)
        return EDIT_SOURCE
        
    chat_id = int(data.split(":")[1])
    fw_id = context.user_data['edit_fw_id']
    
    await Models().db.execute('UPDATE forwards SET source_id = ? WHERE id = ?', (chat_id, fw_id))
    await query.answer("✅ Source updated", show_alert=False)
    await forward_detail(update, context, fw_id=fw_id)
    return ConversationHandler.END

edit_forward_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(show_edit_dest_entry, pattern="^fw_edit_dest:"),
        CallbackQueryHandler(show_edit_source_entry, pattern="^fw_chg_src:")
    ],
    states={
        EDIT_DEST: [CallbackQueryHandler(edit_dest_selected, pattern="^edit_dest")],
        EDIT_SOURCE: [CallbackQueryHandler(edit_source_selected, pattern="^edit_src")]
    },
    fallbacks=[CallbackQueryHandler(edit_dest_selected, pattern="^cancel_setup$")]
)

async def show_edit_dest_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await check_permissions(query): return ConversationHandler.END
    parts = query.data.split(":")
    context.user_data['edit_fw_id'] = int(parts[1])
    context.user_data['edit_fw_pos'] = int(parts[2])
    context.user_data['setup_page'] = 0
    await show_edit_dest_selection(update, context)
    return EDIT_DEST

async def show_edit_source_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await check_permissions(query): return ConversationHandler.END
    context.user_data['edit_fw_id'] = int(query.data.split(":")[1])
    context.user_data['setup_page'] = 0
    await show_edit_source_selection(update, context)
    return EDIT_SOURCE

async def forward_rules_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, fw_id: int):
    query = update.callback_query
    details, _ = await Models().forwards.get_forward_details(fw_id)
    
    try: filters = json.loads(details['filters'])
    except Exception: filters = []
    
    content_types = ["text", "image", "video", "audio", "document", "sticker"]
    keyboard = []
    
    row = []
    for ct in content_types:
        status = "✅" if ct in filters else "❌"
        row.append(InlineKeyboardButton(f"{status} {ct.title()}", callback_data=f"fw_rule:{fw_id}:{ct}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row: keyboard.append(row)
        
    sender_status = "✅ Show Sender" if "sender" in filters else "❌ Show Sender"
    keyboard.append([InlineKeyboardButton(sender_status, callback_data=f"fw_rule:{fw_id}:sender")])
    keyboard.append([InlineKeyboardButton("⏎ Back", callback_data=f"fw_detail:{fw_id}")])
    
    text = get_forward_rules_text(details)
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_fw_rule(update: Update, context: ContextTypes.DEFAULT_TYPE, query, parts: list):
    fw_id = int(parts[1])
    rule_type = parts[2]
    
    details, _ = await Models().forwards.get_forward_details(fw_id)
    try: filters = json.loads(details['filters'])
    except Exception: filters = []
    
    if rule_type == "sender":
        if "sender" in filters: filters.remove("sender")
        else: filters.append("sender")
    else:
        if rule_type in filters: filters.remove(rule_type)
        else: filters.append(rule_type)
    
    await Models().db.execute('UPDATE forwards SET filters = ? WHERE id = ?', (json.dumps(filters), fw_id))
    await forward_rules_menu(update, context, fw_id)

async def handle_fw_toggles(update: Update, context: ContextTypes.DEFAULT_TYPE, query, action: str, fw_id: int):
    if action == "fw_pause":
        await Models().forwards.toggle_pause(fw_id)
        logger.info(f"Forward {fw_id} paused/resumed by user {update.effective_user.id}")
        await query.answer("✅ Status Updated", show_alert=False)
        await forward_detail(update, context, fw_id=fw_id)
        
    elif action == "fw_delete":
        await Models().forwards.delete_forward(fw_id)
        logger.info(f"Forward {fw_id} deleted by user {update.effective_user.id}")
        await query.answer("🗑️ Forward Deleted", show_alert=False)
        await list_forwards(update, context)
        
    elif action == "fw_header":
        details, _ = await Models().forwards.get_forward_details(fw_id)
        await Models().forwards.set_forward_flags(fw_id, header_enabled=not details['header_enabled'])
        await query.answer("✅ Header Toggled", show_alert=False)
        await forward_detail(update, context, fw_id=fw_id)
        
    elif action == "fw_footer":
        details, _ = await Models().forwards.get_forward_details(fw_id)
        await Models().forwards.set_forward_flags(fw_id, footer_enabled=not details['footer_enabled'])
        await query.answer("✅ Footer Toggled", show_alert=False)
        await forward_detail(update, context, fw_id=fw_id)
        
    elif action == "fw_rules":
        await forward_rules_menu(update, context, fw_id)

async def forward_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await check_permissions(query): return
    
    data = query.data
    
    if data.startswith("fw_test:"):
        return await handle_fw_test(update, context, query, int(data.split(":")[1]))
        
    if data.startswith("fw_clear_menu:"):
        return await handle_fw_clear_menu(update, context, query, int(data.split(":")[1]))
        
    if data.startswith("fw_clear_dest:"):
        return await handle_fw_clear_dest(update, context, query, data.split(":"))
        
    if data.startswith("fw_rule:"):
        return await handle_fw_rule(update, context, query, data.split(":"))

    try:
        action, fw_id = data.split(":")
        fw_id = int(fw_id)
    except ValueError:
        return
        
    return await handle_fw_toggles(update, context, query, action, fw_id)
