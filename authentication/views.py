from rest_framework import generics, status, permissions
from rest_framework.response import Response
from .serializers import UserSerializer, LoginSerializer
from .utils import create_token

class SignupView(generics.CreateAPIView):
    """
    API endpoint for user signup.
    Creates a user, profile, and assigns to Inventory Managers group.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            'user': UserSerializer(user).data,
            'token': create_token(user),
            'message': 'User created successfully.'
        }, status=status.HTTP_201_CREATED)

class LoginView(generics.GenericAPIView):
    """
    API endpoint for user login.
    Returns authentication token upon successful login.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        return Response({
            'user': UserSerializer(user).data,
            'token': create_token(user),
        }, status=status.HTTP_200_OK)