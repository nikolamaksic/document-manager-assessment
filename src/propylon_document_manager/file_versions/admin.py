from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, BaseFile, FileVersion

print("Registering User model with custom UserAdmin in admin.py")
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["username"]
    list_display = ("username", "email", "is_staff", "is_superuser")
    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2"),
        }),
    )

@admin.register(BaseFile)
class BaseFileAdmin(admin.ModelAdmin):
    list_display = ("id", "file_name", "latest_version_number", "owner")
    search_fields = ("file_name", "owner__username")
    list_filter = ("owner",)

@admin.register(FileVersion)
class FileVersionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "base_file",
        "version_number",
        "created_at",
        "updated_at",
        "file_hash",
    )
    search_fields = ("base_file__file_name", "file_hash")
    list_filter = ("base_file__owner", "created_at")
    raw_id_fields = ("base_file",)