from .base import BaseRepository
import json
from datetime import datetime

class ForwardRepository(BaseRepository):
    async def create_forward(self, user_id, source_id, name, filters):
        if isinstance(filters, list): # Ensure filters is stringified if passed as list
             filters = json.dumps(filters)

        cursor = await self.db.execute('''
            INSERT INTO forwards (user_id, source_id, name, filters)
            VALUES (?, ?, ?, ?)
        ''', (user_id, source_id, name, filters))
        return cursor.lastrowid

    async def add_destination(self, forward_id, dest_id, position):
        await self.db.execute('DELETE FROM forward_destinations WHERE forward_id = ? AND position = ?', (forward_id, position))
        await self.db.execute('''
            INSERT INTO forward_destinations (forward_id, dest_id, position)
            VALUES (?, ?, ?)
        ''', (forward_id, dest_id, position))

    async def clear_destination(self, forward_id, position):
        await self.db.execute('DELETE FROM forward_destinations WHERE forward_id = ? AND position = ?', (forward_id, position))


    async def get_user_forwards(self, user_id):
        return await self.db.fetch_all('SELECT * FROM forwards WHERE user_id = ?', (user_id,))

    async def get_forward_details(self, forward_id):
        fw = await self.db.fetch_one('''
            SELECT f.*, c.title as source_title 
            FROM forwards f
            LEFT JOIN chats c ON f.source_id = c.id
            WHERE f.id = ?
        ''', (forward_id,))
        if not fw:
            return None, []
        dests = await self.db.fetch_all('''
            SELECT d.dest_id, c.title 
            FROM forward_destinations d
            JOIN chats c ON d.dest_id = c.id
            WHERE d.forward_id = ?
            ORDER BY d.position
        ''', (forward_id,))
        return dict(fw), [dict(d) for d in dests]

    async def get_forwards_by_source(self, source_id):
        rows = await self.db.fetch_all('SELECT * FROM forwards WHERE source_id = ? AND paused = 0', (source_id,))
        forwards = []
        for row in rows:
            fw = dict(row)
            dests = await self.db.fetch_all('SELECT dest_id FROM forward_destinations WHERE forward_id = ? ORDER BY position', (fw['id'],))
            fw['dest_ids'] = [d['dest_id'] for d in dests]
            forwards.append(fw)
        return forwards

    async def toggle_pause(self, forward_id):
        await self.db.execute('UPDATE forwards SET paused = 1 - paused WHERE id = ?', (forward_id,))

    async def delete_forward(self, forward_id):
        await self.db.execute('DELETE FROM forwards WHERE id = ?', (forward_id,))

    async def set_forward_flags(self, forward_id, header_enabled=None, footer_enabled=None):
        if header_enabled is not None:
            await self.db.execute('UPDATE forwards SET header_enabled = ? WHERE id = ?', (1 if header_enabled else 0, forward_id))
        if footer_enabled is not None:
            await self.db.execute('UPDATE forwards SET footer_enabled = ? WHERE id = ?', (1 if footer_enabled else 0, forward_id))

    async def set_schedule_time(self, forward_id, time_str):
        # time_str: "HH:MM" or None
        await self.db.execute('UPDATE forwards SET schedule_time = ? WHERE id = ?', (time_str, forward_id))

    # Buffer Methods
    async def add_to_buffer(self, forward_id, source_message_id, source_chat_id, msg_type, text, caption):
        await self.db.execute('''
            INSERT INTO forward_buffer (forward_id, source_message_id, source_chat_id, msg_type, text, caption)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (forward_id, source_message_id, source_chat_id, msg_type, text, caption))

    async def get_buffered_messages(self, forward_id):
        return await self.db.fetch_all('SELECT * FROM forward_buffer WHERE forward_id = ? ORDER BY created_at', (forward_id,))

    async def clear_buffer(self, forward_id):
        await self.db.execute('DELETE FROM forward_buffer WHERE forward_id = ?', (forward_id,))

    async def get_scheduled_forwards(self, time_str):
        return await self.db.fetch_all('SELECT * FROM forwards WHERE schedule_time = ? AND paused = 0', (time_str,))
