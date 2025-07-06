from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (CustomUserViewSet,
                    IngredientListViewSet,
                    RecipeManagementViewSet)

router = DefaultRouter()
router.register(r"users", CustomUserViewSet, basename="users")
router.register(r"ingredients", IngredientListViewSet)
router.register(r"recipes", RecipeManagementViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("auth/", include("djoser.urls.authtoken")),
    path("recipes/<int:pk>/",
         RecipeManagementViewSet.as_view({'get': 'retrieve'}), name='recipe-link'),
]
