from django.urls import path
from .views import LoanRequestView, SubmitLoanRequestView, UserLoansView, LoansManagerView, ApproveLoanRequestView, RejectLoanRequestView, ReturnBookView

urlpatterns = [
    path('', LoanRequestView.as_view(), name='loans'),
    path('approved/<int:loan_request_id>', ApproveLoanRequestView.as_view(), name='approve_loan_request'),
    path('rejected/<int:loan_request_id>', RejectLoanRequestView.as_view(), name='reject_loan_request'),
    path('submit/', SubmitLoanRequestView.as_view(), name='submit_loan_request'),
    path('my/', UserLoansView.as_view(), name='user_loans'),
    path('gestionar/', LoansManagerView.as_view(), name='manage_loans'),
    path('return/<int:loan_id>/', ReturnBookView.as_view(), name='return_book'),
]
