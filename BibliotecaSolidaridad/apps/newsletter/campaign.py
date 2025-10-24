from django.utils import timezone
from datetime import timedelta
from newsletter.models import NewsletterCampaign

campaign = NewsletterCampaign.objects.create(
    title="Novedades de Primavera",
    subject="🌺 Nuevos libros y actividades de primavera",
    html_content="...",  # Tu contenido HTML
    text_content="...",  # Tu contenido en texto
    scheduled_for=timezone.now() + timedelta(days=1)
)