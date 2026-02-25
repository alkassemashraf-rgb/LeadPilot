import bcrypt
from datetime import datetime, timedelta
from typing import Any, Union, Optional
import json
from cryptography.fernet import Fernet
from jose import jwt
from app.core.config import settings

def create_access_token(
    subject: Union[str, Any], workspace_id: Optional[str] = None, expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    if workspace_id:
        to_encode["workspace_id"] = str(workspace_id)
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')
    # bcrypt 4.0+ limitation
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    password_bytes = password.encode('utf-8')
    # bcrypt 4.0+ limitation
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

# --- Integration Encryption ---

def encrypt_data(data: dict) -> str:
    """Encrypt a dictionary using Fernet."""
    f = Fernet(settings.ENCRYPTION_KEY_FERNET.encode())
    json_data = json.dumps(data)
    return f.encrypt(json_data.encode()).decode()

def decrypt_data(token: str) -> dict:
    """Decrypt a Fernet token back to a dictionary."""
    f = Fernet(settings.ENCRYPTION_KEY_FERNET.encode())
    decrypted_data = f.decrypt(token.encode())
    return json.loads(decrypted_data.decode())
