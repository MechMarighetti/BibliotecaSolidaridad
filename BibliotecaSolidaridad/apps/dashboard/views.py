import logging

from django.views import View
from django.views.generic import TemplateView
from django.shortcuts import render
from django.db.models import Count, Q
from django.core.cache import cache
from django.utils import timezone

from apps.users.mixin import LibrarianRequiredMixin, is_librarian
from apps.books.models import Book, Category, Review, Author
from apps.loans.models import Loan
from apps.users.models import User

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutos


class LibrarianDashboardView(LibrarianRequiredMixin, TemplateView):
    """
    Dashboard principal para bibliotecarios y admins.
    Reemplaza a las dos vistas duplicadas anteriores.
    """
    template_name = 'dashboard/dashboard.html'

    # ------------------------- KPIs -------------------------

    def get_kpis(self):
        cache_key = 'dashboard_kpis'
        kpis = cache.get(cache_key)
        if kpis is not None:
            return kpis

        today = timezone.now().date()
        kpis = {
            'active_loans': Loan.objects.filter(status='active').count(),
            'active_members': User.objects.filter(is_active=True).count(),
            'overdue_loans': Loan.objects.filter(
                status='active',
                due_date__lt=today
            ).count(),
            'available_books': Book.objects.filter(stock__gt=0).count(),
            'total_books': Book.objects.count(),
            'total_authors': Author.objects.count(),
            'total_categories': Category.objects.count(),
            'total_reviews': Review.objects.count(),
        }
        cache.set(cache_key, kpis, CACHE_TTL)
        return kpis

    # ------------------------- Listados -------------------------

    def get_popular_books(self):
        """
        Top libros por préstamos.
        Devolvemos instancias (no values) para poder mostrar autores
        en el template sin queries extra gracias a prefetch_related.
        """
        cache_key = 'dashboard_popular_books'
        cached_ids = cache.get(cache_key)

        if cached_ids is None:
            qs = (
                Book.objects
                .annotate(
                    loan_count=Count(
                        'loans',
                        filter=Q(loans__status__in=['active', 'returned'])
                    )
                )
                .filter(loan_count__gt=0)
                .order_by('-loan_count')[:10]
            )
            cached_ids = list(qs.values_list('id', flat=True))
            cache.set(cache_key, cached_ids, CACHE_TTL)

        if not cached_ids:
            return Book.objects.none()

        # Recuperamos instancias preservando el orden de popularidad
        books = (
            Book.objects
            .filter(id__in=cached_ids)
            .prefetch_related('authors')
        )
        order = {pk: idx for idx, pk in enumerate(cached_ids)}
        return sorted(books, key=lambda b: order.get(b.id, 999))

    def get_recent_books(self):
        return Book.objects.order_by('-created_at')[:5]

    def get_featured_authors(self):
        return Author.featured(limit=5)

    # ------------------------- Estadísticas -------------------------

    def get_overdue_stats(self):
        today = timezone.now().date()
        overdue_loans = (
            Loan.objects
            .filter(status='active', due_date__lt=today)
            .select_related('user', 'book')
        )

        total = overdue_loans.count()
        if not total:
            return {
                'total_overdue': 0,
                'avg_overdue_days': 0,
                'users_with_overdue': 0,
            }

        overdue_days = [
            (today - loan.due_date).days
            for loan in overdue_loans.only('due_date')
        ]
        avg_days = sum(overdue_days) / len(overdue_days) if overdue_days else 0

        return {
            'total_overdue': total,
            'avg_overdue_days': round(avg_days, 1),
            'users_with_overdue': overdue_loans.values('user').distinct().count(),
        }

    def get_score_distribution(self):
        total_users = User.objects.count()
        if not total_users:
            return {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0}

        dist = User.objects.aggregate(
            excellent=Count('id', filter=Q(score__gte=4.0)),
            good=Count('id', filter=Q(score__gte=3.0, score__lt=4.0)),
            fair=Count('id', filter=Q(score__gte=2.0, score__lt=3.0)),
            poor=Count('id', filter=Q(score__lt=2.0)),
        )
        return {
            k: round((v or 0) / total_users * 100, 1)
            for k, v in dist.items()
        }

    # ------------------------- Rankings -------------------------

    def get_top_users(self):
        return (
            User.objects
            .annotate(
                completed_loans=Count(
                    'loans', filter=Q(loans__status='returned')
                ),
                active_loans=Count(
                    'loans', filter=Q(loans__status='active')
                ),
            )
            .order_by('-score')[:10]
            .values(
                'id', 'username', 'score',
                'completed_loans', 'active_loans'
            )
        )

    def get_popular_categories(self):
        return (
            Category.objects
            .annotate(
                book_count=Count('libros', distinct=True),
                total_loans=Count(
                    'libros__loans',
                    filter=Q(libros__loans__status__in=['active', 'returned']),
                    distinct=True,
                ),
            )
            .order_by('-total_loans')[:8]
            .values('id', 'name', 'book_count', 'total_loans')
        )

    # ------------------------- Contexto -------------------------

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Cada bloque por separado para que un fallo puntual no rompa todo
        try:
            context['kpis'] = self.get_kpis()
        except Exception as e:
            logger.error(f"Error en KPIs del dashboard: {e}", exc_info=True)
            context['kpis'] = {}

        try:
            context['popular_books'] = self.get_popular_books()
        except Exception as e:
            logger.error(f"Error en popular_books: {e}", exc_info=True)
            context['popular_books'] = []

        try:
            context['stats'] = self.get_overdue_stats()
        except Exception as e:
            logger.error(f"Error en overdue_stats: {e}", exc_info=True)
            context['stats'] = {}

        try:
            context['score_distribution'] = self.get_score_distribution()
        except Exception as e:
            logger.error(f"Error en score_distribution: {e}", exc_info=True)
            context['score_distribution'] = {}

        try:
            context['top_users'] = self.get_top_users()
        except Exception as e:
            logger.error(f"Error en top_users: {e}", exc_info=True)
            context['top_users'] = []

        try:
            context['popular_categories'] = self.get_popular_categories()
        except Exception as e:
            logger.error(f"Error en popular_categories: {e}", exc_info=True)
            context['popular_categories'] = []

        context['recent_books'] = self.get_recent_books()
        context['featured_authors'] = self.get_featured_authors()

        return context