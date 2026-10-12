from django.test import TestCase
from django.urls import reverse
from unittest.mock import Mock, patch

from .forms import BookForm
from .models import Author, Book
from .services import OpenLibraryService


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


class AuthorOpenLibraryTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.author = Author.objects.create(name='Jorge Luis Borges')
        book = Book.objects.create(title='Ficciones')
        book.authors.add(self.author)

    @patch('apps.books.services.requests.get')
    def test_profile_resolves_author_and_photo_from_openlibrary(self, get):
        search_response = Mock()
        search_response.json.return_value = {
            'docs': [
                {'name': 'Jorge Luis Borges', 'key': '/authors/OL123A'},
            ],
        }
        search_response.raise_for_status.return_value = None
        details_response = Mock()
        details_response.json.return_value = {
            'key': '/authors/OL123A',
            'name': 'Jorge Luis Borges',
            'bio': {'value': 'Escritor argentino.'},
            'photos': [456],
            'birth_date': '24 de agosto de 1899',
        }
        details_response.raise_for_status.return_value = None
        get.side_effect = [search_response, details_response]

        profile = OpenLibraryService.get_author_profile(self.author.name)

        self.assertEqual(profile['openlibrary_id'], '/authors/OL123A')
        self.assertEqual(profile['bio'], 'Escritor argentino.')
        self.assertEqual(
            profile['photo_url'],
            'https://covers.openlibrary.org/a/id/456-M.jpg',
        )

    @patch(
        'apps.books.services.OpenLibraryService.get_author_profile',
        return_value={
            'photo_url': 'https://covers.openlibrary.org/a/id/456-M.jpg',
            'bio': 'Escritor argentino.',
        },
    )
    def test_author_list_and_detail_render_openlibrary_profile(self, get_profile):
        list_response = self.client.get(reverse('author_list'))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, self.author.name)
        self.assertContains(
            list_response,
            'https://covers.openlibrary.org/a/id/456-M.jpg',
        )

        detail_response = self.client.get(
            reverse('author_detail', kwargs={'pk': self.author.pk})
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, 'Escritor argentino.')
        self.assertContains(
            detail_response,
            'https://covers.openlibrary.org/a/id/456-M.jpg',
        )

    @patch(
        'apps.books.services.OpenLibraryService.get_author_profile',
        return_value={
            'photo_url': 'https://covers.openlibrary.org/a/id/456-M.jpg',
        },
    )
    def test_home_author_card_links_to_author_detail_and_shows_photo(self, get_profile):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Autores Destacados')
        self.assertContains(
            response,
            'https://covers.openlibrary.org/a/id/456-M.jpg',
        )
        self.assertContains(
            response,
            reverse('author_detail', kwargs={'pk': self.author.pk}),
        )
