from .base import BaseRepository
from datetime import datetime
from app.utils.cache import system_settings_cache

class SystemRepository(BaseRepository):
    # --- Settings ---
    async def set_setting(self, key, value):
        await self.db.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        await system_settings_cache.set(key, value)

    async def get_setting(self, key, default=None):
        if await system_settings_cache.contains(key):
            return await system_settings_cache.get(key)
            
        row = await self.db.fetch_one('SELECT value FROM settings WHERE key = ?', (key,))
        value = row['value'] if row else default
        
        await system_settings_cache.set(key, value)
        return value

    # --- Stats ---
    async def increment_stat(self, stat_type):
        # stat_type: 'forwards' or 'failures'
        today = datetime.now().strftime('%Y-%m-%d')
        await self.db.execute(f'''
            INSERT INTO daily_stats (date, {stat_type}) 
            VALUES (?, 1)
            ON CONFLICT(date) DO UPDATE SET 
                {stat_type} = {stat_type} + 1
        ''', (today,))
    
    async def update_system_stats(self, load_percent):
        today = datetime.now().strftime('%Y-%m-%d')
        await self.db.execute('''
            INSERT INTO daily_stats (date, system_load_sum, system_load_count) 
            VALUES (?, ?, 1)
            ON CONFLICT(date) DO UPDATE SET 
                system_load_sum = system_load_sum + ?,
                system_load_count = system_load_count + 1
        ''', (today, load_percent, load_percent))

    async def get_daily_stats(self):
        today = datetime.now().strftime('%Y-%m-%d')
        row = await self.db.fetch_one('SELECT * FROM daily_stats WHERE date = ?', (today,))
        return row if row else {'forwards': 0, 'failures': 0, 'system_load_sum': 0, 'system_load_count': 0}

    async def get_lifetime_stats(self):
        row = await self.db.fetch_one('SELECT SUM(forwards) as forwards, SUM(failures) as failures FROM daily_stats')
        return row if row and row['forwards'] is not None else {'forwards': 0, 'failures': 0}

    async def get_history_stats(self, days=7):
        # Get stats for the last N days
        query = '''
            SELECT date, forwards, failures, system_load_sum, system_load_count
            FROM daily_stats 
            ORDER BY date DESC 
            LIMIT ?
        '''
        rows = await self.db.fetch_all(query, (days,))
        # Sort back to chronological order
        return sorted(rows, key=lambda x: x['date'])
