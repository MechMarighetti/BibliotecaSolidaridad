import logging
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Avg, Q, F
from django.core.cache import cache
from datetime import timedelta
from django.utils import timezone

from apps.books.models import Book, Category, Review
from apps.loans.models import Loan
from apps.users.models import User

logger = logging.getLogger(__name__)

def is_librarian(user):
    """Check if user is librarian or admin"""
    return user.is_authenticated and user.role in ['librarian', 'admin']


class DashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Dashboard mejorado con vistas caché y queries optimizadas"""
    
    template_name = 'dashboard/dashboard.html'
    
    def test_func(self):
        return is_librarian(self.request.user)
    
    def get_kpis(self):
        """Obtiene KPIs principales (caché 5 minutos)"""
        cache_key = 'dashboard_kpis'
        kpis = cache.get(cache_key)
        
        if kpis is None:
            kpis = {
                'active_loans': Loan.objects.filter(status='active').count(),
                'active_members': User.objects.filter(is_active_member=True).count(),
                'overdue_loans': Loan.objects.filter(
                    status='active',
                    due_date__lt=timezone.now().date()
                ).count(),
                'available_books': Book.objects.filter(stock__gt=0).count(),
                'total_books': Book.objects.count(),
            }
            cache.set(cache_key, kpis, 300)  # 5 minutos
        
        return kpis
    
    def get_popular_books(self):
   
        cache_key = 'dashboard_popular_books'
        popular = cache.get(cache_key)
    
        if popular is None:
        # ✅ Agregar prefetch_related para autores
            popular = Book.objects.annotate(
            loan_count=Count('loans', filter=Q(loans__status__in=['active', 'returned']))
        ).prefetch_related('authors').order_by('-loan_count')[:10].values(
            'id', 'title', 'loan_count', 'stock'
        )
        cache.set(cache_key, list(popular), 300)
    
        return popular
    
    def get_overdue_stats(self):
        """Estadísticas de mora calculadas desde DB"""
        overdue_loans = Loan.objects.filter(
            status='active',
            due_date__lt=timezone.now().date()
        ).select_related('user', 'book')
        
        if not overdue_loans.exists():
            return {
                'total_overdue': 0,
                'avg_overdue_days': 0,
                'users_with_overdue': 0,
            }
        
        # Calcular días de mora promedio
        today = timezone.now().date()
        overdue_days = [
            (today - loan.due_date).days 
            for loan in overdue_loans
        ]
        avg_days = sum(overdue_days) / len(overdue_days) if overdue_days else 0
        
        return {
            'total_overdue': overdue_loans.count(),
            'avg_overdue_days': round(avg_days, 1),
            'users_with_overdue': overdue_loans.values('user').distinct().count(),
        }
    
    def get_score_distribution(self):
        """Distribución de puntuaciones (evitar division por cero)"""
        total_users = User.objects.count()
        
        if total_users == 0:
            return {
                'excellent': 0,
                'good': 0,
                'fair': 0,
                'poor': 0,
            }
        
        # Una sola query con aggregation
        distribution = User.objects.aggregate(
            excellent=Count('id', filter=Q(score__gte=4.0)),
            good=Count('id', filter=Q(score__gte=3.0, score__lt=4.0)),
            fair=Count('id', filter=Q(score__gte=2.0, score__lt=3.0)),
            poor=Count('id', filter=Q(score__lt=2.0)),
        )
        
        return {
            'excellent': round(distribution['excellent'] / total_users * 100, 1),
            'good': round(distribution['good'] / total_users * 100, 1),
            'fair': round(distribution['fair'] / total_users * 100, 1),
            'poor': round(distribution['poor'] / total_users * 100, 1),
        }
    
    def get_top_users(self):
        """Top usuarios más activos (optimizado)"""
        return User.objects.annotate(
            completed_loans=Count('loans', filter=Q(loans__status='returned')),
            active_loans=Count('loans', filter=Q(loans__status='active')),
        ).select_related(
            # Agregar select_related según sea necesario
        ).order_by('-score')[:10].values(
            'id', 'username', 'score', 'completed_loans', 'active_loans'
        )
    
    def get_popular_categories(self):
        """Categorías más solicitadas (optimizado)"""
        return Category.objects.annotate(
            book_count=Count('libros'),
            total_loans=Count('libros__loans', filter=Q(libros__loans__status__in=['active', 'returned']))
        ).order_by('-total_loans')[:8].values(
            'id', 'name', 'book_count', 'total_loans'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            context['kpis'] = self.get_kpis()
            context['popular_books'] = self.get_popular_books()
            context['stats'] = self.get_overdue_stats()
            context['score_distribution'] = self.get_score_distribution()
            context['top_users'] = self.get_top_users()
            context['popular_categories'] = self.get_popular_categories()
            
        except Exception as e:
            logger.error(f"Error loading dashboard data: {str(e)}")
            context['error'] = "Error al cargar datos del dashboard"
        
        return context