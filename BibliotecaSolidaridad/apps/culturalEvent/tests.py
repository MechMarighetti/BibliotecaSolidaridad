from datetime import date, timedelta
from io import BytesIO
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from .forms import CulturalEventForm


class CulturalEventCoverTests(TestCase):
    def event_data(self):
        return {
            'title': 'Taller de lectura',
            'description': 'Actividad para la comunidad.',
            'event_type': 'taller',
            'date': date.today() + timedelta(days=1),
            'start_time': '10:00',
            'end_time': '',
            'location': 'Sala principal',
            'capacity': '',
            'status': 'programado',
        }

    def test_cover_is_optional(self):
        form = CulturalEventForm(data=self.event_data())

        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.cleaned_data['cover_image'])

    def test_uploaded_cover_is_shown_in_event_views_and_home(self):
        image_bytes = BytesIO()
        Image.new('RGB', (1, 1), color='blue').save(image_bytes, format='PNG')
        cover = SimpleUploadedFile(
            'portada.png',
            image_bytes.getvalue(),
            content_type='image/png',
        )
        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                form = CulturalEventForm(
                    data=self.event_data(),
                    files={'cover_image': cover},
                )
                self.assertTrue(form.is_valid(), form.errors)
                event = form.save()
                cover_url = event.cover_image.url

                for url in (
                    reverse('event_list'),
                    reverse('event_detail', kwargs={'pk': event.pk}),
                    reverse('home'),
                ):
                    with self.subTest(url=url):
                        response = self.client.get(url)
                        self.assertEqual(response.status_code, 200)
                        self.assertContains(response, f'src="{cover_url}"')
