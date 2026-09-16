from django.utils import timezone
from django.views.generic import TemplateView
from apps.culturalEvent.models import CulturalEvent
from apps.books.models import Book, Category, Author
from apps.loans.models import Loan
from apps.users.models import User
from django.db.models import Count, Sum, Avg, Max, Min, Q, F


class HomeView(TemplateView):
    """OPAC: catálogo público con libros, autores y eventos culturales."""

    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        # ---------------------------------------------------------
        # Libros
        # ---------------------------------------------------------
        recommended_books = (
            Book.objects
            .recommended(limit=12)
            .prefetch_related('authors', 'categories')
        )

        new_arrivals = (
            Book.objects
            .filter(stock__gt=0)
            .prefetch_related('authors')
            .order_by('-created_at')[:8]
        )

        # ---------------------------------------------------------
        # Autores destacados
        # ---------------------------------------------------------
        featured_authors = (
            Author.objects
            .annotate(books_count=Count('books'))
            .filter(books_count__gt=0)
            .order_by('-books_count')[:6]
        )

        # ---------------------------------------------------------
        # Eventos culturales
        # ---------------------------------------------------------
        upcoming_events = (
            CulturalEvent.objects
            .filter(date__gte=today)        # ⚠️ ajustá el nombre del campo
            .order_by('date')[:6]
        )
        featured_event = upcoming_events.first()   # el más próximo

        # ---------------------------------------------------------
        # Stats
        # ---------------------------------------------------------
        stats = {
            'total_books': Book.objects.total_available(),
            'active_members': User.objects.filter(is_active_member=True).count(),
            'active_loans': Loan.objects.active().count(),
            'categories': Category.objects.count(),
            'total_users': User.objects.count(),
            'events': CulturalEvent.objects.count(),
        }

        context.update({
            'recommended_books': recommended_books,
            'new_arrivals': new_arrivals,
            'featured_authors': featured_authors,
            'upcoming_events': upcoming_events,
            'featured_event': featured_event,
            'stats': stats,
            'today': today,
        })
        return context