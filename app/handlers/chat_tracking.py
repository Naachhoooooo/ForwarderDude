from telegram import Update, ChatMember
from telegram.ext import ContextTypes
from app.database.models import Models
from app.logger import get_logger

logger = get_logger(__name__)


async def track_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track when the bot is added or removed from a chat."""
    result = update.my_chat_member
    if not result:
        return

    new_member = result.new_chat_member
    old_member = result.old_chat_member
    chat = result.chat
    user = result.from_user

    # Bot added
    if old_member.status in [ChatMember.LEFT, ChatMember.BANNED] and new_member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
        # Record chat addition
        await Models().chats.add_or_update_chat(chat.id, chat.title, chat.type, user.id)

        logger.info(f"Bot added to chat {chat.title} ({chat.id}) by user {user.id}")

    # Bot removed
    elif old_member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR] and new_member.status in [ChatMember.LEFT, ChatMember.BANNED]:
        await Models().chats.update_chat_status(chat.id, 'kicked')
 
        logger.info(f"Bot removed from chat {chat.title} ({chat.id})") 
