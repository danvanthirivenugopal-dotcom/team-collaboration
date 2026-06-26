"""
Fingerprint service for Face AI Attendance System.
Implements secure cryptographic management of fingerprint credentials in the database.
"""

import json
import base64
import hmac
import hashlib
from datetime import datetime
import logging
from backend.config import JWT_SECRET_KEY
from backend.database.db import get_db

logger = logging.getLogger("faceai.fingerprint_service")

def _crypt(data: bytes, key: bytes) -> bytes:
    """Symmetric encryption/decryption using HMAC-SHA256 CTR keystream generation."""
    out = bytearray()
    block_num = 0
    while len(out) < len(data):
        block_key = hmac.new(key, block_num.to_bytes(4, 'big'), hashlib.sha256).digest()
        chunk = data[len(out):len(out)+32]
        for i in range(len(chunk)):
            out.append(chunk[i] ^ block_key[i])
        block_num += 1
    return bytes(out)

def encrypt_fingerprint_embedding(raw_embedding: bytes) -> bytes:
    """Encrypt fingerprint embedding using derived JWT_SECRET key."""
    key = hashlib.sha256(JWT_SECRET_KEY.encode()).digest()
    return _crypt(raw_embedding, key)

def decrypt_fingerprint_embedding(encrypted_embedding: bytes) -> bytes:
    """Decrypt fingerprint embedding using derived JWT_SECRET key."""
    key = hashlib.sha256(JWT_SECRET_KEY.encode()).digest()
    return _crypt(encrypted_embedding, key)

def capture_fingerprint_embedding(credential_id: str, public_key: str) -> bytes:
    """Structure browser-captured WebAuthn credentials into raw template bytes."""
    data = {
        "credential_id": credential_id,
        "public_key": public_key
    }
    return json.dumps(data).encode("utf-8")

def compare_fingerprint_embeddings(emb1: bytes, emb2: bytes) -> float:
    """Compare two encrypted/decrypted embeddings. Returns 1.0 on exact match, 0.0 otherwise."""
    if emb1 == emb2:
        return 1.0
    return 0.0

def find_user_by_fingerprint(credential_id: str) -> dict | None:
    """Find a user in the MySQL database by matching credential ID inside their decrypted embedding."""
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, name, email, role, approval_status, fingerprint_embedding 
                    FROM users 
                    WHERE fingerprint_embedding IS NOT NULL
                    """
                )
                rows = cursor.fetchall()
                for row in rows:
                    try:
                        decrypted_bytes = decrypt_fingerprint_embedding(row["fingerprint_embedding"])
                        data = json.loads(decrypted_bytes.decode("utf-8"))
                        if data.get("credential_id") == credential_id:
                            return {
                                "user_id": row["id"],
                                "name": row["name"],
                                "email": row["email"],
                                "role": row["role"],
                                "approval_status": row["approval_status"]
                            }
                    except Exception as ex:
                        logger.error(f"Error decrypting fingerprint for user {row['id']}: {ex}")
                        continue
    except Exception as e:
        logger.error(f"find_user_by_fingerprint error: {e}")
    return None

def update_fingerprint_embedding(user_id: int, credential_id: str, public_key: str):
    """Encrypt and store/update fingerprint credentials in both users and webauthn_credentials tables."""
    raw_bytes = capture_fingerprint_embedding(credential_id, public_key)
    encrypted_blob = encrypt_fingerprint_embedding(raw_bytes)
    
    with get_db() as conn:
        with conn.cursor() as cursor:
            # 1. Update users table
            cursor.execute(
                """
                UPDATE users
                SET fingerprint_embedding = %s,
                    fingerprint_updated_at = %s
                WHERE id = %s
                """,
                (encrypted_blob, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id)
            )
            
            # 2. Sync with webauthn_credentials table (for quick standard WebAuthn lookup)
            cursor.execute("DELETE FROM webauthn_credentials WHERE user_id = %s", (user_id,))
            cursor.execute(
                """
                INSERT INTO webauthn_credentials (user_id, credential_id, public_key, sign_count)
                VALUES (%s, %s, %s, 0)
                """,
                (user_id, credential_id, public_key)
            )
    logger.info(f"Fingerprint embedding updated for user {user_id}")
