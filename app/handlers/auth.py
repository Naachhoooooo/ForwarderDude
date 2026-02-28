from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from app.database.models import Models
from app.utils.keyboards import main_menu_keyboard, admin_approval_keyboard, welcome_keyboard
from app.config import Config
from app.logger import system_logger
from datetime import datetime, timedelta
from app.handlers.menus import get_dashboard_text

async def _handle_invitation(update: Update, context: ContextTypes.DEFAULT_TYPE, user, models, code: str):
    invitation = await models.invitations.get_invitation(code)
    if invitation and invitation['status'] == 'pending':
        await models.users.add_user(
            user.id, user.username, user.full_name, 
            status='active', 
            joined_via='invite', 
            invited_by=invitation['created_by']
        )
        await models.invitations.mark_invitation_used(code, user.id)
        
        system_logger.info(f"User {user.id} ({user.username}) joined via invitation from {invitation['created_by']}")
        
        bot_username = context.bot.username
        await update.message.reply_text(
            (
                f"🎉 **Invitation Accepted!**\n\n"
                f"Welcome to Forwarder Dude, {user.first_name}!\n"
                "Let's get started!\n\n"
                "**Usage:**\n\n"
                "1. Add me to your source and destination chats.\n"
                "2. Create a 'New Forward'.\n"
                "3. Relax!"
            ),
            reply_markup=welcome_keyboard(bot_username),
            parse_mode='Markdown'
        )
        await update.message.reply_text(
            "Use the menu below to manage your forwards:",
            reply_markup=main_menu_keyboard(is_admin=False)
        )
        
        try:
            await context.bot.send_message(
                chat_id=invitation['created_by'],
                text=f"✅ Your invitation was accepted by {user.full_name} (@{user.username})."
            )
        except: pass
    elif invitation and invitation['status'] == 'used':
         await update.message.reply_text("⚠️ This invitation link has already been used.")
    else:
         await update.message.reply_text("❌ Invalid or expired invitation link.")

async def _handle_new_user_request(update: Update, context: ContextTypes.DEFAULT_TYPE, user, models):
    await models.users.add_user(user.id, user.username, user.full_name, status='pending')
    await update.message.reply_text(
        "**Forwarder Dude** 🛡️\n\n"
        "**Access Restricted**\n"
        "Your access request has been submitted for review. You’ll be notified once a decision is made.\n\n"
        "__Disclaimer: We are not responsible for any copyrighted content forwarded using this tool.__",
        parse_mode='Markdown'
    )
    
    for admin_id in Config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"🔔 *New Access Request*\n\n"
                     f"Username: @{user.username}\n"
                     f"Name: {user.full_name}\n"
                     f"Telegram ID: `{user.id}`\n"
                     f"Last Request: New User",
                reply_markup=admin_approval_keyboard(user.id),
                parse_mode='Markdown'
            )
        except Exception as e:
            system_logger.error(f"Failed to notify admin {admin_id}: {e}")
            
    system_logger.info(f"New access request from {user.id} ({user.username})")

