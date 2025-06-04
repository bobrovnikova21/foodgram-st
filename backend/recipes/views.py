import io
from decimal import Decimal
from typing import Any

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from ninja import Router
from rest_framework_simplejwt.tokens import AccessToken

from recipes.models import Recipe, Component, RecipeComponent
from recipes.schemas import RecipeSchema, RecipeUpdateSchema
from users.auth import auth
from users.models import User


router = Router()


@router.post("/recipes/", auth=auth)
def create_dish(request, data: RecipeSchema) -> dict[str, Any]:
    user: User = request.auth
    recipe: Recipe = Recipe.objects.create(
        creator=user,
        name=data.name,
        image_url=data.image,
        details=data.text,
        preparation_time=int(data.cooking_time),
    )

    for item in data.ingredients:
        component: Component = get_object_or_404(Component, id=item.get("id"))
        RecipeComponent.objects.create(
            dish=recipe,
            component=component,
            quantity=Decimal(item.get("amount")),
        )

    return {"message": "Блюдо успешно добавлено!", "id": recipe.id}


@router.get("/recipes/")
def list_dishes(
    request,
    page: int = 1,
    limit: int = 6,
    is_favorited: int = 0,
    is_in_shopping_cart: int = 0,
    author: int | None = None,
):
    user = None
    auth_header = request.headers.get("Authorization")

    if auth_header:
        try:
            token = auth_header.split()[1]
            access_token = AccessToken(token)
            user = User.objects.filter(id=access_token["user_id"]).first()
        except Exception:
            return {"error": "Ошибка авторизации"}, 401

    recipes = Recipe.objects.order_by("-id")

    if author:
        recipes = recipes.filter(creator__id=author)

    if is_favorited:
        if not user:
            return {"error": "Требуется авторизация"}, 401
        recipes = recipes.filter(id__in=user.favorites.values_list("id", flat=True))

    if is_in_shopping_cart:
        if not user:
            return {"error": "Требуется авторизация"}, 401
        recipes = recipes.filter(id__in=user.shopping_list.values_list("id", flat=True))

    paginator = Paginator(recipes, limit)
    current_page = paginator.get_page(page)

    return {
        "results": [
            {
                "id": recipe.id,
                "name": recipe.name,
                "author": {
                    "username": recipe.creator.username,
                    "id": recipe.creator.id,
                    "first_name": recipe.creator.first_name,
                    "last_name": recipe.creator.last_name,
                    "avatar": recipe.creator.avatar,
                },
                "text": recipe.details,
                "cooking_time": recipe.preparation_time,
                "image": recipe.image_url,
                "ingredients": [
                    {
                        "id": ingredient.component.id,
                        "name": ingredient.component.title,
                        "amount": ingredient.quantity,
                        "measurement_unit": ingredient.component.measurement,
                    }
                    for ingredient in recipe.recipecomponent_set.all()
                ],
                "is_in_shopping_cart": (
                    user.shopping_list.filter(id=recipe.id).exists() if user else False
                ),
                "is_favorited": (
                    user.favorites.filter(id=recipe.id).exists() if user else False
                ),
            }
            for recipe in current_page
        ],
        "count": recipes.count(),
    }


@router.get("/recipes/download_shopping_cart/", auth=auth)
def download_shopping_cart(request):
    """Скачать список покупок"""
    user = request.auth

    ingredients = {}
    for recipe in user.shopping_list.all():
        for item in recipe.recipecomponent_set.all():
            key = f"{item.component.title} ({item.component.measurement})"
            ingredients[key] = ingredients.get(key, 0) + item.quantity

    shopping_list = "\n".join(
        f"{name} — {amount}" for name, amount in ingredients.items()
    )

    file = io.BytesIO()
    file.write(shopping_list.encode("utf-8"))
    file.seek(0)

    return FileResponse(file, as_attachment=True, filename="shopping-list.txt")


