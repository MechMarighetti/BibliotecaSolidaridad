from django.db.models import Count, F, Q

from apps.books.models import Book, BookStock
from apps.loans.models import Loan


def available_copy_count(book):
    """Return lendable physical copies, falling back to the book's aggregate stock."""
    copies = BookStock.objects.filter(book=book)
    if copies.exists():
        available_copies = copies.filter(status='available').count()
        unassigned_active_loans = Loan.objects.filter(
            book=book,
            status='active',
            stock_item__isnull=True,
        ).count()
        return max(available_copies - unassigned_active_loans, 0)

    active_loans = Loan.objects.filter(book=book, status='active').count()
    return max(book.stock - active_loans, 0)


def available_books_queryset():
    """Books with at least one copy available to request."""
    return (
        Book.objects.filter(available=True)
        .annotate(
            active_loan_count=Count(
                'loans',
                filter=Q(loans__status='active'),
                distinct=True,
            ),
            available_stock_count=Count(
                'copies',
                filter=Q(copies__status='available'),
                distinct=True,
            ),
            unassigned_active_loan_count=Count(
                'loans',
                filter=Q(
                    loans__status='active',
                    loans__stock_item__isnull=True,
                ),
                distinct=True,
            ),
        )
        .filter(
            Q(copies__isnull=True, stock__gt=F('active_loan_count'))
            | Q(
                available_stock_count__gt=F('unassigned_active_loan_count')
            )
        )
        .distinct()
    )
