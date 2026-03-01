import math
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from app.database.models import Models
from app.utils.keyboards import main_menu_keyboard, paginated_keyboard
from app.utils.templates import (
    get_empty_forwards_text,
    get_forwards_list_header,
    get_forward_detail_text
)

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
        text = get_empty_forwards_text()
        if query:
            try:
                await query.edit_message_text(text, reply_markup=main_menu_keyboard(False), parse_mode='Markdown')
            except BadRequest: pass
        else:
            await update.message.reply_text(text, reply_markup=main_menu_keyboard(False), parse_mode='Markdown')
        return
        
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
        
    header_text = get_forwards_list_header()
    
    if query:
        try:
            await query.edit_message_text(
                header_text,
                reply_markup=paginated_keyboard(items, page, total_pages, "fw_list"),
                parse_mode='Markdown'
            )
        except BadRequest: pass
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
            return
            
    details, dests = await Models().forwards.get_forward_details(fw_id)
    if not details:
        await query.answer("⚠️ Forward Not Found", show_alert=True)
        return

    text = get_forward_detail_text(details, dests)
    
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
    
    # Destinations
    dest1_name = dests[0]['title'] if len(dests) > 0 else "Not Set"
    keyboard.append([InlineKeyboardButton(f"D1: {dest1_name}", callback_data=f"fw_edit_dest:{fw_id}:1")])
    
    dest2_name = dests[1]['title'] if len(dests) > 1 else "Not Set"
    keyboard.append([InlineKeyboardButton(f"D2: {dest2_name}", callback_data=f"fw_edit_dest:{fw_id}:2")])
    
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
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    except BadRequest: pass
