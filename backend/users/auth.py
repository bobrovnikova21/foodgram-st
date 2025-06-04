from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

from ninja.security import HttpBearer

from users.models import User


class JWTAuth(HttpBearer):
    """Кастомная аутентификация через JWT."""

    def authenticate(self, request, token):
        try:
            access_token = AccessToken(token)
            user_id = access_token["user_id"]
            user = User.objects.get(id=user_id)
            return user
        except Exception:
            return None


auth = JWTAuth()


def get_tokens_for_user(user):
    """Генерирует JWT токены для пользователя."""
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }
