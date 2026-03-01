from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ChatMemberHandler, MessageHandler, filters, InlineQueryHandler
from app.handlers.auth import start, auth_callback
from app.handlers.chat_tracking import track_chat_member
from app.handlers.menus import menu_callback
from app.handlers.forwarding_setup import new_forward_handler
from app.handlers.forwards_lister import list_forwards, forward_detail
from app.handlers.forwards_scheduler import schedule_handler
from app.handlers.forwards_editor import edit_forward_handler, forward_action
from app.handlers.settings import settings_handler
from app.handlers.admin import (
    admin_menu, admin_access_control, admin_maintenance, admin_invite, 
    admin_performance, admin_performance_graph, admin_send_log, admin_user_detail, admin_user_action,
    notice_handler
)
from app.handlers.broadcast import broadcast_handler
from app.handlers.inviter import invite_query_handler
from app.services.forwarder import handle_message

def register_handlers(application: Application):
    """Registers all handlers for the application."""
    
    # Conversation Handlers
    application.add_handler(new_forward_handler)
    application.add_handler(settings_handler)
    application.add_handler(schedule_handler)
    application.add_handler(edit_forward_handler)
    application.add_handler(notice_handler)
    
    # Command Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("forwards", list_forwards))
    
    # Callback Handlers - General
    application.add_handler(CallbackQueryHandler(auth_callback, pattern="^auth_"))
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="^(menu_|main_menu)"))
    
    # Callback Handlers - Forwarding
    application.add_handler(CallbackQueryHandler(list_forwards, pattern="^fw_list_page:"))
    application.add_handler(CallbackQueryHandler(forward_detail, pattern="^fw_detail:"))
    application.add_handler(CallbackQueryHandler(forward_action, pattern="^fw_(pause|delete|header|footer|rules|rule|test|clear_menu|clear_dest)"))
    
    # Admin Handlers
    application.add_handler(broadcast_handler) # Must be before admin_maintenance
    application.add_handler(CallbackQueryHandler(admin_access_control, pattern="^admin_access"))
    application.add_handler(CallbackQueryHandler(admin_access_control, pattern="^admin_access_page:"))
    application.add_handler(CallbackQueryHandler(admin_user_detail, pattern="^admin_user:"))
    application.add_handler(CallbackQueryHandler(admin_user_action, pattern="^admin_(remove|restrict):"))
    application.add_handler(CallbackQueryHandler(admin_maintenance, pattern="^admin_maint"))
    application.add_handler(CallbackQueryHandler(admin_invite, pattern="^admin_invite"))
    application.add_handler(CallbackQueryHandler(admin_performance_graph, pattern="^admin_perf_graph"))
    application.add_handler(CallbackQueryHandler(admin_performance, pattern="^admin_perf"))
    application.add_handler(CallbackQueryHandler(admin_send_log, pattern="^admin_log:"))
    
    # Inline Query Handler
    application.add_handler(InlineQueryHandler(invite_query_handler))
    
    # Chat Member Handler
    application.add_handler(ChatMemberHandler(track_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    
    # Message Handler (Last)
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
