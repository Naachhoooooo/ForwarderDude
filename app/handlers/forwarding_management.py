from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler, MessageHandler, CommandHandler, filters
from app.database.models import Models
from app.utils.keyboards import main_menu_keyboard

# Conversation states
SET_SCHEDULE = range(1)




async def list_forwards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    
    if query:
        await query.answer()

    # Check Restriction
    user = await Models().users.get_user(user_id)
    if user and user['status'] == 'restricted':
        if query:
            await query.answer("⛔ Access Restricted", show_alert=True)
        else:
            await update.message.reply_text("⛔ Your account is restricted.")
        return
        
    forwards = await Models().forwards.get_user_forwards(user_id)
    
    if not forwards:
        text = (
            "*No Forwards Yet* 🤷‍♂️\n\n"
            "It looks like you haven't set up any rules.\n"
            "Click *[➕ New Forward]* in the main menu to get started!"
        )
        if query:
            try:
                await query.edit_message_text(text, reply_markup=main_menu_keyboard(False), parse_mode='Markdown')
            except BadRequest: pass
        else:
            await update.message.reply_text(text, reply_markup=main_menu_keyboard(False), parse_mode='Markdown')
        return
        

    import math
    from app.utils.keyboards import paginated_keyboard
    
    page = 0
    if query and query.data.startswith("fw_list_page:"):
        page = int(query.data.split(":")[1])
        
    per_page = 6
    total_pages = math.ceil(len(forwards) / per_page)
    
    start = page * per_page
    end = start + per_page
    current_forwards = forwards[start:end]
    
    items = []
    for fw in current_forwards:
        status = "▐▐" if fw['paused'] else "▶"
        items.append({
            'text': f"{status} {fw['name']}",
            'callback_data': f"fw_detail:{fw['id']}"
        })
        
    header_text = (
        "📂 *Your Forwards*\n"
        "──────────────\n"
        "Tap an item to manage or edit:"
    )
    
    if query:
        try:
            await query.edit_message_text(
                header_text,
                reply_markup=paginated_keyboard(items, page, total_pages, "fw_list"),
                parse_mode='Markdown'
            )
        except BadRequest:
            pass # Message not modified
    else:
        await update.message.reply_text(
            header_text,
            reply_markup=paginated_keyboard(items, page, total_pages, "fw_list"),
            parse_mode='Markdown'
        )

async def forward_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, fw_id: int = None):
    query = update.callback_query
    
    if fw_id is None:
        if query.data.startswith("fw_detail:"):
            fw_id = int(query.data.split(":")[1])
        else:
            return # Should not happen if routed correctly
    
    details, dests = await Models().forwards.get_forward_details(fw_id)
    if not details:
        await query.answer("⚠️ Forward Not Found", show_alert=True)
        return


    status_icon = "🔴" if details['paused'] else "🟢"
    status_text = "Paused" if details['paused'] else "Active"
    source_chat = details['source_title'] or "Unknown"
    
    dest_text = ""
    if not dests:
        dest_text = " None"
    else:
        for i, dest in enumerate(dests, 1):
            dest_text += f"\n   └ {dest['title']}"
    
    import json
    try:
        filters_list = json.loads(details['filters'])
    except:
        filters_list = []
        

    content_filters = [f.title() for f in filters_list if f != 'sender']
    filters_str = ", ".join(content_filters) if content_filters else "None"
    
    sender_mode = "Show Sender" if "sender" in filters_list else "Hide Sender (Copy)"
    
    schedule_line = ""
    if details['schedule_time']:
        schedule_line = f"• Schedule: 🕒 {details['schedule_time']}\n"
    
    text = (
        f"📱 *{details['name']}*\n"
        f"──────────────\n"
        f"{status_icon} *Status:* {status_text}\n"
        f"📤 *Source:* {source_chat}\n"
        f"📥 *Destination(s):*{dest_text}\n\n"
        f"⚙️ *Configuration*\n"
        f"• Filters: {filters_str}\n"
        f"• Mode: {sender_mode}\n"
        f"{schedule_line}"
    )
    

    pause_label = "▶ Resume" if details['paused'] else "▐▐  Pause"
    
    keyboard = []
    keyboard.append([InlineKeyboardButton(pause_label, callback_data=f"fw_pause:{fw_id}")])
    keyboard.append([InlineKeyboardButton("📝 Edit Filters", callback_data=f"fw_rules:{fw_id}")])
    
    # Toggle style buttons
    header_state = "🟢" if details['header_enabled'] else "⚪"
    footer_state = "🟢" if details['footer_enabled'] else "⚪"
    
    keyboard.append([
        InlineKeyboardButton(f"Header {header_state}", callback_data=f"fw_header:{fw_id}"),
        InlineKeyboardButton(f"Footer {footer_state}", callback_data=f"fw_footer:{fw_id}")
    ])
    
    # Dest 1
    dest1_name = dests[0]['title'] if len(dests) > 0 else "Not Set"
    keyboard.append([InlineKeyboardButton(f"D1: {dest1_name}", callback_data=f"fw_edit_dest:{fw_id}:1")])
    
    # Dest 2
    dest2_name = dests[1]['title'] if len(dests) > 1 else "Not Set"
    keyboard.append([InlineKeyboardButton(f"D2: {dest2_name}", callback_data=f"fw_edit_dest:{fw_id}:2")])
    
    # Clear Destination button (only show if at least one destination is set)
    if len(dests) > 0:
        keyboard.append([InlineKeyboardButton("🗑️ Clear Destination", callback_data=f"fw_clear_menu:{fw_id}")])
    
    
    keyboard.append([InlineKeyboardButton("♻ Change Source", callback_data=f"fw_chg_src:{fw_id}")])
    keyboard.append([
        InlineKeyboardButton("🧪 Test", callback_data=f"fw_test:{fw_id}"),
        InlineKeyboardButton(f"🕒 Schedule", callback_data=f"fw_schedule:{fw_id}")
    ])
    keyboard.append([InlineKeyboardButton("Delete", callback_data=f"fw_delete:{fw_id}")])
    keyboard.append([InlineKeyboardButton("⏎ Back", callback_data="menu_forwards")])
    
    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except:
        # If message content is same, ignore
        pass

