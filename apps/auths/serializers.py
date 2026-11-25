from django.contrib.auth import get_user_model, password_validation
from rest_framework import serializers

from apps.auths.constants import INVALID_CREDENTIALS_MESSAGE

User=get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Output only the user's public data"""

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "password")
        extra_kwargs = {"password": {"write_only": True}}

    def validate_email(self, value: str) -> str:
        value = value.lower()
        # The built-in unique check ran before .lower(), so check again.
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value

    def validate_password(self, value: str) -> str:
        # Django's ValidationError becomes a normal 400 inside validate_<field>()
        password_validation.validate_password(value)
        return value

    def create(self, validated_data: dict) -> User:
        # Without this, save() would store the password as plain text.
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict) -> dict:
        user = User.objects.filter(email=attrs["email"].lower()).first()
        if (
            user is None 
            or not user.check_password(attrs["password"])
            or not user.is_active
        ):
            raise serializers.ValidationError(INVALID_CREDENTIALS_MESSAGE)
        attrs["user"] = user
        return attrs


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_nime']