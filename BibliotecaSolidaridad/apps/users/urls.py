from django.urls import path
from .views import CustomLoginView, CustomLogoutView, RegisterView, CarnetView

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('carnet/', CarnetView.as_view(), name='virtual_card'),
]
