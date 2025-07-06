import re
from datetime import datetime
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import FileResponse
from django_filters.rest_framework import DjangoFilterBackend

from djoser.views import UserViewSet as BaseUserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import (
    AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from recipes.models import Ingredient, Recipe, Favorite, ShoppingCart
from users.models import Follow
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (
    UserAvatarSerializer,
    IngredientDataSerializer,
    RecipeDetailSerializer,
    RecipeSummarySerializer,
    RecipeCreateUpdateSerializer,
    UserWithRecipesSerializer,
)
from api.filters import IngredientFilter

CustomUser = get_user_model()


class IngredientListViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientDataSerializer
    permission_classes = (AllowAny,)
    pagination_class = None

    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeManagementViewSet(viewsets.ModelViewSet):
    """ViewSet для управления рецептами с полным функционалом."""

    queryset = (Recipe.objects
                .select_related('author')
                .prefetch_related('recipe_ingredients__ingredient'))
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от типа запроса."""
        if self.request.method in {'POST', 'PUT', 'PATCH'}:
            return RecipeCreateUpdateSerializer
        return RecipeDetailSerializer

    def perform_create(self, serializer):
        """Установка автора при создании рецепта."""
        serializer.save(author=self.request.user)

    def create_short_recipe_response(self, recipe_obj, status_code):
        """Создание краткого ответа с информацией о рецепте."""
        serialized_data = RecipeSummarySerializer(
            recipe_obj, context={'request': self.request}
        ).data
        return Response(serialized_data, status=status_code)

    def handle_recipe_relation_toggle(self, relation_model, target_recipe):
        """Универсальный обработчик для добавления/удаления рецепта из избранного/корзины."""
        current_request = self.request

        if current_request.method == 'POST':
            relation_obj, was_created = relation_model.objects.get_or_create(
                user=current_request.user, recipe=target_recipe
            )
            if not was_created:
                raise ValidationError('Рецепт уже добавлен в список')
            return self.create_short_recipe_response(
                target_recipe, status.HTTP_201_CREATED
            )

        existing_relation = relation_model.objects.filter(
            user=current_request.user, recipe=target_recipe
        ).first()

        if not existing_relation:
            raise ValidationError({'errors': 'Рецепт отсутствует в списке'})

        existing_relation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=('post', 'delete'),
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        """Добавление/удаление рецепта в избранное."""
        return self.handle_recipe_relation_toggle(Favorite, self.get_object())

    @action(detail=True, methods=('post', 'delete'), url_path='shopping_cart',
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        """Добавление/удаление рецепта в корзину покупок."""
        return self.handle_recipe_relation_toggle(ShoppingCart, self.get_object())

    def get_queryset(self):
        """Фильтрация рецептов по различным параметрам."""
        base_queryset = super().get_queryset()
        request_params = self.request.query_params

        author_id = request_params.get('author')
        if author_id:
            base_queryset = base_queryset.filter(author_id=author_id)

        current_user = self.request.user
        if current_user.is_authenticated:
            if request_params.get('is_favorited') == '1':
                base_queryset = base_queryset.filter(
                    favorites__user=current_user)

            if request_params.get('is_in_shopping_cart') == '1':
                base_queryset = base_queryset.filter(
                    in_carts__user=current_user)

        return base_queryset

    @action(detail=True, methods=('get',), url_path='get-link')
    def get_link(self, request, pk=None):
        """Получение короткой ссылки на рецепт."""
        try:
            recipe = self.get_object()
            short_url = request.build_absolute_uri(f'/api/recipes/{pk}/')
            return Response({'short-link': short_url})
        except Exception as e:
            return Response(
                {'error': 'Ошибка при создании ссылки'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=('get',), url_path='download_shopping_cart',
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        """Скачивание списка покупок в текстовом формате."""
        shopping_ingredients = (
            Ingredient.objects
            .filter(ingredient_recipes__recipe__in_carts__user=request.user)
            .values('name', 'measurement_unit')
            .annotate(total_amount=Sum('ingredient_recipes__amount'))
            .order_by('name')
        )

        current_datetime = datetime.now()
        report_lines = [
            f"Список покупок пользователя {request.user.username}",
            f"Дата создания: {current_datetime.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "=== ПРОДУКТЫ ===",
        ]

        for index, ingredient in enumerate(shopping_ingredients, start=1):
            product_line = (
                f"{index}. {ingredient['name'].title()} "
                f"({ingredient['measurement_unit']}) — {ingredient['total_amount']}"
            )
            report_lines.append(product_line)

        report_lines.extend([
            "",
            "=== РЕЦЕПТЫ ===",
        ])

        cart_recipes = Recipe.objects.filter(in_carts__user=request.user)
        for recipe in cart_recipes:
            recipe_line = f"• {recipe.name} (автор: {recipe.author.username})"
            report_lines.append(recipe_line)

        final_report = '\n'.join(report_lines)

        return FileResponse(
            final_report.encode('utf-8'),
            filename=f"shopping_list_{current_datetime.strftime('%Y%m%d_%H%M%S')}.txt",
            as_attachment=True,
            content_type='text/plain; charset=utf-8'
        )


class CustomUserViewSet(BaseUserViewSet):
    """Расширенный ViewSet для управления пользователями."""

    lookup_field = 'id'

    @action(detail=False, methods=('get',), permission_classes=[IsAuthenticated])
    def me(self, request, *args, **kwargs):
        """Получение информации о текущем пользователе."""
        return super().me(request, *args, **kwargs)

    @action(detail=False, methods=('put', 'delete'),
            url_path='me/avatar', permission_classes=[IsAuthenticated])
    def avatar(self, request):
        """Управление аватаром пользователя."""
        if request.method == 'PUT':
            avatar_serializer = UserAvatarSerializer(
                data=request.data,
                context={'request': request}
            )
            avatar_serializer.is_valid(raise_exception=True)

            request.user.avatar = avatar_serializer.validated_data['avatar']
            request.user.save(update_fields=['avatar'])

            return Response({'avatar': request.user.avatar.url})

        if request.user.avatar:
            request.user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=('get',),
            serializer_class=UserWithRecipesSerializer,
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        """Получение списка подписок пользователя."""
        subscribed_authors = CustomUser.objects.filter(
            following__user=request.user
        )

        paginated_authors = self.paginate_queryset(subscribed_authors)
        subscription_serializer = self.get_serializer(
            paginated_authors,
            many=True,
            context={'request': request}
        )

        return self.get_paginated_response(subscription_serializer.data)

    @action(detail=True, methods=('post', 'delete'),
            serializer_class=UserWithRecipesSerializer,
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        """Подписка/отписка от автора."""
        target_author = self.get_object()

        if request.method == 'POST':
            if target_author == request.user:
                raise ValidationError(
                    {'errors': 'Невозможно подписаться на себя'})

            follow_obj, was_created = Follow.objects.get_or_create(
                user=request.user, author=target_author
            )

            if not was_created:
                raise ValidationError({'errors': 'Подписка уже существует'})

            return Response(
                self.get_serializer(target_author).data,
                status=status.HTTP_201_CREATED
            )

        existing_follow = Follow.objects.filter(
            user=request.user, author=target_author
        ).first()

        if not existing_follow:
            raise ValidationError({'errors': 'Подписка не найдена'})

        existing_follow.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
