from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

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