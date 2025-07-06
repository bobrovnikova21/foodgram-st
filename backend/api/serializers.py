from __future__ import annotations

from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer as BaseUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError

from recipes.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    Favorite,
    ShoppingCart,
)
from users.models import Follow

CustomUser = get_user_model()


class UserAvatarSerializer(serializers.Serializer):
    """Сериализатор для загрузки аватарки пользователя."""
    avatar = Base64ImageField(required=True, allow_empty_file=False)

    def validate_avatar(self, value):
        if not value:
            raise serializers.ValidationError("Аватар не может быть пустым")
        return value


class ExtendedUserSerializer(BaseUserSerializer):
    """Расширенный сериализатор пользователя с аватаром и подписками."""

    avatar = serializers.ImageField(read_only=True)
    is_subscribed = serializers.SerializerMethodField(
        method_name='check_subscription_status')

    class Meta(BaseUserSerializer.Meta):
        fields = (*BaseUserSerializer.Meta.fields, "avatar", "is_subscribed")

    def check_subscription_status(self, target_user):
        """Проверяет, подписан ли текущий пользователь на данного автора."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        current_user = request.user
        return Follow.objects.filter(
            user=current_user,
            author=target_user
        ).exists()


class IngredientDataSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения данных ингредиента."""

    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")
        read_only_fields = ("id", "name", "measurement_unit")


class RecipeIngredientDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор ингредиента в рецепте для чтения."""

    id = serializers.IntegerField(source="ingredient.id", read_only=True)
    name = serializers.CharField(source="ingredient.name", read_only=True)
    measurement_unit = serializers.CharField(
        source="ingredient.measurement_unit", read_only=True
    )
    amount = serializers.IntegerField(read_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")
        read_only_fields = ("id", "name", "measurement_unit", "amount")


class RecipeDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор рецепта для чтения."""

    author = ExtendedUserSerializer(read_only=True)
    ingredients = RecipeIngredientDetailSerializer(
        many=True, source="recipe_ingredients", read_only=True
    )
    image = serializers.ImageField(read_only=True)
    is_favorited = serializers.SerializerMethodField(
        method_name='check_favorite_status')
    is_in_shopping_cart = serializers.SerializerMethodField(
        method_name='check_cart_status')

    class Meta:
        model = Recipe
        fields = (
            "id", "author", "ingredients", "is_favorited",
            "is_in_shopping_cart", "name", "image", "text", "cooking_time",
        )
        read_only_fields = (
            "id", "author", "ingredients", "is_favorited",
            "is_in_shopping_cart", "name", "image", "text", "cooking_time",
        )

    def check_favorite_status(self, recipe_obj):
        """Проверяет, добавлен ли рецепт в избранное."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        current_user = request.user
        return Favorite.objects.filter(
            user=current_user,
            recipe=recipe_obj
        ).exists()

    def check_cart_status(self, recipe_obj):
        """Проверяет, добавлен ли рецепт в корзину покупок."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        current_user = request.user
        return ShoppingCart.objects.filter(
            user=current_user,
            recipe=recipe_obj
        ).exists()


class RecipeIngredientInputSerializer(serializers.Serializer):
    """Сериализатор для ввода ингредиентов при создании/редактировании рецепта."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        error_messages={
            'does_not_exist': 'Указанный ингредиент не существует.'}
    )
    amount = serializers.IntegerField(
        min_value=1,
        error_messages={
            'min_value': 'Количество ингредиента должно быть больше 0.',
            'invalid': 'Количество должно быть числом.'
        }
    )


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""

    ingredients = RecipeIngredientInputSerializer(many=True, write_only=True)
    image = Base64ImageField(write_only=True, required=True)

    class Meta:
        model = Recipe
        fields = ("ingredients", "image", "name", "text", "cooking_time")

    def validate_cooking_time(self, cooking_time_value):
        """Валидация времени приготовления."""
        if cooking_time_value < 1:
            raise serializers.ValidationError(
                'Время приготовления должно быть не менее 1 минуты'
            )
        return cooking_time_value

    def validate_ingredients(self, ingredients_list):
        """Валидация списка ингредиентов."""
        if not ingredients_list:
            raise serializers.ValidationError(
                'Необходимо указать хотя бы один ингредиент'
            )

        ingredient_ids = [ingredient_data['id']
                          for ingredient_data in ingredients_list]
        unique_ids = set(ingredient_ids)

        if len(ingredient_ids) != len(unique_ids):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться'
            )
        return ingredients_list

    def validate(self, data_attrs):
        """Общая валидация данных."""
        if self.instance and 'ingredients' not in self.initial_data:
            raise serializers.ValidationError(
                {'ingredients': 'Поле ингредиентов обязательно для заполнения.'}
            )

        if 'image' in self.initial_data and not self.initial_data['image']:
            raise serializers.ValidationError(
                {'image': 'Поле изображения не может быть пустым.'}
            )
        return data_attrs

    def create_recipe_ingredients(self, recipe_instance: Recipe, ingredients_data):
        """Создание связей рецепт-ингредиент."""
        # Удаляем старые связи
        recipe_instance.recipe_ingredients.all().delete()

        # Создаем новые связи
        ingredient_objects = [
            RecipeIngredient(
                recipe=recipe_instance,
                ingredient=ingredient_data["id"],
                amount=ingredient_data["amount"],
            )
            for ingredient_data in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(ingredient_objects)

    def create(self, validated_data):
        """Создание нового рецепта."""
        ingredients_data = validated_data.pop("ingredients")
        new_recipe = super().create(validated_data)
        self.create_recipe_ingredients(new_recipe, ingredients_data)
        return new_recipe

    def update(self, recipe_instance, validated_data):
        """Обновление существующего рецепта."""
        ingredients_data = validated_data.pop("ingredients", None)
        updated_recipe = super().update(recipe_instance, validated_data)

        if ingredients_data is not None:
            self.create_recipe_ingredients(updated_recipe, ingredients_data)
        return updated_recipe

    def to_representation(self, recipe_instance):
        """Преобразование в представление для ответа."""
        return RecipeDetailSerializer(
            recipe_instance,
            context=self.context
        ).data


class RecipeSummarySerializer(serializers.ModelSerializer):
    """Краткий сериализатор рецепта для списков."""

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")
        read_only_fields = ("id", "name", "image", "cooking_time")


class UserWithRecipesSerializer(ExtendedUserSerializer):
    """Сериализатор пользователя с его рецептами и их количеством."""

    recipes = serializers.SerializerMethodField(method_name='get_user_recipes')
    recipes_count = serializers.IntegerField(
        source="recipes.count", read_only=True
    )

    class Meta(ExtendedUserSerializer.Meta):
        fields = (*ExtendedUserSerializer.Meta.fields,
                  "recipes", "recipes_count")

    def get_user_recipes(self, user_obj):
        """Получение рецептов пользователя с учетом лимита."""
        recipes_limit = self.context["request"].query_params.get(
            "recipes_limit")
        user_recipes = user_obj.recipes.all()

        if recipes_limit and recipes_limit.isdigit():
            user_recipes = user_recipes[:int(recipes_limit)]

        return RecipeSummarySerializer(
            user_recipes,
            many=True,
            context=self.context
        ).data
