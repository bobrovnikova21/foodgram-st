from django.db import models


class Recipe(models.Model):
    """Модель блюда с автором и списком ингредиентов."""

    creator = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, verbose_name="Создатель"
    )
    name = models.CharField(max_length=200, verbose_name="Название блюда")
    image_url = models.TextField(
        verbose_name="Ссылка на изображение", blank=True, null=True
    )
    details = models.TextField(verbose_name="Описание рецепта")
    components = models.ManyToManyField(
        "Component", through="RecipeComponent", verbose_name="Состав"
    )
    preparation_time = models.PositiveIntegerField(verbose_name="Время готовки")

    class Meta:
        ordering = ["-id"]
        verbose_name = "Блюдо"
        verbose_name_plural = "Блюда"

    def __str__(self):
        return f"{self.name} (Создатель: {self.creator.username})"


class Component(models.Model):
    """Модель продукта с названием и единицей измерения."""

    title = models.CharField(
        max_length=100, unique=True, verbose_name="Название продукта"
    )
    measurement = models.CharField(max_length=50, verbose_name="Единица измерения")

    class Meta:
        ordering = ["title"]
        verbose_name = "Продукт"
        verbose_name_plural = "Продукты"

    def __str__(self) -> str:
        return f"{self.title} ({self.measurement})"


class RecipeComponent(models.Model):
    """Связь между блюдами и их ингредиентами."""

    dish = models.ForeignKey(Recipe, on_delete=models.CASCADE, verbose_name="Блюдо")
    component = models.ForeignKey(
        Component, on_delete=models.CASCADE, verbose_name="Продукт"
    )
    quantity = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="Количество"
    )

    class Meta:
        verbose_name = "Продукт в блюде"
        verbose_name_plural = "Продукты в блюдах"

    def __str__(self) -> str:
        return f"{self.component.title} - {self.quantity} {self.component.measurement} для {self.dish.name}"
