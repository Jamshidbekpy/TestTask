from django.urls import path
from apps.calendarapp.api import UserRequestCreateView


urlpatterns = [
    path('user-requests/create/', UserRequestCreateView.as_view(), name='user-request-create'),
]
