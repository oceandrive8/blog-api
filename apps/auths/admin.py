from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import BooleanRadioFilter
from unfold.decorators import action, display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

User = get_user_model()

admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    change_password_form = AdminPasswordChangeForm

    ordering = ("-id",)
    list_display = ("header", "active_label", "staff_label", "posts_total")
    list_filter = [
        ("is_active", BooleanRadioFilter),
        ("is_staff", BooleanRadioFilter),
    ]
    list_filter_submit = True
    search_fields = ("email", "first_name", "last_name")
    readonly_fields = ("last_login",)
    actions = ["activate_users", "deactivate_users"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {"fields": ("first_name", "last_name"), "classes": ["tab"]},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "classes": ["tab"],
            },
        ),
        (
            "Important dates",
            {"fields": ("last_login",), "classes": ["tab"]},
        ),
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

    def get_queryset(self, request: HttpRequest) -> QuerySet[User]:
        return super().get_queryset(request).annotate(posts_count=Count("posts"))

    @display(description="User", header=True)
    def header(self, obj: User) -> list[str]:
        full_name = obj.get_full_name() or obj.email
        initials = (obj.first_name[:1] + obj.last_name[:1]).upper()
        return [full_name, obj.email, initials or obj.email[:1].upper()]

    @display(description="Active", label={True: "success", False: "danger"})
    def active_label(self, obj: User) -> tuple[bool, str]:
        return obj.is_active, "Active" if obj.is_active else "Inactive"

    @display(description="Staff", label={True: "info", False: "warning"})
    def staff_label(self, obj: User) -> tuple[bool, str]:
        return obj.is_staff, "Staff" if obj.is_staff else "User"

    @display(description="Posts", ordering="posts_count")
    def posts_total(self, obj: User) -> int:
        return obj.posts_count

    @action(description="Activate selected users", permissions=["change"])
    def activate_users(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} user(s) activated.")

    @action(description="Deactivate selected users", permissions=["change"])
    def deactivate_users(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} user(s) deactivated.")