from django.contrib import admin

from recipes.models import Recipe, Component, RecipeComponent


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Представление блюд в админке."""

    list_display = ("name", "creator", "preparation_time")
    list_filter = ("creator",)
    search_fields = ("name", "creator__username")


@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    """Представление продуктов в админке."""

    list_display = ("title", "measurement")
    search_fields = ("title",)


@admin.register(RecipeComponent)
class RecipeComponentAdmin(admin.ModelAdmin):
    """Представление продуктов в блюде в админке."""

    list_display = ("dish", "component", "quantity")
    search_fields = ("dish__name", "component__title")
