from urllib.parse import parse_qs

from channels.auth import AuthMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()

@database_sync_to_async
def get_user_from_token(token):
    try:
        access_token = AccessToken(token)
        user = User.objects.get(id=access_token['user_id'])
        return user if user.is_active else AnonymousUser()
    except Exception:
        return AnonymousUser()

class TokenAuthMiddleware(AuthMiddleware):
    async def resolve_scope(self, scope):
        # Extrai token da query string
        query_string = scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token = params.get('token', [None])[0]
        
        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()
        
        return scope

def TokenAuthMiddlewareStack(inner):
    from channels.sessions import CookieMiddleware, SessionMiddleware
    return CookieMiddleware(SessionMiddleware(TokenAuthMiddleware(inner)))