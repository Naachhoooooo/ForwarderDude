from .base import BaseRepository

class InvitationRepository(BaseRepository):
    async def create_invitation(self, code, created_by):
        await self.db.execute('''
            INSERT INTO invitations (code, created_by)
            VALUES (?, ?)
        ''', (code, created_by))

    async def get_invitation(self, code):
        return await self.db.fetch_one('SELECT * FROM invitations WHERE code = ?', (code,))

    async def mark_invitation_used(self, code, used_by):
        await self.db.execute('''
            UPDATE invitations 
            SET status = 'used', 
                used_by = ?, 
                used_at = CURRENT_TIMESTAMP 
            WHERE code = ?
        ''', (used_by, code))
