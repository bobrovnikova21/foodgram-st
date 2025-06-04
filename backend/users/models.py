from django.db import models
from django.contrib.auth.models import AbstractUser

from recipes.models import Recipe


class User(AbstractUser):
    """Расширенная модель пользователя с email и изображением профиля."""

    email = models.EmailField(unique=True, verbose_name="Электронная почта")
    avatar = models.TextField(blank=True, null=True, verbose_name="Изображение профиля")

    favorites = models.ManyToManyField(
        Recipe, blank=True, verbose_name="Любимые рецепты"
    )
    shopping_list = models.ManyToManyField(
        Recipe,
        blank=True,
        related_name="included_in_shopping_list",
        verbose_name="Список покупок",
    )
    followings = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        related_name="followers",
        verbose_name="Подписки",
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self) -> str:
        return self.username
