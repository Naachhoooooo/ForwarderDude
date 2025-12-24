from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def admin_approval_keyboard(user_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"auth_accept:{user_id}"),
            InlineKeyboardButton("🚫 Reject", callback_data=f"auth_reject:{user_id}")
        ]
    ])

def admin_user_actions_keyboard(user_id, is_restricted):
    restrict_label = "🟢 Unrestrict" if is_restricted else "🔴 Restrict"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(restrict_label, callback_data=f"admin_restrict:{user_id}")
        ],
        [InlineKeyboardButton("⏎ Back", callback_data="admin_access")]
    ])

def main_menu_keyboard(is_admin=False):
    keyboard = [
        [InlineKeyboardButton("⚡ New Forward", callback_data="menu_new")],
        [InlineKeyboardButton("🗂️ My Forwards", callback_data="menu_forwards")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")],
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("🔐 Admin Panel", callback_data="menu_admin")])
    
    return InlineKeyboardMarkup(keyboard)
    
def welcome_keyboard(bot_username):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Add to Group", url=f"https://t.me/{bot_username}?startgroup=true")],
        [InlineKeyboardButton("Add to Channel", url=f"https://t.me/{bot_username}?startchannel=true&admin=post_messages")]
    ])

def _add_pagination_row(keyboard, page, total_pages, callback_prefix):
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⮜", callback_data=f"{callback_prefix}_page:{page-1}"))
        
        # Page indicator button
        nav_row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
        
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("⮞", callback_data=f"{callback_prefix}_page:{page+1}"))
        
        keyboard.append(nav_row)

def chat_selection_keyboard(chats, page, total_pages, callback_prefix):
    keyboard = []
    for chat in chats:
        keyboard.append([InlineKeyboardButton(chat['title'], callback_data=f"{callback_prefix}:{chat['id']}")])
    
    _add_pagination_row(keyboard, page, total_pages, callback_prefix)
        
    keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel_setup")])
    return InlineKeyboardMarkup(keyboard)

def paginated_keyboard(items, page, total_pages, callback_prefix, back_callback="main_menu", back_label="⏎ Back", refresh_callback=None):
    keyboard = []
    for item in items:
        keyboard.append([InlineKeyboardButton(item['text'], callback_data=item['callback_data'])])
        
    _add_pagination_row(keyboard, page, total_pages, callback_prefix)
    
    footer_row = []
    if refresh_callback:
        footer_row.append(InlineKeyboardButton("♻ Refresh", callback_data=refresh_callback))
    
    if back_callback:
        footer_row.append(InlineKeyboardButton(back_label, callback_data=back_callback))
        
    if footer_row:
        keyboard.append(footer_row)
        
    return InlineKeyboardMarkup(keyboard)