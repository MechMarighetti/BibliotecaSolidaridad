from django.urls import path
from .views import SubscribeNewsletterView, UnsubscribeByEmailView, UnsubscribeNewsletterView

urlpatterns = [
    path('subscribe/', SubscribeNewsletterView.as_view(), name='subscribe_newsletter'),
    path('unsubscribe/<str:token>/', UnsubscribeNewsletterView.as_view(), name='unsubscribe_newsletter'),
    path('unsubscribe/', UnsubscribeByEmailView.as_view(), name='unsubscribe_by_email'),
]