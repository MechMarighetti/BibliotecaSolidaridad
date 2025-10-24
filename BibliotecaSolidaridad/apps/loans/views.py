from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, CreateView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from .models import LoanRequest, Loan
from apps.books.models import Book


class LoanRequestView(LoginRequiredMixin, TemplateView):
    template_name = "loans/loan_request.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["available_books"] = Book.objects.filter(available=True)
        return context


class SubmitLoanRequestView(LoginRequiredMixin, CreateView):
    model = LoanRequest
    fields = ["book"]
    success_url = reverse_lazy("user_loans")

    def post(self, request, *args, **kwargs):
        book_id = request.POST.get("book_id")
        book = get_object_or_404(Book, id=book_id)

        if not book.available:
            messages.error(request, "Este libro no está disponible para préstamo.")
            return redirect("loans")

        LoanRequest.objects.create(
            user=request.user,
            book=book,
            status="pending"
        )
        messages.success(request, f'Solicitud de préstamo para "{book.title}" enviada correctamente.')
        return redirect("user_loans")


class UserLoansView(LoginRequiredMixin, ListView):
    template_name = "loans/user_loans.html"
    context_object_name = "loans"

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user).select_related("book").order_by("-loan_date")
