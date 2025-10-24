from django.urls import path
from .views import LoanRequestView, SubmitLoanRequestView, UserLoansView

urlpatterns = [
    path('', LoanRequestView.as_view(), name='loans'),
    path('submit/', SubmitLoanRequestView.as_view(), name='submit_loan_request'),
    path('my/', UserLoansView.as_view(), name='user_loans'),
]
