from django.urls import path
# from apps.calendarapp.api import EventCreateAPIView, EventRetrieveDestroyAPIView, EventListAPIView, EventUpdateAPIView


# urlpatterns = [
#     path('events/create/', EventCreateAPIView.as_view(), name='event-create'),
#     path('events/<uuid:pk>/', EventRetrieveDestroyAPIView.as_view(), name='event-retrieve-destroy'),
#     path('events/', EventListAPIView.as_view(), name='event-list'),
#     path('events/<uuid:pk>/update/', EventUpdateAPIView.as_view(), name='event-update'),
# ]

# apps/calendar/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Events
    path('events/', views.EventListCreateAPIView.as_view(), name='event-list-create'),
    path('events/<uuid:id>/', views.EventDetailAPIView.as_view(), name='event-detail'),
    path('events/<uuid:id>/cancel/', views.CancelEventAPIView.as_view(), name='event-cancel'),
    path('events/today/', views.TodayEventsAPIView.as_view(), name='today-events'),
    path('events/upcoming/', views.UpcomingEventsAPIView.as_view(), name='upcoming-events'),
    path('events/filter/', views.EventsByDateRangeAPIView.as_view(), name='events-by-date'),
    
    # Event invites & alerts
    path('events/<uuid:event_id>/invites/', views.EventInviteListAPIView.as_view(), name='event-invites'),
    path('events/<uuid:event_id>/alerts/', views.EventAlertListAPIView.as_view(), name='event-alerts'),
    
    # Invites
    path('invites/my/', views.MyInvitesAPIView.as_view(), name='my-invites'),
    path('invites/<uuid:invite_id>/respond/', views.RespondToInviteAPIView.as_view(), name='respond-invite'),
    
    # NLP Parser
    path('parse/', views.ParseTextView.as_view(), name='parse-text'),
    path('draft/confirm/', views.ConfirmDraftView.as_view(), name='confirm-draft'),
    
    # History & Logs
    path('requests/', views.UserRequestListAPIView.as_view(), name='user-requests'),
    path('audit-logs/', views.AuditLogListAPIView.as_view(), name='audit-logs'),
]