async def _handle_restricted_blocked_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user, models, db_user):
    if db_user['status'] == 'pending':
        return await update.message.reply_text("**Request Pending** ⏳\nYour request is currently under review..")
        
    if db_user['status'] == 'restricted':
        return await update.message.reply_text(
            "⛔ **Access Restricted**\n"
            "Your account has been restricted by an administrator. You cannot perform actions at this time.\n\n"
            "Please contact support if you believe this is an error.",
            parse_mode='Markdown'
         )
         
    if db_user['status'] in ['rejected', 'blocked']:
        last_request = datetime.strptime(db_user['last_request_date'], '%Y-%m-%d %H:%M:%S') if db_user['last_request_date'] else datetime.min
        if datetime.now() - last_request < timedelta(hours=24):
            remaining = timedelta(hours=24) - (datetime.now() - last_request)
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            time_str = f"{hours}h {minutes}m"
            status_text = "Blocked" if db_user['status'] == 'blocked' else "Rejected"
            
            return await update.message.reply_text(
                f"⛔ *Access Blocked ({status_text})*\n"
                f"Your request cannot be processed right now, try after 24 hours.\n\n"
                f"⏳ You can try accessing again in`{time_str}`.",
                parse_mode='Markdown'
            )
        
        await models.users.update_last_request(user.id)
        await models.users.update_user_status(user.id, 'pending')
        await update.message.reply_text(
            "**Forwarder Dude** 🛡️\n\n"
            "*Access Restricted*\n"
            "Your access request has been submitted for review. You’ll be notified once a decision is made.\n\n"
            "__Disclaimer: We are not responsible for any copyrighted content forwarded using this tool.__",
            parse_mode='Markdown'
        )
        
        for admin_id in Config.ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"🔔 *New Access Request*\n\n"
                         f"Username: @{user.username}\n"
                         f"Name: {user.full_name}\n"
                         f"Telegram ID: `{user.id}`\n"
                         f"Last Request: Requested on {last_request.strftime('%d %b %Y')}",
                    reply_markup=admin_approval_keyboard(user.id),
                    parse_mode='Markdown'
                )
            except Exception as e:
                system_logger.error(f"Failed to notify admin {admin_id}: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    models = Models()
    db_user = await models.users.get_user(user.id)
    is_admin = user.id in Config.ADMIN_IDS
    
    if is_admin:
        await models.users.add_user(user.id, user.username, user.full_name, status='admin')

    maintenance_mode = await models.system.get_setting("maintenance_mode", "off")
    if maintenance_mode == "on" and not is_admin:
        notice = await models.system.get_setting("maintenance_notice", "The bot is currently under maintenance. Please try again later.")
        return await update.message.reply_text(f"*🚧 Maintenance Mode - Activated*\n\n{notice}\n\n_We are very sorry for the inconvenience_", parse_mode='Markdown')

    if is_admin:
        dashboard_text = await get_dashboard_text(user, models)
        await update.message.reply_text(dashboard_text, reply_markup=main_menu_keyboard(is_admin=True), parse_mode='Markdown')
        return await update.message.reply_text("Add bot to your group or channel", reply_markup=welcome_keyboard(context.bot.username), parse_mode='Markdown')

    if context.args and context.args[0].startswith('invite_'):
        return await _handle_invitation(update, context, user, models, context.args[0].split('_')[1])

    if not db_user:
        return await _handle_new_user_request(update, context, user, models)
                
    if db_user['status'] in ['pending', 'restricted', 'rejected', 'blocked']:
        return await _handle_restricted_blocked_user(update, context, user, models, db_user)

    dashboard_text = await get_dashboard_text(user, models)
    await update.message.reply_text(dashboard_text, reply_markup=main_menu_keyboard(is_admin=False), parse_mode='Markdown')
    await update.message.reply_text("Add bot to your group or channel", reply_markup=welcome_keyboard(context.bot.username), parse_mode='Markdown')

async def auth_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    action, user_id = data.split(':')
    user_id = int(user_id)
    
    models = Models()
    if query.from_user.id not in Config.ADMIN_IDS:
        await query.edit_message_text("Unauthorized action.")
        return

    if action == 'auth_accept':
        await models.users.approve_user(user_id, query.from_user.id)
        system_logger.info(f"User {user_id} approved by admin {query.from_user.id}")
        await query.edit_message_text(f"✅ User {user_id} approved.")

        try:
            bot_username = context.bot.username
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "🎉 **Welcome to Forwarder Bot !**\n\n"
                    "This bot allows you to forward messages from one chat to another responsibly.\n\n"
                    "This tool is provided as-is. You are fully responsible for the content you share. "
                    "We strictly disclaim liability for any copyrighted or illegal materials forwarded using this bot.\n\n"
                    "**Usage:**\n\n"
                    "1. Add the bot to your source and destination groups/channels (you must be the one adding it for security).\n"
                    "2. Use 'New Forward' to set up by selecting chats.\n"
                    "3. Manage forwards via 'Forwards'.\n\n"
                    "__Note: If the bot is removed from a chat, related forwards are automatically cleaned up.__"
                ),
                reply_markup=welcome_keyboard(bot_username),
                parse_mode='Markdown'
            )
            # Send main menu follow-up
            await context.bot.send_message(
                chat_id=user_id,
                text="Use the menu below to manage your forwards:",
                reply_markup=main_menu_keyboard(is_admin=False)
            )
        except Exception as e:
            await query.message.reply_text(f"User approved, but failed to notify them: {e}")
            
    elif action == 'auth_reject':
        await models.users.reject_user(user_id)
        system_logger.info(f"User {user_id} rejected by admin {query.from_user.id}")
        await query.edit_message_text(f"❌ User {user_id} rejected.")
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="Your access request was declined."
            )
        except:
            pass
