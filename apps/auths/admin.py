from django.contrib.admin import register
from django.contrib.auth.admin import UserAdmin

from apps.auths.models import User

@register(User)
class CustomUserAdmin(UserAdmin):
    """
    User admin class configuration """

    ordering=("email",)
    list_display=(
        "email",
        "first_name",
        "last_name",
        "is_staff"
    )

    search_fields=("email",)
    fieldsets=(
        (None,
          {"fields": (
                 "email", 
                 "password")}),

        ("Personal", 
          {"fields":(
                 "first_name",
                 "last_name"
                 )}),

        ("Permissions",
         {
             "fields": (
                 "is_active",
                 "is_staff",
                 "is_superuser",
                 "groups",
                 "user_permissions",
             ),
         }
         
     )
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
