# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import Count, Q
from django.utils.html import format_html

from .models import User, Follow


class HasAvatarFilter(admin.SimpleListFilter):
    title = "Наличие аватара"
    parameter_name = "has_avatar"

    def lookups(self, request, model_admin):
        return (("yes", "С аватаром"), ("no", "Без аватара"))

    def queryset(self, request, qs):
        if self.value() == "yes":
            return qs.exclude(avatar="")
        if self.value() == "no":
            return qs.filter(Q(avatar="") | Q(avatar__isnull=True))


class FollowingInline(admin.TabularInline):
    model = Follow
    fk_name = "user"
    verbose_name_plural = "Подписки пользователя"
    extra = 0
    autocomplete_fields = ("author",)
    can_delete = False


class FollowerInline(admin.TabularInline):
    model = Follow
    fk_name = "author"
    verbose_name_plural = "Подписчики"
    extra = 0
    autocomplete_fields = ("user",)
    can_delete = False


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "avatar_thumb",
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "followers_count",
        "following_count",
        "date_joined",
    )
    list_display_links = ("username", "email")
    list_filter = ("is_staff", "is_active", "date_joined", HasAvatarFilter)
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)
    list_per_page = 50
    readonly_fields = (
        "avatar_preview",
        "followers_count",
        "following_count",
        "last_login",
        "date_joined",
    )
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Персональные данные",
            {"fields": ("username", "first_name", "last_name",
                        "avatar", "avatar_preview")},
        ),
        ("Показатели", {"fields": ("followers_count", "following_count")}),
        (
            "Права доступа",
            {"fields": ("is_active", "is_staff", "is_superuser",
                        "groups", "user_permissions")},
        ),
        ("Важные даты", {"fields": ("last_login", "date_joined")}),
    )
    inlines = (FollowingInline, FollowerInline)
    save_on_top = True
    empty_value_display = "—"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(followers_total=Count("followers"), following_total=Count("following"))
        )

    def followers_count(self, obj):
        return obj.followers_total

    def following_count(self, obj):
        return obj.following_total

    def avatar_thumb(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" width="40" height="40" '
                'style="object-fit: cover; border-radius: 50%;" />',
                obj.avatar.url,
            )
        return "—"

    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" width="120" height="120" '
                'style="object-fit: cover; border-radius: 6px;" />',
                obj.avatar.url,
            )
        return "—"


admin.site.site_header = "Foodgram — админ-панель"
admin.site.site_title = "Foodgram admin"
admin.site.index_title = "Управление Foodgram"
