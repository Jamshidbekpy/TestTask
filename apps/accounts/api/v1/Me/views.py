from rest_framework import views
from rest_framework.response import Response
from rest_framework import status
from .serializers import MeSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class MeAPIView(views.APIView):
    def get(self, request, *args, **kwargs):
        pk = request.user.id
        user = User.objects.get(pk=pk)
        serializer = MeSerializer(user)
        
        return Response(serializer.data, status=status.HTTP_200_OK)

__all__ = ['MeAPIView']
    