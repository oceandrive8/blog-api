from typing import Any 

from rest_framework.serializers import BaseSerializer


class ValidatedSerializerMixin:
    """Builds a serilizer, validates it and raises a 400 on errors."""

    def get_valid_serializer(
            self,
            serilizer_class: type[BaseSerializer],
            data: Any,
            **kwargs: Any,
    ) -> BaseSerializer:
        serilizer = serilizer_class(data=data, **kwargs)
        serilizer.is_valid(raise_exception=True)
        return serilizer


