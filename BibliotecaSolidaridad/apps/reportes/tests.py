from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.loans.models import Loan
from apps.books.models import Book
from datetime import date, timedelta

User = get_user_model()


class LoanReportTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin', password='pass', role='admin', is_staff=True)
        self.user = User.objects.create_user(username='user', password='pass', role='reader')
        self.book = Book.objects.create(title='Test Book')
        # create loans
        Loan.objects.create(user=self.user, book=self.book, loan_date=date.today() - timedelta(days=10), due_date=date.today() - timedelta(days=1), status='overdue')
        Loan.objects.create(user=self.user, book=self.book, loan_date=date.today() - timedelta(days=5), due_date=date.today() + timedelta(days=5), status='active')

    def test_anonymous_redirects(self):
        url = reverse('reportes:libros_prestados')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)

    def test_non_admin_forbidden(self):
        self.client.login(username='user', password='pass')
        url = reverse('reportes:libros_prestados')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

    def test_admin_access(self):
        self.client.login(username='admin', password='pass')
        url = reverse('reportes:libros_prestados')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Test Book')

    def test_export_csv(self):
        self.client.login(username='admin', password='pass')
        url = reverse('reportes:export_loans_csv')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