async def check_permissions(query) -> bool:
    from app.database.models import Models
    from app.config import Config
    models = Models()
    maintenance_mode = await models.system.get_setting("maintenance_mode", "off")
    user_id = query.from_user.id
    is_admin = user_id in Config.ADMIN_IDS
    
    if maintenance_mode == "on" and not is_admin:
        notice = await models.system.get_setting("maintenance_notice", "The bot is currently under maintenance. Please try again later.")
        await query.answer(f"🚧 Maintenance Mode - Activated\n\n{notice}\n\nWe are very sorry for the inconvenience", show_alert=True)
        return False
    
    if user_id not in Config.ADMIN_IDS:
        user = await Models().users.get_user(user_id)
        if user and user['status'] == 'restricted':
            await query.answer("⛔ Access Restricted", show_alert=True)
            return False
            
    return True

async def handle_fw_test(update: Update, context: ContextTypes.DEFAULT_TYPE, query, fw_id: int):
    details, dests = await Models().forwards.get_forward_details(fw_id)
    if not details: return
    
    success_count = 0
    from telegram.error import TimedOut
    from app.logger import get_logger
    logger = get_logger('forwards')
    
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
    details, dests = await Models().forwards.get_forward_details(fw_id)
    keyboard = []
    if len(dests) > 0:
        keyboard.append([InlineKeyboardButton(f"Clear D1: {dests[0]['title']}", callback_data=f"fw_clear_dest:{fw_id}:1")])
    if len(dests) > 1:
        keyboard.append([InlineKeyboardButton(f"Clear D2: {dests[1]['title']}", callback_data=f"fw_clear_dest:{fw_id}:2")])
    if len(dests) > 1:
        keyboard.append([InlineKeyboardButton("🗑️ Clear Both", callback_data=f"fw_clear_dest:{fw_id}:0")])
    keyboard.append([InlineKeyboardButton("⏎ Back", callback_data=f"fw_detail:{fw_id}")])
    
    await query.edit_message_text(
        "*Clear Destination*\n\nSelect which destination(s) to clear:",
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

async def handle_fw_rule(update: Update, context: ContextTypes.DEFAULT_TYPE, query, parts: list):
    fw_id = int(parts[1])
    rule_type = parts[2]
    
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
    await forward_rules_menu(update, context, fw_id)

async def handle_fw_toggles(update: Update, context: ContextTypes.DEFAULT_TYPE, query, action: str, fw_id: int):
    from app.logger import get_logger
    logger = get_logger('forwards')
    
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
        details, dests = await Models().forwards.get_forward_details(fw_id)
        await Models().forwards.set_forward_flags(fw_id, header_enabled=not details['header_enabled'])
        await query.answer("✅ Header Toggled", show_alert=False)
        await forward_detail(update, context, fw_id=fw_id)
        
    elif action == "fw_footer":
        details, dests = await Models().forwards.get_forward_details(fw_id)
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
        
    if data.startswith("fw_edit_dest:"):
        parts = data.split(":")
        context.user_data['edit_fw_id'] = int(parts[1])
        context.user_data['edit_fw_pos'] = int(parts[2])
        context.user_data['setup_page'] = 0
        await show_edit_dest_selection(update, context)
        return EDIT_DEST
        
    if data.startswith("fw_chg_src:"):
        context.user_data['edit_fw_id'] = int(data.split(":")[1])
        context.user_data['setup_page'] = 0
        await show_edit_source_selection(update, context)
        return EDIT_SOURCE
        
    if data.startswith("fw_rule:"):
        return await handle_fw_rule(update, context, query, data.split(":"))

    try:
        action, fw_id = data.split(":")
        fw_id = int(fw_id)
    except ValueError:
        return
        
    if action == "fw_schedule":
        await query.edit_message_text(
            f"*Set Schedule for Forward {fw_id}*\n\n"
            "Send the daily time in `HH:MM` format (24h), e.g., `09:00` or `18:30`.\n"
            "Send `off` to disable scheduling.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_conv")]]),
            parse_mode='Markdown'
        )
        context.user_data['schedule_fw_id'] = fw_id
        return SET_SCHEDULE

    return await handle_fw_toggles(update, context, query, action, fw_id)

