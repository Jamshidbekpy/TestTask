from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from jwt import decode as jwt_decode
from jwt.exceptions import PyJWTError
from django.conf import settings

User = get_user_model()


@database_sync_to_async
def get_user(user_id):
    """User ni database dan olish"""
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware:
    """
    Postman uchun WebSocket JWT auth middleware
    """
    
    def __init__(self, inner):
        self.inner = inner
    
    async def __call__(self, scope, receive, send):
        # Avval anonymous user
        scope["user"] = AnonymousUser()
        
        try:
            # 1. Token ni query string dan olish
            query_string = scope.get("query_string", b"").decode()
            if not query_string:
                print("❌ No query string - connection rejected")
                return await self.inner(scope, receive, send)
            
            # 2. Query parametrlarini parse qilish
            query_params = parse_qs(query_string)
            token = query_params.get("token", [None])[0]
            
            if not token:
                print("❌ No token in query string")
                return await self.inner(scope, receive, send)
            
            # 3. Token ni validate qilish
            access_token = AccessToken(token)
            payload = jwt_decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
            
            # 4. User ID ni olish
            user_id = payload.get("user_id")
            if not user_id:
                print("❌ No user_id in token")
                return await self.inner(scope, receive, send)
            
            # 5. User ni olish
            user = await get_user(user_id)
            
            if user and user.is_authenticated:
                scope["user"] = user
                print(f"✅ WebSocket authenticated: {user.email}")
            else:
                print("❌ User not authenticated")
                
        except TokenError as e:
            print(f"❌ Token error: {str(e)}")
        except PyJWTError as e:
            print(f"❌ JWT error: {str(e)}")
        except Exception as e:
            print(f"❌ Auth error: {str(e)}")
        
        return await self.inner(scope, receive, send)