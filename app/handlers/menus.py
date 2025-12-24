from telegram import Update
from telegram.ext import ContextTypes
from app.config import Config
from app.utils.keyboards import main_menu_keyboard
from app.handlers.forwarding_management import list_forwards
from app.handlers.settings import settings_menu
from app.handlers.admin import admin_menu

async def get_dashboard_text(user, models=None):
    if not models:
        from app.database.models import Models
        models = Models()
        
    forwards = await models.forwards.get_user_forwards(user.id)
    active_rules = len([f for f in forwards if not f['paused']])
    daily_stats = await models.system.get_daily_stats()
    
    success_count = daily_stats['forwards']
    fail_count = daily_stats['failures']
    total_ops = success_count + fail_count
    success_rate = (success_count / total_ops * 100) if total_ops > 0 else 100.0
    
    bar_len = 10
    filled_len = int(success_rate / 100 * bar_len)
    progress_bar = "🟩" * filled_len + "⬜" * (bar_len - filled_len)
    
    return (
        f"🚀 *Forwarder Dude* \n\n"
        f"Hello, {user.first_name}! Ready to forward?\n\n"
        f"📈 *Today's Statistics*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ *Processed:* `{success_count}` messages\n"
        f"🎯 *Success Rate:* `{success_rate:.1f}%`\n"
        f"{progress_bar}\n\n"
        f"👇 *Control Panel*"
    )

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    data = query.data
    user_id = query.from_user.id
    is_admin = user_id in Config.ADMIN_IDS

    from app.database.models import Models
    models = Models()
    maintenance_mode = await models.system.get_setting("maintenance_mode", "off")
    
    if maintenance_mode == "on" and not is_admin:
        notice = await models.system.get_setting("maintenance_notice", "The bot is currently under maintenance. Please try again later.")
        await query.answer(f"🚧 Maintenance Mode - Activated\n\n{notice}\n\nWe are very sorry for the inconvenience", show_alert=True)
        return

    user = await models.users.get_user(user_id)
    if user and user['status'] == 'restricted' and not is_admin:
         await query.answer("⛔ Access Restricted", show_alert=True)
         return

    if data == "menu_forwards":
        await query.answer()
        await list_forwards(update, context)
        
    elif data == "menu_settings":
        await query.answer()
        await settings_menu(update, context)
        
    elif data == "menu_admin":
        if not is_admin:
            await query.answer("⚠️ Access Denied", show_alert=True)
            return
        await query.answer()
        await admin_menu(update, context)
        
    elif data == "main_menu":
        await query.answer()
        dashboard_text = await get_dashboard_text(update.effective_user, models)
        
        try:
            await query.edit_message_text(
                dashboard_text,
                reply_markup=main_menu_keyboard(is_admin),
                parse_mode='Markdown'
            )
        except Exception:
            pass
