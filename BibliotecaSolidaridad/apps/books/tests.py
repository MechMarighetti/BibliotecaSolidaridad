from django.test import TestCase
from django.urls import reverse

from .forms import BookForm


class BookCoverTests(TestCase):
    def test_selected_cover_is_saved_and_shown_on_book_detail(self):
        cover_url = 'https://covers.openlibrary.org/b/id/12345-M.jpg'
        form = BookForm(data={
            'title': 'Libro de prueba',
            'authors_input': 'Autora de prueba',
            'isbn_input': '',
            'cover_url': cover_url,
            'stock': '1',
            'available': 'on',
        })

        self.assertTrue(form.is_valid(), form.errors)
        book = form.save()

        self.assertEqual(book.cover_url, cover_url)
        response = self.client.get(
            reverse('book_detail', kwargs={'pk': book.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'src="{cover_url}"')
