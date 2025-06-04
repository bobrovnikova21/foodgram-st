import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "foodgram.settings")

application = get_wsgi_application()

# Запускаем автоматическую загрузку ингредиентов, пользователей и рецептов.
from create_data import load_components, create_users, create_dishes

load_components()
user = create_users()
create_dishes(user)
