from django.urls import path
from . import views

urlpatterns = [
    path('', views.users, name='users'),
    path('profile/', views.users, name='profile'),
    path('login/', views.users, name='login'),
    path('register/', views.users, name='register'),
    path('logout/', views.users, name='logout'),
    path('user_loans/', views.users, name='user_loans'),
]