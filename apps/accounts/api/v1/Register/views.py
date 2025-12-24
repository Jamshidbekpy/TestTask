from rest_framework import generics
from django.contrib.auth import get_user_model

from .serializers import RegisterSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = []
    
    
__all__ = ['RegisterView']

    