from django.urls import path
from .views import LibrarianDashboardView

urlpatterns = [
    path('', LibrarianDashboardView.as_view(), name='dashboard'),
]