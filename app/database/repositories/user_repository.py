from .base import BaseRepository
from datetime import datetime, timedelta

class UserRepository(BaseRepository):
    async def add_user(self, user_id, username, full_name, status='pending', **kwargs):
        import uuid
        from datetime import datetime
        fd_id = f"FD-{uuid.uuid4().hex[:6].upper()}"
        joined_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status == 'active' else None
        
        await self.db.execute('''
            INSERT INTO users (id, username, full_name, status, last_request_date, joined_at, joined_via, invited_by, forwarder_dude_id) 
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET 
                username=excluded.username, 
                full_name=excluded.full_name,
                last_request_date=CURRENT_TIMESTAMP
        ''', (user_id, username, full_name, status, joined_at, kwargs.get('joined_via', 'request'), kwargs.get('invited_by'), fd_id))

    async def update_last_request(self, user_id):
        await self.db.execute('UPDATE users SET last_request_date = CURRENT_TIMESTAMP WHERE id = ?', (user_id,))

    async def approve_user(self, user_id, admin_id):
        await self.db.execute('''
            UPDATE users 
            SET status = 'active', 
                approved_by = ?, 
                joined_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (admin_id, user_id))

    async def reject_user(self, user_id):
        await self.db.execute('''
            UPDATE users 
            SET status = 'rejected', 
                rejection_count = rejection_count + 1 
            WHERE id = ?
        ''', (user_id,))

    async def get_user(self, user_id):
        return await self.db.fetch_one('SELECT * FROM users WHERE id = ?', (user_id,))

    async def update_user_status(self, user_id, status):
        await self.db.execute('UPDATE users SET status = ? WHERE id = ?', (status, user_id))

    async def get_pending_users(self):
        return await self.db.fetch_all("SELECT * FROM users WHERE status = 'pending'")

    async def get_all_users(self):
        return await self.db.fetch_all("SELECT * FROM users ORDER BY joined_at DESC")
    
    async def get_total_users(self):
        row = await self.db.fetch_one('SELECT COUNT(*) as count FROM users')
        return row['count']
