from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.database.models import Models
from app.config import Config
import uuid

async def invite_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    user_id = update.inline_query.from_user.id
    
    # Only admins can generate invites
    if user_id not in Config.ADMIN_IDS:
        return

    if query == "invite":
        # Generate unique code
        code = str(uuid.uuid4())[:8]
        
        # Save to DB
        await Models().invitations.create_invitation(code, user_id)
        
        # Create result
        bot_username = context.bot.username
        invite_link = f"https://t.me/{bot_username}?start=invite_{code}"
        
        results = [
            InlineQueryResultArticle(
                id=code,
                title="Send Invitation",
                description="Click to send an invitation card.",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        "✨ **Exclusive Invitation** ✨\n\n"
                        "You've been invited to join the **Forwarder Dude**.\n\n"
                        "🚀 **Unlock Powerful Features:**\n"
                        "• Intelligent Message Forwarding\n"
                        "• Custom Rules & Filters\n"
                        "• Detailed Analytics\n\n"
                        "👇 **Claim Your Access Now**"
                     ),
                    parse_mode='Markdown'
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Accept Invitation", url=invite_link)]
                ])
            )
        ]
        
        await update.inline_query.answer(results, cache_time=0, is_personal=True)
