
from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    Favorite,
    ShoppingCart,
)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "measurement_unit", "recipes_count")
    search_fields = ("name",)
    list_filter = ("measurement_unit",)
    ordering = ("name",)
    list_per_page = 50
    empty_value_display = "—"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(recipes_total=Count("ingredient_recipes"))
        )

    def recipes_count(self, obj):
        return obj.recipes_total


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    autocomplete_fields = ("ingredient",)
    min_num = 1


class FavoriteInline(admin.TabularInline):
    """Показываем, кто добавил рецепт в избранное (только чтение)."""

    model = Favorite
    extra = 0
    readonly_fields = ("user",)
    can_delete = False
    verbose_name_plural = "В избранном у пользователей"


class ShoppingCartInline(admin.TabularInline):
    """Показываем, у кого рецепт в корзине (только чтение)."""

    model = ShoppingCart
    extra = 0
    readonly_fields = ("user",)
    can_delete = False
    verbose_name_plural = "В корзинах пользователей"


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "author",
        "cooking_time",
        "favorites_count",
        "image_preview",
        "pub_date",
    )
    list_filter = ("author", "pub_date")
    search_fields = ("name", "author__username")
    autocomplete_fields = ("author",)
    inlines = (RecipeIngredientInline, FavoriteInline, ShoppingCartInline)
    save_on_top = True
    list_per_page = 30
    readonly_fields = ("favorites_count", "image_preview")
    empty_value_display = "—"

    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("name", "author"),
                    "text",
                    ("cooking_time",),
                )
            },
        ),
        (
            "Изображение",
            {"fields": ("image", "image_preview")},
        ),
        ("Служебные", {"fields": ("pub_date",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(fav_cnt=Count("favorites"))

    def favorites_count(self, obj):
        return obj.fav_cnt

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="75" height="75" '
                'style="object-fit: cover; border-radius: 4px;" />',
                obj.image.url,
            )
        return "—"


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ("recipe", "ingredient", "amount")
    search_fields = ("recipe__name", "ingredient__name")
    autocomplete_fields = ("recipe", "ingredient")
    list_filter = ("ingredient__measurement_unit",)
    list_per_page = 50
    empty_value_display = "—"


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe")
    search_fields = ("user__username", "recipe__name")
    autocomplete_fields = ("user", "recipe")
    list_per_page = 50
    empty_value_display = "—"


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe")
    search_fields = ("user__username", "recipe__name")
    autocomplete_fields = ("user", "recipe")
    list_per_page = 50
    empty_value_display = "—"


admin.site.site_header = "Foodgram — админ-панель"
admin.site.site_title = "Foodgram admin"
admin.site.index_title = "Управление приложением Foodgram"
