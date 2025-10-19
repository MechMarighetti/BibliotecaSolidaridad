from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import LoanRequest, Book

def loans(request):
    return render(request, 'loans/loan_request.html')



@login_required
def submit_loan_request(request, book_id=None):
    if request.method == 'POST':
        # Si recibes el book_id por POST
        book_id = request.POST.get('book_id', book_id)
        book = get_object_or_404(Book, id=book_id)
        
        # Verificar si el libro está disponible
        if not book.is_available:
            messages.error(request, 'Este libro no está disponible para préstamo.')
            return redirect('book_list')  # o donde quieras redirigir
        
        # Crear la solicitud de préstamo
        loan_request = LoanRequest.objects.create(
            user=request.user,
            book=book,
            status='pending'  # o el estado inicial que uses
        )
        
        messages.success(request, f'Solicitud de préstamo para "{book.title}" enviada correctamente.')
        return redirect('loans')  # Redirige a la lista de préstamos
    
    # Si es GET, mostrar formulario o procesar de otra manera
    return redirect('book_list')