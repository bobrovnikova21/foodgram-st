import json
import os
import django
import logging
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "foodgram.settings")
django.setup()

from users.models import User
from recipes.models import Recipe, Component, RecipeComponent

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(os.path.join(settings.BASE_DIR, "init.log")),
        logging.StreamHandler(),
    ],
)

# ---- ФУНКЦИЯ ЗАГРУЗКИ ПРОДУКТОВ ----


def load_components():
    file_path = os.path.join(settings.BASE_DIR, "ingredients.json")

    if not os.path.exists(file_path):
        logging.error("❌ Файл ingredients.json отсутствует!")
        return

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    existing_components = set(Component.objects.values_list("title", flat=True))

    new_components = [
        Component(title=item["name"], measurement=item["unit"])
        for item in data
        if item.get("name")
        and item.get("unit")
        and item["name"] not in existing_components
    ]

    Component.objects.bulk_create(new_components)
    logging.info(f"✅ Загружено {len(new_components)} новых продуктов!")


# ---- СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ ----


def create_users():
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@example.com", "admin", first_name="Администратор", last_name="Фудграм")
        logging.info("✅ Администратор создан!")
    else:
        logging.info("Администратор уже существует.")

    user = None
    if not User.objects.filter(username="user").exists():
        user = User.objects.create_user("user", "user@example.com", "user", first_name="Петя", last_name="Иванов")
        logging.info("✅ Обычный пользователь создан!")
    else:
        user = User.objects.get(username="user")
        logging.info("Обычный пользователь уже существует.")

    return user


# ---- СОЗДАНИЕ БЛЮД ----


def create_dishes(user):
    dishes_data = [
        {
            "name": "Бутерброд с сыром и колбасой",
            "details": "Классический бутерброд с сыром, колбасой и свежими овощами.",
            "preparation_time": 5,
            "components": [
                {"title": "Хлеб", "quantity": 60},
                {"title": "Сыр", "quantity": 40},
                {"title": "Колбаса", "quantity": 50},
                {"title": "Помидор", "quantity": 30},
            ],
        },
        {
            "name": "Тост с сыром и томатом",
            "details": "Хрустящий горячий тост с расплавленным сыром и свежими томатами.",
            "preparation_time": 10,
            "components": [
                {"title": "Хлеб", "quantity": 60},
                {"title": "Сыр", "quantity": 50},
                {"title": "Помидор", "quantity": 40},
            ],
        },
    ]

    for dish_data in dishes_data:
        dish, created = Recipe.objects.get_or_create(
            creator=user,
            name=dish_data["name"],
            defaults={
                "details": dish_data["details"],
                "preparation_time": dish_data["preparation_time"],
            },
        )

        if created:
            logging.info(f"✅ Создано новое блюдо: {dish.name}")
        else:
            logging.info(f"Блюда не добавлены.")

        for component_info in dish_data["components"]:
            component, _ = Component.objects.get_or_create(
                title=component_info["title"]
            )
            RecipeComponent.objects.get_or_create(
                dish=dish,
                component=component,
                defaults={"quantity": component_info["quantity"]},
            )


# ---- ГЛАВНЫЙ ВЫЗОВ СКРИПТА ----

if __name__ == "__main__":
    logging.info("🚀 Запуск процесса автоматического наполнения базы...")
    load_components()
    user = create_users()
    create_dishes(user)
    logging.info("🏁 Процесс завершен!")
