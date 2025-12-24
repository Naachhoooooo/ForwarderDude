from .base import BaseRepository

class ChatRepository(BaseRepository):
    async def add_or_update_chat(self, chat_id, title, type, added_by):
        await self.db.execute('''
            INSERT INTO chats (id, title, type, added_by, status, updated_at)
            VALUES (?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                updated_at=CURRENT_TIMESTAMP
        ''', (chat_id, title, type, added_by))

    async def get_user_chats(self, user_id):
        return await self.db.fetch_all("SELECT * FROM chats WHERE added_by = ? AND status = 'active' ORDER BY title", (user_id,))

    async def update_chat_status(self, chat_id, status):
        await self.db.execute('UPDATE chats SET status = ? WHERE id = ?', (status, chat_id))
