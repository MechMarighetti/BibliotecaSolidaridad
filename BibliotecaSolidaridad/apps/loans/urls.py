from django.urls import path
from . import views

urlpatterns = [
    path('', views.loans, name='loans'),
    path('submit/', views.submit_loan_request, name='submit_loan_request'),
]