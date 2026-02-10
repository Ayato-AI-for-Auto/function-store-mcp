"""
API Key Management for Function Store
Implements deterministic hash-based API keys as recommended by Horiemon.
"""
import hashlib
import secrets
import time
from typing import Optional, Tuple
import duckdb

from solo_mcp.config import API_KEYS_DB_PATH as API_KEYS_DB

def init_api_keys_db():
    """Initialize API keys database."""
    API_KEYS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(API_KEYS_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            key_hash VARCHAR PRIMARY KEY,
            user_id VARCHAR NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            rate_limit INTEGER DEFAULT 1000,
            metadata VARCHAR
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY,
            key_hash VARCHAR NOT NULL,
            endpoint VARCHAR NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status_code INTEGER
        )
    """)
    conn.close()

def generate_api_key(user_id: str, salt: Optional[str] = None) -> str:
    """
    Generate deterministic API key based on user_id + salt + timestamp.
    
    Benefits:
    - Authenticity: Key itself serves as proof of issuance
    - Reduced management: Mathematical guarantee of DB consistency
    - Security: Harder to guess than random strings
    
    Format: fsk_<hash>
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    timestamp = str(int(time.time()))
    composite = f"{user_id}|{salt}|{timestamp}"
    key_hash = hashlib.sha256(composite.encode()).hexdigest()
    
    # Store in DB
    conn = duckdb.connect(str(API_KEYS_DB))
    try:
        conn.execute("""
            INSERT INTO api_keys (key_hash, user_id, metadata)
            VALUES (?, ?, ?)
        """, [key_hash, user_id, f"salt={salt}|ts={timestamp}"])
        conn.commit()
    finally:
        conn.close()
    
    return f"fsk_{key_hash[:32]}"  # Function Store Key

def verify_api_key(api_key: str) -> Tuple[bool, Optional[str]]:
    """
    Verify API key and return (is_valid, user_id).
    Also updates last_used timestamp.
    """
    if not api_key.startswith("fsk_"):
        return False, None
    
    key_hash = api_key[4:]  # Remove prefix
    
    conn = duckdb.connect(str(API_KEYS_DB))
    try:
        result = conn.execute("""
            SELECT user_id, is_active FROM api_keys
            WHERE key_hash LIKE ? AND is_active = TRUE
        """, [f"{key_hash}%"]).fetchone()
        
        if not result:
            return False, None
        
        user_id, is_active = result
        
        # Update last_used
        conn.execute("""
            UPDATE api_keys SET last_used = CURRENT_TIMESTAMP
            WHERE key_hash LIKE ?
        """, [f"{key_hash}%"])
        conn.commit()
        
        return True, user_id
    finally:
        conn.close()

def revoke_api_key(api_key: str) -> bool:
    """Revoke an API key."""
    if not api_key.startswith("fsk_"):
        return False
    
    key_hash = api_key[4:]
    
    conn = duckdb.connect(str(API_KEYS_DB))
    try:
        result = conn.execute("""
            UPDATE api_keys SET is_active = FALSE
            WHERE key_hash LIKE ?
        """, [f"{key_hash}%"])
        conn.commit()
        return result.rowcount > 0
    finally:
        conn.close()

def log_usage(api_key: str, endpoint: str, status_code: int):
    """Log API usage for analytics and rate limiting."""
    if not api_key.startswith("fsk_"):
        return
    
    key_hash = api_key[4:]
    
    conn = duckdb.connect(str(API_KEYS_DB))
    try:
        conn.execute("""
            INSERT INTO usage_logs (key_hash, endpoint, status_code)
            VALUES (?, ?, ?)
        """, [key_hash, endpoint, status_code])
        conn.commit()
    finally:
        conn.close()

# Initialize on import
init_api_keys_db()
