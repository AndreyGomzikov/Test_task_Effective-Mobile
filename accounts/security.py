from datetime import timedelta
import bcrypt
import jwt
from django.conf import settings
from django.utils import timezone

from accounts.models import Session

JWT_ALGORITHM = 'HS256'
SESSION_DAYS = 7


def hash_password(raw_password: str) -> str:
    password_bytes = raw_password.encode('utf-8')
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')


def check_password(raw_password: str, password_hash: str) -> bool:
    password_bytes = raw_password.encode('utf-8')
    hash_bytes = password_hash.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hash_bytes)


def create_token_for_user(user):
    expires_at = timezone.now() + timedelta(days=SESSION_DAYS)
    session = Session.objects.create(user=user, expires_at=expires_at)
    payload = {
        'sub': str(user.id),
        'sid': str(session.id),
        'exp': int(expires_at.timestamp()),
        'iat': int(timezone.now().timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, session


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[JWT_ALGORITHM])
