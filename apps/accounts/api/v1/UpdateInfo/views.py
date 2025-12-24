from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .serializers import UpdateInfoSerializer

class UpdateInfoView(generics.UpdateAPIView):
    serializer_class = UpdateInfoSerializer

    def get_object(self):
        return self.request.user

    def patch(self, request, *args, **kwargs):
        partial = True  
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

__all__ = ["UpdateInfoView"]

