from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.db.models import Count, Avg, Q
from apps.books.models import Book, Category, Review
from apps.loans.models import Loan
from apps.users.models import User

def is_librarian(user):
    return user.is_authenticated and (user.role == 'librarian' or user.role == 'admin')

@login_required
@user_passes_test(is_librarian)
def dashboard(request):
    # KPIs principales
    kpis = {
        'active_loans': Loan.objects.filter(status='active').count(),
        'active_members': User.objects.filter(is_active_member=True).count(),
        'overdue_loans': Loan.objects.filter(status='overdue').count(),
        'available_books': Book.objects.filter(available_copies__gt=0).count(),
    }
    
    # Libros más prestados
    popular_books = Book.objects.annotate(
        loan_count=Count('loan')
    ).order_by('-loan_count')[:10]
    
    # Estadísticas de morosidad
    overdue_loans = Loan.objects.filter(status='overdue')
    avg_overdue_days = 0
    if overdue_loans.exists():
        # Calcular días promedio de mora (esto es un ejemplo, necesitarías un campo para días de mora)
        avg_overdue_days = 5  # Esto debería calcularse basado en datos reales
    
    stats = {
        'avg_overdue_days': avg_overdue_days,
        'total_overdue_loans': overdue_loans.count(),
        'users_with_low_score': User.objects.filter(score__lt=2.0).count(),
    }
    
    # Distribución de puntuaciones
    total_users = User.objects.count()
    score_distribution = {
        'excellent': User.objects.filter(score__gte=4.0).count() / total_users * 100 if total_users > 0 else 0,
        'good': User.objects.filter(score__gte=3.0, score__lt=4.0).count() / total_users * 100 if total_users > 0 else 0,
        'fair': User.objects.filter(score__gte=2.0, score__lt=3.0).count() / total_users * 100 if total_users > 0 else 0,
        'poor': User.objects.filter(score__lt=2.0).count() / total_users * 100 if total_users > 0 else 0,
    }
    
    # Mejores usuarios
    top_users = User.objects.annotate(
        completed_loans=Count('loan', filter=Q(loan__status='returned')),
        review_count=Count('review')
    ).order_by('-score')[:10]
    
    # Categorías populares
    popular_categories = Category.objects.annotate(
        book_count=Count('books'),
        loan_count=Count('books__loan')
    ).order_by('-loan_count')[:8]
    
    context = {
        'kpis': kpis,
        'popular_books': popular_books,
        'stats': stats,
        'score_distribution': score_distribution,
        'top_users': top_users,
        'popular_categories': popular_categories,
    }
    
    return render(request, 'dashboard/dashboard.html', context)