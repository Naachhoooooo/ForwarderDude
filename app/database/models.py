# Database schema initialization and repository facade
from app.database.connection import Database
from app.database.repositories.user_repository import UserRepository
from app.database.repositories.chat_repository import ChatRepository
from app.database.repositories.forward_repository import ForwardRepository
from app.database.repositories.invitation_repository import InvitationRepository
from app.database.repositories.system_repository import SystemRepository

class Models:
    """Facade for database repository access."""
    def __init__(self):
        self.db = Database()
        self.users = UserRepository()
        self.chats = ChatRepository()
        self.forwards = ForwardRepository()
        self.invitations = InvitationRepository()
        self.system = SystemRepository()

    async def init_tables(self):
        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                status TEXT DEFAULT 'pending',
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                approved_by INTEGER,
                last_request_date DATETIME,
                rejection_count INTEGER DEFAULT 0,
                joined_via TEXT DEFAULT 'request',
                invited_by INTEGER,
                forwarder_dude_id TEXT UNIQUE
            )
        ''')

        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS invitations (
                code TEXT PRIMARY KEY,
                created_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                used_by INTEGER,
                used_at DATETIME,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (created_by) REFERENCES users(id),
                FOREIGN KEY (used_by) REFERENCES users(id)
            )
        ''')

        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY,
                title TEXT,
                type TEXT,
                added_by INTEGER,
                status TEXT DEFAULT 'active',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (added_by) REFERENCES users(id)
            )
        ''')

        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS forwards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                source_id INTEGER,
                name TEXT,
                paused INTEGER DEFAULT 0,
                filters TEXT DEFAULT '[\"text\",\"image\",\"video\",\"audio\",\"document\",\"sticker\"]',
                header_enabled INTEGER DEFAULT 0,
                footer_enabled INTEGER DEFAULT 0,
                schedule_time TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (source_id) REFERENCES chats(id)
            )
        ''')

        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS forward_destinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                forward_id INTEGER,
                dest_id INTEGER,
                position INTEGER,
                FOREIGN KEY (forward_id) REFERENCES forwards(id) ON DELETE CASCADE,
                FOREIGN KEY (dest_id) REFERENCES chats(id)
            )
        ''')

        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS forward_buffer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                forward_id INTEGER,
                source_message_id INTEGER,
                source_chat_id INTEGER,
                msg_type TEXT,
                text TEXT,
                caption TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (forward_id) REFERENCES forwards(id) ON DELETE CASCADE
            )
        ''')

        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date DATE PRIMARY KEY,
                forwards INTEGER DEFAULT 0,
                failures INTEGER DEFAULT 0,
                system_load_sum REAL DEFAULT 0,
                system_load_count INTEGER DEFAULT 0
            )
        ''')

        await self.db.execute('''
            CREATE TABLE IF NOT EXISTS message_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                forward_id INTEGER,
                dest_chat_id INTEGER,
                source_chat_id INTEGER,
                source_message_id INTEGER,
                message_type TEXT,
                message_data TEXT,
                priority INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                retry_count INTEGER DEFAULT 0,
                last_retry_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                sent_at DATETIME,
                error TEXT,
                FOREIGN KEY (forward_id) REFERENCES forwards(id) ON DELETE CASCADE
            )
        ''')

        await self.db.execute('CREATE INDEX IF NOT EXISTS idx_chats_added_by ON chats(added_by)')
        await self.db.execute('CREATE INDEX IF NOT EXISTS idx_forwards_user ON forwards(user_id)')
        await self.db.execute('CREATE INDEX IF NOT EXISTS idx_forwards_source ON forwards(source_id)')
        await self.db.execute('CREATE INDEX IF NOT EXISTS idx_queue_status ON message_queue(status)')
        await self.db.execute('CREATE INDEX IF NOT EXISTS idx_queue_dest ON message_queue(dest_chat_id)')
        await self.db.execute('CREATE INDEX IF NOT EXISTS idx_queue_created ON message_queue(created_at)')
