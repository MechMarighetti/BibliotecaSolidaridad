from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.books.models import Book, BookStock
from .availability import available_books_queryset, available_copy_count
from .models import Loan, LoanRequest


User = get_user_model()


class LoanRequestFlowTests(TestCase):
    def make_user(self, username, role='reader', dni='12345678'):
        return User.objects.create_user(
            username=username,
            password='test-password',
            role=role,
            dni=dni,
            address='Biblioteca 1',
            phone='11111111',
        )

    def make_book(self, title='Libro de prueba', stock=1, available=True):
        return Book.objects.create(
            title=title,
            stock=stock,
            available=available,
        )

    def test_reader_and_librarian_can_request_a_book_with_stock(self):
        book = self.make_book()

        for index, role in enumerate(('reader', 'librarian'), start=1):
            user = self.make_user(
                f'user-{role}',
                role=role,
                dni=f'1234567{index}',
            )
            self.client.force_login(user)
            response = self.client.post(
                reverse('submit_loan_request'),
                {'book': book.pk, 'loan_type': 'normal'},
            )

            self.assertRedirects(response, reverse('user_loans'))
            self.assertTrue(
                LoanRequest.objects.filter(
                    user=user,
                    book=book,
                    status='pending',
                ).exists()
            )

    def test_book_detail_shows_confirmation_modal_for_available_copy(self):
        user = self.make_user('reader')
        book = self.make_book(stock=1)
        self.client.force_login(user)

        response = self.client.get(reverse('book_detail', args=[book.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'loanConfirmationModal')
        self.assertContains(response, 'Confirmar solicitud')
        self.assertContains(response, 'name="book"')

    def test_unavailable_book_is_not_requestable(self):
        user = self.make_user('reader')
        book = self.make_book(stock=0)
        self.client.force_login(user)

        response = self.client.get(reverse('book_detail', args=[book.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No hay copias disponibles')
        self.assertNotContains(response, 'loanConfirmationModal')

        response = self.client.post(
            reverse('submit_loan_request'),
            {'book': book.pk, 'loan_type': 'normal'},
        )
        self.assertRedirects(response, reverse('book_detail', args=[book.pk]))
        self.assertFalse(LoanRequest.objects.filter(book=book).exists())

    def test_other_roles_cannot_submit_loan_requests(self):
        admin = self.make_user('admin-user', role='admin')
        book = self.make_book(stock=1)
        self.client.force_login(admin)

        response = self.client.post(
            reverse('submit_loan_request'),
            {'book': book.pk, 'loan_type': 'normal'},
        )

        self.assertRedirects(response, reverse('book_search'))
        self.assertFalse(LoanRequest.objects.filter(book=book).exists())

    def test_approval_and_return_track_each_physical_copy(self):
        reader = self.make_user('reader')
        librarian = self.make_user('librarian', role='librarian', dni='22345678')
        book = self.make_book(stock=2)
        copies = [
            BookStock.objects.create(book=book, physical_id=f'COPY-{index}')
            for index in range(2)
        ]
        loan_request = LoanRequest.objects.create(user=reader, book=book)

        loan = loan_request.approve(approved_by=librarian)

        self.assertIn(loan.stock_item, copies)
        self.assertEqual(loan.stock_item.status, 'borrowed')
        self.assertEqual(available_copy_count(book), 1)
        self.assertTrue(book.available)
        self.assertEqual(book.stock, 2)

        self.client.force_login(librarian)
        response = self.client.post(
            reverse('return_book', args=[loan.pk]),
        )

        self.assertRedirects(response, reverse('manage_loans'))
        loan.refresh_from_db()
        loan.stock_item.refresh_from_db()
        self.assertEqual(loan.status, 'returned')
        self.assertEqual(loan.stock_item.status, 'available')
        self.assertEqual(available_copy_count(book), 2)

    def test_aggregate_stock_is_not_lost_after_first_approval(self):
        librarian = self.make_user('librarian', role='librarian')
        readers = [
            self.make_user('reader-one', dni='22345678'),
            self.make_user('reader-two', dni='32345678'),
        ]
        book = self.make_book(stock=2)
        requests = [
            LoanRequest.objects.create(user=reader, book=book)
            for reader in readers
        ]

        for loan_request in requests:
            loan_request.approve(approved_by=librarian)

        self.assertEqual(Loan.objects.filter(book=book, status='active').count(), 2)
        self.assertEqual(available_copy_count(book), 0)
        self.assertFalse(available_books_queryset().filter(pk=book.pk).exists())
        self.assertTrue(book.available)

    def test_physical_inventory_and_catalog_switch_both_limit_requests(self):
        user = self.make_user('reader')
        book = self.make_book(stock=3)
        copy = BookStock.objects.create(book=book, physical_id='ONLY-COPY')
        self.client.force_login(user)

        self.assertEqual(available_copy_count(book), 1)
        response = self.client.post(
            reverse('submit_loan_request'),
            {'book': book.pk, 'loan_type': 'normal'},
        )
        self.assertRedirects(response, reverse('user_loans'))
        loan_request = LoanRequest.objects.get(book=book, user=user)
        librarian = self.make_user('librarian', role='librarian', dni='22345678')
        loan_request.approve(approved_by=librarian)
        copy.refresh_from_db()
        self.assertEqual(copy.status, 'borrowed')
        self.assertEqual(available_copy_count(book), 0)

        book.available = False
        book.save(update_fields=['available'])
        self.assertFalse(available_books_queryset().filter(pk=book.pk).exists())
