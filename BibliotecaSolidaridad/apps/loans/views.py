from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, ListView, CreateView, View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.db import transaction
from .models import LoanRequest, Loan
from apps.books.models import Book, BookStock
from .availability import available_books_queryset, available_copy_count
from django.utils import timezone
import logging


class LoanRequestView(LoginRequiredMixin, TemplateView):
    template_name = "loans/loan_request.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["available_books"] = available_books_queryset().prefetch_related(
            'authors'
        )
        return context


class SubmitLoanRequestView(LoginRequiredMixin, CreateView):
    """Crear solicitud de préstamo con validaciones"""
    model = LoanRequest
    fields = ['book', 'loan_type']
    template_name = 'loans/submit_loan_request.html'
    success_url = reverse_lazy('user_loans')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in ('reader', 'librarian'):
            messages.error(
                request,
                'Solo lectores y bibliotecarios pueden solicitar préstamos.',
            )
            return redirect('book_search')
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['book'].queryset = available_books_queryset().prefetch_related(
            'authors'
        )
        return form
    
    def form_valid(self, form):
        """Validaciones adicionales antes de guardar"""
        form.instance.user = self.request.user
        
        # Validación 1: Usuario activo
        if not self.request.user.is_active_member:
            messages.error(self.request, "No puedes solicitar préstamos. Tu membresía no está activa.")
            return redirect('loans')

        book = form.instance.book
        if not book.available or available_copy_count(book) < 1:
            messages.error(
                self.request,
                f'No hay copias disponibles de "{book.title}" en este momento.',
            )
            return redirect('book_detail', pk=book.pk)
        
        # Validación 2: Límite de préstamos
        active_loans = Loan.objects.filter(
            user=self.request.user,
            status='active'
        ).count()
        
        if active_loans >= self.request.user.get_loan_limit():
            messages.error(
                self.request, 
                f"Has alcanzado tu límite de préstamos ({active_loans}). Devuelve alguno primero."
            )
            return redirect('loans')
        
        # Validación 3: No duplicar solicitud pendiente
        existing = LoanRequest.objects.filter(
            user=self.request.user,
            book=book,
            status='pending'
        ).exists()
        
        if existing:
            messages.error(self.request, "Ya tienes una solicitud pendiente para este libro.")
            return redirect('book_detail', pk=book.pk)

        already_borrowed = Loan.objects.filter(
            user=self.request.user,
            book=book,
            status='active',
        ).exists()
        if already_borrowed:
            messages.error(
                self.request,
                'Ya tienes un préstamo activo de este libro.',
            )
            return redirect('book_detail', pk=book.pk)
        
        messages.success(
            self.request, 
            f'Solicitud de préstamo para "{book.title}" enviada.'
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        # Mostrar errores como mensajes y redirigir al listado para evitar responder 200 con formulario inválido
        for field, errors in form.errors.items():
            for err in errors:
                messages.error(self.request, f"{field}: {err}")
        book_id = form.data.get('book', '')
        if book_id.isdigit() and Book.objects.filter(pk=book_id).exists():
            return redirect('book_detail', pk=book_id)
        return redirect('loans')
    
class LoansManagerView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Panel de gestión de préstamos para bibliotecarios"""
    model = LoanRequest
    template_name = 'loans/loan_management.html'
    # Template expects `loan_requests` variable
    context_object_name = 'loan_requests'
    
    def test_func(self):
        return self.request.user.role in ['librarian', 'admin']
    
    def get_queryset(self):
        return LoanRequest.objects.filter(
            status='pending'
        ).select_related('user', 'book').order_by('-request_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ensure loan_requests is present and evaluated to avoid template/qs mismatches
        loan_reqs = list(self.get_queryset())
        context['loan_requests'] = loan_reqs
        # Debug helpers
        try:
            context['debug_loan_ids'] = [lr.id for lr in loan_reqs]
            logging.getLogger('apps').debug('LoansManagerView loan_reqs ids: %s', context['debug_loan_ids'])
        except Exception:
            context['debug_loan_ids'] = []

        # Préstamos activos
        context['active_loans'] = Loan.objects.filter(
            status='active'
        ).select_related('user', 'book').order_by('-due_date')[:20]
        
        # Préstamos vencidos (solo los activos pero con fecha vencida)
        today = timezone.now().date()
        context['overdue_loans'] = Loan.objects.filter(
            status='active',
            due_date__lt=today
        ).select_related('user', 'book').order_by('due_date')
        
        # Estadísticas
        context['stats'] = {
            'pending_requests': len(loan_reqs),
            'active_loans': Loan.objects.filter(status='active').count(),
            'overdue_loans': context['overdue_loans'].count(),
            'total_books': available_books_queryset().count(),
        }
        
        return context

class ApproveLoanRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Aprobar solicitud de préstamo y crear préstamo"""
    
    def test_func(self):
        return self.request.user.role in ['librarian', 'admin']
    
    def post(self, request, loan_request_id):
        request_obj = get_object_or_404(LoanRequest, id=loan_request_id)

        try:
            request_obj.approve(approved_by=request.user)
            messages.success(
                request,
                f'Préstamo de "{request_obj.book.title}" aprobado. Entrega al usuario.'
            )
        except ValueError as e:
            messages.error(request, str(e))

        return redirect('manage_loans')



class RejectLoanRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Vista para rechazar una solicitud de préstamo
    """
    def test_func(self):
        return self.request.user.role in ['librarian', 'admin']
    
    def post(self, request, loan_request_id):
        loan_request = get_object_or_404(LoanRequest, id=loan_request_id, status='pending')
        
        try:
            loan_request.status = 'rejected'
            loan_request.approved_by = request.user
            loan_request.approved_date = timezone.now()
            loan_request.save()
            
            messages.info(
                request, 
                f'Solicitud rechazada para {loan_request.user.get_full_name()} - "{loan_request.book.title}"'
            )
            
        except Exception as e:
            messages.error(request, f'Error al rechazar la solicitud: {str(e)}')
        
        return redirect('manage_loans')

class ReturnBookView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Vista para registrar la devolución de un libro
    """
    def test_func(self):
        return self.request.user.role in ['librarian', 'admin']
    
    def post(self, request, loan_id):
        with transaction.atomic():
            loan = get_object_or_404(
                Loan.objects.select_for_update().select_related(
                    'book', 'user', 'stock_item'
                ),
                id=loan_id,
                status='active',
            )
            loan.status = 'returned'
            loan.return_date = timezone.now().date()
            loan.save(update_fields=['status', 'return_date'])

            if loan.stock_item_id:
                BookStock.objects.filter(
                    pk=loan.stock_item_id,
                    status='borrowed',
                ).update(status='available')

            if loan.return_date > loan.due_date:
                days_overdue = (loan.return_date - loan.due_date).days
                loan.user.score = max(0, loan.user.score - (days_overdue * 0.5))
                loan.user.save()
                messages.warning(
                    request, 
                    f'Libro devuelto con {days_overdue} días de mora. Puntuación del usuario actualizada.'
                )
            else:
                messages.success(request, f'Libro "{loan.book.title}" devuelto correctamente.')

        return redirect('manage_loans')

class UserLoansView(LoginRequiredMixin, ListView):
    template_name = "loans/user_loans.html"
    context_object_name = "loans"

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user).select_related("book").order_by("-loan_date")
