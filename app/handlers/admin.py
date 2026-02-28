from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from app.database.models import Models
from app.config import Config
from app.utils.keyboards import main_menu_keyboard
from app.logger import system_logger
import os

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in Config.ADMIN_IDS:
        await query.answer("⚠️ Access Denied", show_alert=True)
        return

    text = "**Forwarder Dude - Admin Dashboard**"
    keyboard = [
        [InlineKeyboardButton("Access Control", callback_data="admin_access")],
        [InlineKeyboardButton("Maintenance Mode", callback_data="admin_maint")],
        [InlineKeyboardButton("Send Invitation", callback_data="admin_invite")],
        [InlineKeyboardButton("Performance", callback_data="admin_perf")],
        [InlineKeyboardButton("⏎ Back", callback_data="main_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def admin_access_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    users = await Models().users.get_all_users()

    visible_users = [u for u in users if u['status'] in ['active', 'restricted', 'blocked']]
    text = f"**Access Control Menu**\n\nExisting Users: {len(visible_users)}"
    visible_users.sort(key=lambda u: u['id'], reverse=True)
    
    import math
    from app.utils.keyboards import paginated_keyboard
    
    page = 0
    if query.data.startswith("admin_access_page:"):
        page = int(query.data.split(":")[1])
        
    per_page = 6
    total_pages = math.ceil(len(visible_users) / per_page)
    
    start = page * per_page
    end = start + per_page
    current_users = visible_users[start:end]
    
    text = f"**Access Control Menu**\n\nExisting Users: {len(visible_users)}"
    
    items = []
    for user in current_users:
        if user['status'] == 'restricted':
            status_icon = "🔴"
        elif user['status'] == 'blocked':
            status_icon = "🚫"
        else:
            status_icon = "🟢"

        items.append({
            'text': f"{status_icon} {user['full_name']}",
            'callback_data': f"admin_user:{user['id']}"
        })
        
    try:
        await query.edit_message_text(
            text, 
            reply_markup=paginated_keyboard(
                items, page, total_pages, "admin_access", 
                back_callback="menu_admin",
                refresh_callback=f"admin_access_page:{page}"
            ), 
            parse_mode='Markdown'
        )
    except Exception as e:
        if "Message is not modified" in str(e):
            await query.answer()
        else:
            raise

async def admin_user_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, target_user_id: int = None):
    query = update.callback_query
    
    if target_user_id:
        user_id = target_user_id
    else:
        user_id = int(query.data.split(":")[1])
    user = await Models().users.get_user(user_id)
    
    if not user:
        await query.answer("⚠️ User Not Found", show_alert=True)
        return


    approved_by_name = "Unknown"
    approver = None
    if user['approved_by']:
        approver = await Models().users.get_user(user['approved_by'])
    if approver:
        approved_by_name = approver['full_name']

    fd_id = user['forwarder_dude_id'] if 'forwarder_dude_id' in user.keys() else 'N/A'
            
    text = (
        f"Name: `{user['full_name']}`\n"
        f"Username: `@{user['username']}`\n"
        f"Telegram ID: `{user['id']}`\n"
        f"Forwarder Dude ID: `{fd_id}`\n"
        f"Date Joined: {user['joined_at']}\n"
        f"Approved By: {approved_by_name}\n"
        f"Status: {user['status'].upper()}"
    )
    
    from app.utils.keyboards import admin_user_actions_keyboard
    is_restricted = user['status'] == 'restricted'
    await query.edit_message_text(text, reply_markup=admin_user_actions_keyboard(user['id'], is_restricted), parse_mode='Markdown')

async def admin_user_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action, user_id = query.data.split(":")
    user_id = int(user_id)
    
    if action == "admin_restrict":
        user = await Models().users.get_user(user_id)
        new_status = 'active' if user['status'] == 'restricted' else 'restricted'
        await query.answer(f"✅ Status Updated: {new_status.title()}", show_alert=False)
        await Models().users.update_user_status(user_id, new_status)
        system_logger.info(f"User {user_id} status changed to {new_status} by admin {query.from_user.id}")
        await admin_user_detail(update, context, target_user_id=user_id)

async def admin_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    current = await Models().system.get_setting("maintenance_mode", "off")
    new_state = "on" if current == "off" else "off"
    
    if query.data == "admin_maint_toggle":
        await Models().system.set_setting("maintenance_mode", new_state)
        system_logger.info(f"Maintenance mode set to {new_state} by admin {query.from_user.id}")
        await query.answer(f"✅ Maintenance Mode {new_state.upper()}", show_alert=False)
        current = new_state
    
    status_icon = "🟢" if current == "off" else "🔴"
    status_text = "ONLINE" if current == "off" else "MAINTENANCE"
    text = f"**Maintenance Mode**\n\nStatus: {status_icon} {status_text}"
    
    toggle_label = "ON" if current == "off" else "OFF"
    
    keyboard = [
        [InlineKeyboardButton(f"Turn {toggle_label}", callback_data="admin_maint_toggle")],
        [InlineKeyboardButton("Set Notice", callback_data="admin_maint_notice")],
        [InlineKeyboardButton("Notify All Users", callback_data="admin_maint_notify")],
        [InlineKeyboardButton("⏎ Back", callback_data="menu_admin")]
    ]
    
    if query.data == "admin_maint":
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception as e:
            if "Message is not modified" in str(e):
                await query.answer()
            else:
                raise

SET_NOTICE = range(1)

async def admin_notice_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    current_notice = await Models().system.get_setting("maintenance_notice", "The bot is currently under maintenance. Please try again later.")
    
    await query.edit_message_text(
        f"**Set Maintenance Notice**\n\n"
        f"Current Notice:\n`{current_notice}`\n\n"
        "Send the new message text below, or /cancel.",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_notice")]])
    )
    return SET_NOTICE

async def admin_notice_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    await Models().system.set_setting("maintenance_notice", text)
    system_logger.info(f"Maintenance notice updated by admin {update.effective_user.id}")
    
    await update.message.reply_text("✅ Notice updated", reply_markup=main_menu_keyboard(True))
    return ConversationHandler.END

async def admin_notice_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer("❌ Cancelled")
        await update.callback_query.edit_message_text("Cancelled.", reply_markup=main_menu_keyboard(True))
    else:
        await update.message.reply_text("Cancelled.", reply_markup=main_menu_keyboard(True))
    return ConversationHandler.END

from telegram.ext import ConversationHandler, MessageHandler, filters, CommandHandler

notice_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(admin_notice_start, pattern="^admin_maint_notice")],
    states={
        SET_NOTICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_notice_save)]
    },
    fallbacks=[
        CommandHandler("cancel", admin_notice_cancel),
        CallbackQueryHandler(admin_notice_cancel, pattern="^cancel_notice")
    ]
)


