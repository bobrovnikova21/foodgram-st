from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import json
from pathlib import Path

from recipes.models import Ingredient


class Command(BaseCommand):
    help = "Импортирует ингредиенты из data/ingredients.json"

    def handle(self, *args, **kwargs):
        try:
            raw = json.loads(
                (Path(settings.BASE_DIR) / "data" /
                 "ingredients.json").read_text(encoding="utf-8")
            )
        except FileNotFoundError:
            raise CommandError("Файл ingredients.json не найден.")
        except json.JSONDecodeError as exc:
            raise CommandError(f"Некорректный JSON: {exc}")

        objs = [
            Ingredient(name=i["name"], measurement_unit=i["unit"])
            for i in raw
            if i.get("name") and i.get("unit")
        ]

        added = Ingredient.objects.bulk_create(objs, ignore_conflicts=True)
        self.stdout.write(
            self.style.SUCCESS(
                f"Добавлено {len(added)}, пропущено {len(objs) - len(added)}."
            )
        )
