from django.views.generic import TemplateView
from apps.books.models import Book, Category
from apps.loans.models import Loan
from apps.users.models import User


class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recommended_books = Book.objects.recommended()
        stats = {
            'total_books': Book.objects.total_available(),
            'active_members': User.objects.filter(is_active_member=True).count(),
            'active_loans': Loan.objects.active().count(),
            'categories': Category.objects.count(),
        }
        featured_authors = Book.objects.featured_authors()
        authors_list = [
            {'name': a['authors'], 'books_count': a['books_count']}
            for a in featured_authors
        ]
        context.update({
            'recommended_books': recommended_books,
            'stats': stats,
            'featured_authors': authors_list,
        })
        return context
