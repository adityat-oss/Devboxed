import sqlite3
import os
from datetime import datetime

class AuditLogger:
    def __init__(self, db_path: str = None):
        if not db_path:
            db_path = os.path.join(os.path.dirname(__file__), "..", "audit.db")
        self.db_path = os.path.abspath(db_path)
        self._init_db()
        # Ephemeral cache for this proxy session
        self._decision_cache = {}

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    domain TEXT,
                    port INTEGER,
                    status TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS proxy_rules (
                    domain TEXT PRIMARY KEY,
                    decision TEXT
                )
            ''')
            # Load persistent cache
            cursor = conn.execute('SELECT domain, decision FROM proxy_rules')
            for row in cursor.fetchall():
                self._decision_cache[row[0]] = row[1]

    def log_request(self, domain: str, port: int, status: str):
        timestamp = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO audit_logs (timestamp, domain, port, status)
                VALUES (?, ?, ?, ?)
            ''', (timestamp, domain, port, status))
            
            # Persist decision
            conn.execute('''
                INSERT OR REPLACE INTO proxy_rules (domain, decision)
                VALUES (?, ?)
            ''', (domain, status))
            
        self._decision_cache[domain] = status

    def get_cached_decision(self, domain: str) -> str:
        """Returns 'Allowed', 'Denied', or None if unknown in this session."""
        return self._decision_cache.get(domain)
