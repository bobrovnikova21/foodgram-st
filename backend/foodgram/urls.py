from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from ninja import NinjaAPI

from users.views import router as users_router
from recipes.views import router as recipes_router

api = NinjaAPI(title="Foodgram API", version="1.0.0")

api.add_router("", users_router, tags=["Пользователи"])
api.add_router("", recipes_router, tags=["Рецепты"])


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", api.urls, name="api"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
