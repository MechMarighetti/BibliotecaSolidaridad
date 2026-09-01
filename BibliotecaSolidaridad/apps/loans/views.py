from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, ListView, CreateView, View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from .models import LoanRequest, Loan
from apps.books.models import Book
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Count



class LoanRequestView(LoginRequiredMixin, TemplateView):
    template_name = "loans/loan_request.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["available_books"] = Book.objects.filter(available=True)
        return context


class SubmitLoanRequestView(LoginRequiredMixin, CreateView):
    """Crear solicitud de préstamo con validaciones"""
    model = LoanRequest
    fields = ['book', 'loan_type']
    template_name = 'loans/submit_loan_request.html'
    success_url = reverse_lazy('user_loans')
    
    def form_valid(self, form):
        """Validaciones adicionales antes de guardar"""
        form.instance.user = self.request.user
        
        # Validación 1: Usuario activo
        if not self.request.user.is_active_member:
            messages.error(self.request, "No puedes solicitar préstamos. Tu membresía no está activa.")
            return redirect('loans')
        
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
            book=form.instance.book,
            status='pending'
        ).exists()
        
        if existing:
            messages.error(self.request, "Ya tienes una solicitud pendiente para este libro.")
            return redirect('loans')
        
        messages.success(
            self.request, 
            f'Solicitud de préstamo para "{form.instance.book.title}" enviada.'
        )
        return super().form_valid(form)
    
class LoansManagerView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Panel de gestión de préstamos para bibliotecarios"""
    model = LoanRequest
    template_name = 'loans/loan_management.html'
    context_object_name = 'pending_requests'
    
    def test_func(self):
        return self.request.user.role in ['librarian', 'admin']
    
    def get_queryset(self):
        return LoanRequest.objects.filter(
            status='pending'
        ).select_related('user', 'book').order_by('-request_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
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
            'pending_requests': self.get_queryset().count(),
            'active_loans': Loan.objects.filter(status='active').count(),
            'overdue_count': context['overdue_loans'].count(),
        }
        
        return context

class ApproveLoanRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Aprobar solicitud de préstamo y crear préstamo"""
    
    def test_func(self):
        return self.request.user.role in ['librarian', 'admin']
    
    def post(self, request, request_id):
        request_obj = get_object_or_404(LoanRequest, id=request_id)
        
        try:
            # El modelo maneja la lógica
            loan = request_obj.approve(approved_by=request.user)
            messages.success(
                request, 
                f'Préstamo de "{request_obj.book.title}" aprobado. Entrega al usuario.'
            )
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('loan_management')


class RejectLoanRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Rechazar solicitud de préstamo"""
    
    def test_func(self):
        return self.request.user.role in ['librarian', 'admin']
    
    def post(self, request, request_id):
        request_obj = get_object_or_404(LoanRequest, id=request_id)
        
        try:
            request_obj.reject()
            messages.success(
                request, 
                f'Solicitud de "{request_obj.book.title}" rechazada.'
            )
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('loan_management')
    
class ReturnBookView(LoginRequiredMixin, UserPassesTestMixin, View):
    
    def test_func(self):
        return self.request.user.role in ['librarian', 'admin']
    
    def post(self, request, loan_id):
        loan = get_object_or_404(Loan, id=loan_id, status='active')
        
        try:
            # Actualizar el préstamo
            loan.status = 'returned'
            loan.return_date = timezone.now().date()
            loan.save()
            
            # Marcar el libro como disponible
            loan.book.available = True
            loan.book.save()
            
            messages.success(
                request, 
                f'Libro "{loan.book.title}" devuelto por {loan.user.get_full_name()}'
            )
            
        except Exception as e:
            messages.error(request, f'Error al registrar la devolución: {str(e)}')
        
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
        loan = get_object_or_404(Loan, id=loan_id, status='active')
        
        try:
            # Marcar préstamo como devuelto
            loan.status = 'returned'
            loan.return_date = timezone.now().date()
            loan.save()
            
            # Marcar libro como disponible
            loan.book.available = True
            loan.book.save()
            
            # Calcular si hubo mora
            if loan.return_date > loan.due_date:
                days_overdue = (loan.return_date - loan.due_date).days
                # Aplicar penalización por mora
                loan.user.score = max(0, loan.user.score - (days_overdue * 0.5))
                loan.user.save()
                
                messages.warning(
                    request, 
                    f'Libro devuelto con {days_overdue} días de mora. Puntuación del usuario actualizada.'
                )
            else:
                messages.success(request, f'Libro "{loan.book.title}" devuelto correctamente.')
            
        except Exception as e:
            messages.error(request, f'Error al registrar devolución: {str(e)}')
        
        return redirect('loans_manager')

class UserLoansView(LoginRequiredMixin, ListView):
    template_name = "loans/user_loans.html"
    context_object_name = "loans"

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user).select_related("book").order_by("-loan_date")
