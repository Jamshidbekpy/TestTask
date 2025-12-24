from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .api import RegisterView, EmailLoginAPIView, LogoutAPIView, MeAPIView, UpdateInfoView


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", EmailLoginAPIView.as_view(), name="email-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("me/", MeAPIView.as_view(), name="me"),
    path("update-info/", UpdateInfoView.as_view(), name="update-info"),  
]