# --- Edit Handlers ---
from app.utils.keyboards import chat_selection_keyboard
import math

EDIT_DEST, EDIT_SOURCE = range(1, 3)

async def show_edit_dest_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chats = await Models().chats.get_user_chats(user_id)
    # Filter out current source?
    fw_id = context.user_data['edit_fw_id']
    details, dests = await Models().forwards.get_forward_details(fw_id)
    chats = [c for c in chats if c['id'] != details['source_id']]
    
    page = context.user_data.get('setup_page', 0)
    per_page = 5
    total_pages = math.ceil(len(chats) / per_page)
    
    start = page * per_page
    end = start + per_page
    current_chats = chats[start:end]
    
    keyboard = chat_selection_keyboard(current_chats, page, total_pages, "edit_dest")
    
    pos = context.user_data['edit_fw_pos']
    text = f"*Select Chat for Destination {pos}*"
    await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def edit_dest_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer("Select destination chat...")
    except Exception:
        pass # Ignore timeouts on answer
    data = query.data
    
    if data == "cancel_setup":
        # Go back to detail
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
    
    text = f"*Select New Source Chat*"
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
    
    # Update source
    await Models().db.execute('UPDATE forwards SET source_id = ? WHERE id = ?', (chat_id, fw_id))
    
    await query.answer("✅ Source updated", show_alert=False)
    await forward_detail(update, context, fw_id=fw_id)
    return ConversationHandler.END

# Unified Edit Handler
edit_forward_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(forward_action, pattern="^fw_edit_dest:"),
        CallbackQueryHandler(forward_action, pattern="^fw_chg_src:")
    ],
    states={
        EDIT_DEST: [CallbackQueryHandler(edit_dest_selected, pattern="^edit_dest")],
        EDIT_SOURCE: [CallbackQueryHandler(edit_source_selected, pattern="^edit_src")]
    },
    fallbacks=[CallbackQueryHandler(edit_dest_selected, pattern="^cancel_setup$")] # Reuse cancel logic
)

# Schedule Conversation

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
    entry_points=[CallbackQueryHandler(forward_action, pattern="^fw_schedule")],
    states={
        SET_SCHEDULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_schedule_time)]
    },
    fallbacks=[
        CommandHandler("cancel", cancel_schedule),
        CallbackQueryHandler(cancel_schedule, pattern="^cancel_conv$")
    ]
)

async def forward_rules_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, fw_id: int):
    query = update.callback_query
    
    details, dests = await Models().forwards.get_forward_details(fw_id)
    import json
    filters = json.loads(details['filters'])
    
    # Define rules
    # Content types
    content_types = ["text", "image", "video", "audio", "document", "sticker"]
    
    keyboard = []
    
    # Grid of content types (2 per row)
    row = []
    for ct in content_types:
        status = "✅" if ct in filters else "❌"
        row.append(InlineKeyboardButton(f"{status} {ct.title()}", callback_data=f"fw_rule:{fw_id}:{ct}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    # Sender Toggle
    sender_status = "✅ Show Sender" if "sender" in filters else "❌ Show Sender"
    keyboard.append([InlineKeyboardButton(sender_status, callback_data=f"fw_rule:{fw_id}:sender")])
    
    keyboard.append([InlineKeyboardButton("⏎ Back", callback_data=f"fw_detail:{fw_id}")])
    
    text = (
        f"*Rules for {details['name']}*\n\n"
        "Toggle content types to forward.\n"
        "*Show Sender*: Forward message (with tag).\n"
        "*Hide Sender*: Copy message (no tag)."
    )
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
