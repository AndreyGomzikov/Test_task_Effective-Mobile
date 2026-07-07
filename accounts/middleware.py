import jwt
from django.utils import timezone

from accounts.models import Session
from accounts.security import decode_token


class JWTSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.current_user = None
        request.current_session = None

        authorization = request.headers.get('Authorization', '')
        if authorization.startswith('Bearer '):
            token = authorization.removeprefix('Bearer ').strip()
            self._set_user_from_token(request, token)

        return self.get_response(request)

    def _set_user_from_token(self, request, token):
        try:
            payload = decode_token(token)
            session = self._get_active_session(payload)
            if session and str(session.user_id) == payload.get('sub'):
                request.current_user = session.user
                request.current_session = session
        except (jwt.PyJWTError, ValueError, KeyError):
            request.current_user = None
            request.current_session = None

    @staticmethod
    def _get_active_session(payload):
        return (
            Session.objects.select_related('user')
            .filter(
                id=payload.get('sid'),
                is_active=True,
                expires_at__gt=timezone.now(),
                user__is_active=True,
            )
            .first()
        )
