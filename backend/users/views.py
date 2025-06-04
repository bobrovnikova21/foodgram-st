from django.contrib.auth import login, logout
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from users.models import User
from users.auth import get_tokens_for_user, auth
from rest_framework_simplejwt.tokens import AccessToken

router = Router()


class RegisterSchema(Schema):
    username: str
    email: str
    password: str
    first_name: str
    last_name: str


@router.post("/users/")
def register(request, data: RegisterSchema):
    """Создание нового аккаунта пользователя."""
    if User.objects.filter(username=data.username).exists():
        return {"error": "Это имя уже занято"}

    if User.objects.filter(email=data.email).exists():
        return {"error": "Этот email уже используется"}

    new_user = User.objects.create_user(
        username=data.username,
        email=data.email,
        password=data.password,
        first_name=data.first_name,
        last_name=data.last_name,
    )

    auth_tokens = get_tokens_for_user(new_user)
    return {
        "message": "Аккаунт успешно создан",
        "user_id": new_user.id,
        "tokens": auth_tokens,
    }


class LoginSchema(Schema):
    email: str
    password: str


@router.post("/auth/token/login/")
def login_view(request, body: LoginSchema):
    """Аутентификация пользователя по электронной почте."""
    account = User.objects.filter(email=body.email).first()
    if account is None or not account.check_password(body.password):
        return {"error": "Некорректные данные для входа"}

    login(request, account)
    auth_data = get_tokens_for_user(account)

    return {"message": "Успешная авторизация", "auth_token": auth_data.get("access")}


@router.post("/auth/token/logout/")
def logout_view(request):
    """Выход пользователя."""
    logout(request)
    return {"message": "Выход выполнен"}


@router.get("/users/me/", auth=auth)
def get_user_data(request):
    """Возвращает информацию о текущем пользователе."""
    user = request.auth
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "avatar": user.avatar,
    }


class ChangePasswordSchema(Schema):
    current_password: str
    new_password: str


@router.post("/users/set_password/", auth=auth)
def change_password(request, body: ChangePasswordSchema):
    """Обновление пароля пользователя."""
    account = request.auth

    if not account.check_password(body.current_password):
        return {"error": "Введен неверный пароль"}

    if len(body.new_password) < 8:
        return {"error": "Минимальная длина пароля — 8 символов"}

    account.set_password(body.new_password)
    account.save()

    return {"message": "Пароль успешно обновлен"}


class ChangeAvatarSchema(Schema):
    avatar: str


@router.put("/users/me/avatar/", auth=auth)
def change_avatar(request, body: ChangeAvatarSchema):
    """Обновление изображения профиля из Base64."""
    account = request.auth

    if not body.avatar:
        return {"error": "Файл не был загружен"}

    account.avatar = body.avatar
    account.save()

    return {"message": "Изображение профиля обновлено", "avatar_url": account.avatar}


@router.delete("/users/me/avatar/", auth=auth)
def delete_avatar(request):
    """Обновляет аватар пользователя из Base64."""
    user = request.auth
    user.avatar = ""
    user.save()

    return {"message": "Аватар успешно удален"}


@router.get("/users/subscriptions/", auth=auth)
def list_subscriptions(
    request,
    page: int = 1,
    limit: int = 6,
    recipes_limit: int = 3,
):
    account = request.auth

    subscribed_authors = account.followings.all()

    paginator = Paginator(subscribed_authors, limit)
    current_page = paginator.get_page(page)

    return {
        "results": [
            {
                "id": author.id,
                "username": author.username,
                "first_name": author.first_name,
                "last_name": author.last_name,
                "avatar": author.avatar,
                "email": author.email,
                "recipes_count": author.recipe_set.count(),
                "recipes": [
                    {
                        "id": recipe.id,
                        "name": recipe.name,
                        "image": recipe.image_url,
                        "cooking_time": recipe.preparation_time,
                    }
                    for recipe in author.recipe_set.all().order_by("-id")[
                        :recipes_limit
                    ]
                ],
            }
            for author in current_page
        ],
        "count": subscribed_authors.count(),
    }


@router.get("/users/{user_id}/")
def get_user(request, user_id: int):
    """Получение информации о пользователе по его идентификатору."""
    current_user = None
    auth_header = request.headers.get("Authorization")

    if auth_header:
        try:
            token = auth_header.split()[1]
            access_token = AccessToken(token)
            current_user = User.objects.filter(id=access_token["user_id"]).first()
        except Exception:
            return {"error": "Ошибка авторизации"}, 401

    profile = get_object_or_404(User, id=user_id)

    return {
        "id": profile.id,
        "username": profile.username,
        "email": profile.email,
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "avatar": profile.avatar,
        "is_subscribed": (
            current_user.followings.filter(id=profile.id).exists()
            if current_user
            else False
        ),
    }


@router.post("/users/{user_id}/subscribe/", auth=auth)
def subscribe_user(request, user_id: int):
    """Оформление подписки на другого пользователя."""
    account = request.auth
    creator = get_object_or_404(User, id=user_id)

    if account == creator:
        return {"error": "Нельзя оформить подписку на себя"}, 400

    account.followings.add(creator)

    return {"message": f"Теперь вы подписаны на {creator.username}"}


@router.delete("/users/{user_id}/subscribe/", auth=auth)
def unsubscribe_user(request, user_id: int):
    """Удаление подписки на пользователя."""
    account = request.auth
    creator = get_object_or_404(User, id=user_id)

    if not account.followings.filter(id=creator.id).exists():
        return {"error": "Вы не подписаны на этого пользователя"}, 400

    account.followings.remove(creator)

    return {"message": f"Вы больше не подписаны на {creator.username}"}