async def admin_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Use inline query to select chat for invitation
    
    text = (
        "**Send Invitation**\n\n"
        "Click the button below to select a chat. "
        "An invitation card will be generated which you can send to the user.\n\n"
        "The user will be able to join immediately without approval."
    )
    
    keyboard = [
        [InlineKeyboardButton("✉️ Send Invitation", switch_inline_query="invite")],
        [InlineKeyboardButton("⏎ Back", callback_data="menu_admin")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def _get_performance_text() -> str:
    models = Models()
    daily = await models.system.get_daily_stats()
    lifetime = await models.system.get_lifetime_stats()
    total_users = await models.users.get_total_users()
    
    import os
    from app.config import Config
    try:
        db_size = os.path.getsize(Config.DB_PATH)
    except:
        db_size = 0

    from app.main import START_TIME
    from datetime import datetime
    uptime = datetime.now() - START_TIME
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    uptime_str = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"
    
    from app.utils.system_stats import get_system_resources, get_bot_resources, get_cpu_temperature
    sys_stats = get_system_resources()
    bot_stats = get_bot_resources()
    cpu_temp = get_cpu_temperature()
    
    def format_bytes(size):
        power = 2**10
        n = 0
        power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
        while size > power:
            size /= power
            n += 1
        return f"{size:.1f} {power_labels[n]}B"
        
    db_size_str = format_bytes(db_size)
    
    from app.services.message_queue import get_message_queue
    queue = get_message_queue()
    queue_stats = await queue.get_statistics()

    return (
        "🚀 **Forwarder Dude - Dashboard**\n\n"
        f"📊 **Daily Stats:**\n"
        f"• Success: `{daily['forwards']}`\n"
        f"• Failed: `{daily['failures']}`\n\n"
        f"📈 **Lifetime Stats:**\n"
        f"• Success: `{lifetime['forwards']}`\n"
        f"• Failed: `{lifetime['failures']}`\n\n"
        f"👥 **Users:** `{total_users}`\n\n"
        f"📬 **Message Queue:**\n"
        f"• Pending: `{queue_stats['pending']}`\n"
        f"• Processing: `{queue_stats['processing']}`\n"
        f"• Failed: `{queue_stats['failed']}`\n\n"
        "🖥  **Server Info**\n\n"
        f"⏱️ **Uptime:** `{uptime_str}`\n\n"
        f"🌡️ **Temperature:** `{cpu_temp}`\n\n"
        f"⚙️ **CPU:** `{bot_stats['cpu']}%`\n"
        f"🧠 **RAM:** `{bot_stats['ram_used']}MB`\n\n"
        f"💾 **Database:** `{db_size_str}`\n\n"
        f"⚙️ **Total CPU:** `{sys_stats['cpu']}%`\n"
        f"🧠 **Total RAM:** `{sys_stats['ram_used']}MB` / `{sys_stats['ram_total']}MB` ({sys_stats['ram_percent']}%)\n"
    )

async def admin_performance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = await _get_performance_text()
    
    keyboard = [
        [InlineKeyboardButton("✨ Generate Graph", callback_data="admin_perf_graph")],
        [
            InlineKeyboardButton("📄 System Log", callback_data="admin_log:bot"),
            InlineKeyboardButton("📄 Forward Log", callback_data="admin_log:forward")
        ],
        [InlineKeyboardButton("♻ Refresh", callback_data="admin_perf")],
        [InlineKeyboardButton("⏎ Back", callback_data="menu_admin")]
    ]
    
    if query.message.caption: # If it was a photo (graph)
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        await query.message.delete() # Delete the graph photo to clean up
    elif query.data == "admin_perf":
        try:
           await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception as e:
           if "Message is not modified" in str(e):
               await query.answer("✅ Statistics Refreshed")
           else:
               raise
    else:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def admin_performance_graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ Generating Graph...")
    
    models = Models()
    # Get last 7 days history
    # Get last 7 days history
    history = await models.system.get_history_stats(7)
    
    # Get current system stats for the chart header
    from app.utils.system_stats import get_system_resources, get_cpu_temperature, get_bot_resources
    sys_stats = get_system_resources()
    bot_stats = get_bot_resources()
    temp = get_cpu_temperature()
    
    system_info = {
        'cpu': sys_stats['cpu'],
        'ram_used': bot_stats['ram_used'], # Show bot RAM usage
        'temp': temp
    }
    
    from app.utils.charts import generate_performance_chart
    chart_io = generate_performance_chart(history, system_info)
    
    keyboard = [[InlineKeyboardButton("⏎ Back", callback_data="admin_perf")]]
    
    await query.message.reply_photo(
        photo=chart_io,
        caption="**Performance History (Last 7 Days)**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    ) 

async def admin_send_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    log_type = query.data.split(":")[1]
    
    filename = "bot.log" if log_type == "bot" else "forwards.log"
    path = os.path.join("logs", filename)
    
    try:
        if os.path.exists(path) and os.path.getsize(path) == 0:
             await query.answer("⚠️ Log file is empty", show_alert=True)
             return

        await query.message.reply_document(document=open(path, 'rb'), filename=filename)
        await query.answer("✅ Log Sent", show_alert=False)
    except FileNotFoundError:
        await query.answer("⚠️ Log file not found", show_alert=True)
    except Exception as e:
        await query.answer(f"❌ Error: {e}", show_alert=True)