@router.get("/recipes/{recipe_id}/")
def get_dish(request, recipe_id: int):
    user = None
    auth_header = request.headers.get("Authorization")

    if auth_header:
        try:
            token = auth_header.split()[1]
            access_token = AccessToken(token)
            user = User.objects.filter(id=access_token["user_id"]).first()
        except Exception:
            return {"error": "Ошибка авторизации"}, 401

    recipe = get_object_or_404(Recipe, id=recipe_id)

    return {
        "name": recipe.name,
        "text": recipe.details,
        "cooking_time": recipe.preparation_time,
        "image": recipe.image_url,
        "author": {
            "username": recipe.creator.username,
            "id": recipe.creator.id,
            "first_name": recipe.creator.first_name,
            "last_name": recipe.creator.last_name,
            "avatar": recipe.creator.avatar,
            "is_subscribed": (
                user.followings.filter(id=recipe.creator.id).exists() if user else False
            ),
        },
        "ingredients": [
            {
                "id": ingredient.component.id,
                "name": ingredient.component.title,
                "amount": ingredient.quantity,
                "measurement_unit": ingredient.component.measurement,
            }
            for ingredient in recipe.recipecomponent_set.all()
        ],
        "is_in_shopping_cart": (
            user.shopping_list.filter(id=recipe.id).exists() if user else False
        ),
        "is_favorited": user.favorites.filter(id=recipe.id).exists() if user else False,
    }


@router.patch("/recipes/{recipe_id}/", auth=auth)
def update_dish(request, recipe_id: int, data: RecipeUpdateSchema):
    user = request.auth
    recipe = get_object_or_404(Recipe, id=recipe_id, creator=user)

    if data.name:
        recipe.name = data.name
    if data.text:
        recipe.details = data.text
    if data.cooking_time:
        recipe.preparation_time = data.cooking_time
    if data.image:
        recipe.image_url = data.image

    recipe.save()

    if data.ingredients:
        recipe.recipecomponent_set.all().delete()
        for item in data.ingredients:
            component = get_object_or_404(Component, id=item.get("id"))
            RecipeComponent.objects.create(
                dish=recipe, component=component, quantity=Decimal(item.get("amount"))
            )

    return {"message": "Блюдо обновлено"}


@router.delete("/recipes/{recipe_id}/", auth=auth)
def delete_dish(request, recipe_id: int):
    user = request.auth
    recipe = get_object_or_404(Recipe, id=recipe_id, creator=user)
    recipe.delete()

    return {"message": "Блюдо удалено"}


@router.post("/recipes/{recipe_id}/favorite/", auth=auth)
def add_to_favorites(request, recipe_id: int):
    user = request.auth
    recipe = get_object_or_404(Recipe, id=recipe_id)

    user.favorites.add(recipe)
    return {"message": "Блюдо добавлено в избранное"}


@router.delete("/recipes/{recipe_id}/favorite/", auth=auth)
def remove_from_favorites(request, recipe_id: int):
    user = request.auth
    recipe = get_object_or_404(Recipe, id=recipe_id)

    user.favorites.remove(recipe)
    return {"message": "Блюдо удалено из избранного"}


@router.post("/recipes/{recipe_id}/shopping_cart/", auth=auth)
def add_to_cart(request, recipe_id: int):
    user = request.auth
    recipe = get_object_or_404(Recipe, id=recipe_id)

    user.shopping_list.add(recipe)
    return {"message": "Блюдо добавлено в корзину"}


@router.delete("/recipes/{recipe_id}/shopping_cart/", auth=auth)
def remove_from_cart(request, recipe_id: int):
    user = request.auth
    recipe = get_object_or_404(Recipe, id=recipe_id)

    user.shopping_list.remove(recipe)
    return {"message": "Блюдо удалено из корзины"}


@router.get("/ingredients/")
def get_components(request, name: str | None = None):
    name = name.strip().lower() if name else None

    components = list(Component.objects.values("id", "title", "measurement"))

    filtered_components = [
        {
            "id": component["id"],
            "name": f'{component["title"]} ({component["measurement"]})',
        }
        for component in components
        if not name or name in component["title"].lower()
    ]

    return filtered_components


@router.get("/recipes/{recipe_id}/get-link/")
def get_dish_link(request, recipe_id: int):
    """Создание короткой ссылки на блюдо"""
    dish = get_object_or_404(Recipe, id=recipe_id)

    base_url = request.build_absolute_uri("/")[:-1]

    return {"short-link": f"{base_url}/recipes/{dish.id}/"}
