from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.auths.constants import ACCESS_TOKEN_HEADER, REFRESH_TOKEN_HEADER
from apps.auths.serializers import LoginSerializer, ProfileUpdateSerializer, RegisterSerializer, UserSerializer
from apps.mixins import ValidatedSerializerMixin



class UserViewSet(ValidatedSerializerMixin, viewsets.ViewSet):
    @action(
            detail=False, 
            methods=['post'], 
            permission_classes=[AllowAny], 
            authentication_classes=[],
    )
    def register(self, request:Request)->Response:
        serializer = self.get_valid_serializer(RegisterSerializer, request.data)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
       

    @action(
            detail=False, 
            methods=['post'], 
            permission_classes=[AllowAny], 
            authentication_classes=[],
    )
    def login(self, request:Request)->Response:
        serializer = self.get_valid_serializer(LoginSerializer, request.data)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return Response(
            UserSerializer(user).data, 
            status=status.HTTP_200_OK, 
            headers={
                ACCESS_TOKEN_HEADER: str(refresh.access_token),
                REFRESH_TOKEN_HEADER: str(refresh),
                },
            )

    @action(
            detail=False, 
            methods=["get", "patch"], 
            url_path="me"
        )
    def me(self, request: Request)->Response:
        if request.method == "PATCH":
            serializer = self.get_valid_serializer(
                ProfileUpdateSerializer,
                request.data,
                instance=request.user,
                partial=True,
            )
            serializer.save()
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)

class HeaderTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request, *args, **kwargs) -> Response:
        response = super().post(request, *args, **kwargs)
        response[ACCESS_TOKEN_HEADER] = response.data.pop("access")
        response.data = {}
        return response
    
