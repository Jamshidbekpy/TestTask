from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("id", "email","is_active", "is_staff")
    list_filter = ("is_active", "is_staff")
    search_fields = ("email",)
    ordering = ("email",)
    readonly_fields = ("last_login", "date_joined")

    # Default fieldsets
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "bio",
                    "avatar",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",     # faqat superuser ko‘radi
                    "groups",           # faqat superuser ko‘radi
                    "user_permissions", # faqat superuser ko‘radi
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    # Create user page uchun
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_active", "is_staff"),
            },
        ),
    )

    def get_fieldsets(self, request, obj=None):
        """Superuser bo‘lmasa, xavfli permission fieldlarni yashiramiz"""
        fieldsets = super().get_fieldsets(request, obj)
        if not request.user.is_superuser:
            new_fieldsets = []
            for name, opts in fieldsets:
                if name == "Permissions":
                    opts = opts.copy()
                    opts["fields"] = tuple(
                        f
                        for f in opts["fields"]
                        if f not in ("is_superuser", "groups", "user_permissions")
                    )
                new_fieldsets.append((name, opts))
            return new_fieldsets
        return fieldsets
