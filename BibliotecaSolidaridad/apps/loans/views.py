from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, ListView, CreateView, View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from .models import LoanRequest, Loan
from apps.books.models import Book
from django.utils import timezone
from datetime import timedelta


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
    
class LoansManagerView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Vista para que los bibliotecarios gestionen las solicitudes de préstamo
    Solo accesible para usuarios con rol 'librarian' o 'admin'
    """
    model = LoanRequest
    template_name = "loans/loan_management.html"
    context_object_name = "loan_requests"
    
    def test_func(self):
        """
        UserPassesTestMixin: Define quién puede acceder a esta vista
        Retorna True si el usuario tiene permisos, False si no
        """
        return self.request.user.role in ['librarian', 'admin']
    
    def get_queryset(self):
        """
        Obtiene solo las solicitudes pendientes de aprobación
        Incluye información relacionada de usuario y libro para optimizar consultas
        """
        return LoanRequest.objects.filter(
            status='pending'
        ).select_related('user', 'book').order_by('request_date')
    
    def get_context_data(self, **kwargs):
        """
        Agrega información adicional al contexto del template
        """
        context = super().get_context_data(**kwargs)
        context['active_loans'] = Loan.objects.filter(status='active').select_related('user', 'book')
        
        # Agregar préstamos activos para referencia
        context['active_loans'] = Loan.objects.filter(
            status='active'
        ).select_related('user', 'book').order_by('-due_date')[:10]
        
        # Agregar préstamos vencidos
        context['overdue_loans'] = Loan.objects.filter(
            status='active',
            due_date__lt=timezone.now().date()
        ).select_related('user', 'book')
        
        # Estadísticas rápidas
        context['stats'] = {
            'pending_requests': self.get_queryset().count(),
            'active_loans': Loan.objects.filter(status='active').count(),
            'overdue_loans': context['overdue_loans'].count(),
            'total_books': Book.objects.filter(available=True).count(),
        }
        
        return context

class ApproveLoanRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    
    """
    Vista para aprobar una solicitud de préstamo
    """
    def test_func(self):
        return self.request.user.role in ['librarian', 'admin']
    
    def post(self, request, loan_request_id):
        loan_request = get_object_or_404(LoanRequest, id=loan_request_id, status='pending')
        
        # Verificar que el libro todavía esté disponible
        if not loan_request.book.available:
            messages.error(request, f'El libro "{loan_request.book.title}" ya no está disponible.')
            return redirect('loans_manager')
        
        # Verificar que el usuario no tenga demasiados préstamos activos
        user_active_loans = Loan.objects.filter(user=loan_request.user, status='active').count()
        max_loans = loan_request.user.get_loan_limit()
        
        if user_active_loans >= max_loans:
            messages.warning(
                request, 
                f'El usuario {loan_request.user.get_full_name()} ya tiene {user_active_loans} préstamos activos (límite: {max_loans}).'
            )
            return redirect('loans_manager')
        
        try:
            # Crear el préstamo
            loan = Loan.objects.create(
                user=loan_request.user,
                book=loan_request.book,
                loan_date=timezone.now().date(),
                due_date=timezone.now().date() + timedelta(days=15),  # 15 días por defecto
                status='active'
            )
            
            # Actualizar la solicitud
            loan_request.status = 'approved'
            loan_request.approved_by = request.user
            loan_request.approved_date = timezone.now()
            loan_request.save()
            
            # Marcar el libro como no disponible
            loan_request.book.available = False
            loan_request.book.save()
            
            messages.success(
                request, 
                f'Préstamo aprobado para {loan_request.user.get_full_name()} - "{loan_request.book.title}"'
            )
            
        except Exception as e:
            messages.error(request, f'Error al aprobar el préstamo: {str(e)}')
        
        return redirect('manage_loans')
    
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
