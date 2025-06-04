from ninja import Schema


class RecipeSchema(Schema):
    """Схема для представления рецепта."""

    name: str
    text: str
    cooking_time: int
    ingredients: list[dict[str, int | str]]
    image: str | None


class RecipeUpdateSchema(Schema):
    """Схема для обновления рецепта."""

    name: str | None = None
    text: str | None = None
    cooking_time: int | None = None
    image: str | None = None
    ingredients: list | None = None
