"""
WebAuthn / Fingerprint service for Face AI Attendance System.
"""

import base64
import json
import logging
import os
from backend import config
import secrets
from datetime import datetime

from backend.database.db import get_db

logger = logging.getLogger("faceai.webauthn_service")

_pending_challenges: dict[int, dict] = {}


def _b64url_decode(value: str) -> bytes:
    if not value:
        return b""
    value = value.replace("-", "+").replace("_", "/")
    padding = "=" * (-len(value) % 4)
    return base64.b64decode(value + padding)


def _get_rp_id() -> str:
    return config.WEBAUTHN_RP_ID


def _get_origin() -> str:
    return config.WEBAUTHN_ORIGIN


def generate_challenge(user_id: int) -> str:
    raw = secrets.token_bytes(32)
    challenge_b64 = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    _pending_challenges[user_id] = {
        "challenge": challenge_b64,
        "created_at": datetime.now().isoformat(),
    }

    return challenge_b64


def get_pending_challenge(user_id: int):
    entry = _pending_challenges.get(user_id)
    return entry["challenge"] if entry else None


def clear_challenge(user_id: int):
    _pending_challenges.pop(user_id, None)


def register_credential(
    user_id: int,
    credential_id: str,
    public_key: str,
    transports: list | None = None,
) -> dict:
    try:
        from backend.services import fingerprint_service

        fingerprint_service.update_fingerprint_embedding(
            user_id,
            credential_id,
            public_key,
        )

        if transports:
            with get_db() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE webauthn_credentials
                        SET transports = %s
                        WHERE user_id = %s AND credential_id = %s
                        """,
                        (json.dumps(transports), user_id, credential_id),
                    )

        clear_challenge(user_id)

        return {
            "success": True,
            "message": "Fingerprint registered successfully.",
        }

    except Exception as e:
        logger.error("WebAuthn registration error for user %s: %s", user_id, e)
        raise Exception(f"Fingerprint registration failed: {e}")


def has_credential(user_id: int) -> bool:
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id
                    FROM webauthn_credentials
                    WHERE user_id = %s
                    LIMIT 1
                    """,
                    (user_id,),
                )
                return cursor.fetchone() is not None

    except Exception as e:
        logger.error("has_credential error for user %s: %s", user_id, e)
        return False


def get_credential_ids_for_user(user_id: int) -> list:
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT credential_id, transports
                    FROM webauthn_credentials
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
                rows = cursor.fetchall()

        credentials = []

        for row in rows:
            transports_raw = row.get("transports")
            try:
                transports = json.loads(transports_raw) if transports_raw else []
            except Exception:
                transports = []

            credentials.append(
                {
                    "id": row["credential_id"],
                    "type": "public-key",
                    "transports": transports,
                }
            )

        return credentials

    except Exception as e:
        logger.error("Failed to fetch credentials for user %s: %s", user_id, e)
        return []


def find_user_by_credential_id(credential_id: str) -> dict | None:
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 
                        wc.user_id,
                        wc.sign_count,
                        wc.credential_id,
                        wc.public_key,
                        u.name,
                        u.email,
                        u.role,
                        u.approval_status,
                        u.profile_image
                    FROM webauthn_credentials wc
                    JOIN users u ON u.id = wc.user_id
                    WHERE wc.credential_id = %s
                    LIMIT 1
                    """,
                    (credential_id,),
                )
                return cursor.fetchone()

    except Exception as e:
        logger.error("find_user_by_credential_id error: %s", e)
        return None


def verify_assertion(
    credential_id: str,
    client_data_json: str,
    authenticator_data: str,
    signature: str,
    user_handle: str | None = None,
) -> dict:
    try:
        from webauthn import verify_authentication_response
        from webauthn.helpers.structs import AuthenticationCredential
    except ImportError:
        raise Exception(
            "Missing WebAuthn package. Install it using: pip install webauthn"
        )

    user = find_user_by_credential_id(credential_id)

    if not user:
        raise Exception("Fingerprint credential not found.")

    user_id = user["user_id"]
    pending_challenge = get_pending_challenge(user_id)

    if not pending_challenge:
        raise Exception("Fingerprint challenge expired or missing.")

    public_key = user.get("public_key")

    if not public_key:
        raise Exception("Stored fingerprint public key missing.")

    try:
        authentication_credential = AuthenticationCredential.parse_raw(
            json.dumps(
                {
                    "id": credential_id,
                    "rawId": credential_id,
                    "type": "public-key",
                    "response": {
                        "clientDataJSON": client_data_json,
                        "authenticatorData": authenticator_data,
                        "signature": signature,
                        "userHandle": user_handle,
                    },
                }
            )
        )

        verification = verify_authentication_response(
            credential=authentication_credential,
            expected_challenge=pending_challenge,
            expected_rp_id=_get_rp_id(),
            expected_origin=_get_origin(),
            credential_public_key=_b64url_decode(public_key),
            credential_current_sign_count=user.get("sign_count") or 0,
            require_user_verification=False,
        )

    except Exception as e:
        logger.error("WebAuthn assertion verification failed: %s", e)
        raise Exception("Fingerprint verification failed.")

    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE webauthn_credentials
                    SET sign_count = %s,
                        updated_at = NOW()
                    WHERE credential_id = %s
                    """,
                    (verification.new_sign_count, credential_id),
                )

        clear_challenge(user_id)

    except Exception as e:
        logger.error("Failed to update WebAuthn sign_count: %s", e)
        raise Exception("Fingerprint verification succeeded but update failed.")

    return {
        "success": True,
        "user_id": user_id,
        "user_name": user["name"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "approval_status": user["approval_status"],
        "profile_image": user.get("profile_image"),
    }


def delete_credential(user_id: int) -> bool:
    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET fingerprint_embedding = NULL,
                        fingerprint_updated_at = NULL
                    WHERE id = %s
                    """,
                    (user_id,),
                )

                cursor.execute(
                    """
                    DELETE FROM webauthn_credentials
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )

                return True

    except Exception as e:
        logger.error("Failed to delete credential for user %s: %s", user_id, e)
        return False