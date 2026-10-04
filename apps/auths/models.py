
from typing import Any

from django.contrib.auth.models import(
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)
from django.db.models import (
    BooleanField,
    CharField,
    EmailField
)



class UserManager(BaseUserManager):
    """Manager for custo user """
    EMAIL_REQUIRED_MESSAGE="Email is required"

    def create_user(
            self,
            email: str,
            password:str | None = None,
            **extra_fields:Any,
    ) -> User:
        """Create and save regular user"""
        if not email:
            raise ValueError(self.EMAIL_REQUIRED_MESSAGE)

        user=self.model(
            email=self.normalize_email(email).lower(),
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    
    def create_superuser(
            self,
            email: str,
            password:str | None = None,
            **extra_fields:Any,
    ) -> User:
        """Create and save superuser"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)
        

class User(AbstractBaseUser, PermissionsMixin):
    """Users database table"""
    NAME_MAX_LEN=50

    email=EmailField(
        unique=True
    )
    first_name=CharField(
        max_length=NAME_MAX_LEN
    )
    last_name=CharField(
            max_length=NAME_MAX_LEN
    )
    is_active=BooleanField(
        default=True
    )
    is_staff=BooleanField(
        default=False
    )

    objects=UserManager()

    USERNAME_FIELD="email"
    REQUIRED_FIELDS=["first_name","last_name"]

    def __str__(self)->str:
        return self.email