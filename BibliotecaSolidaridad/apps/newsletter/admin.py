from django.contrib import admin
from .models import NewsletterCampaign, NewsletterSubscriber, NewsletterTemplate

admin.register(NewsletterTemplate)
admin.register(NewsletterSubscriber)
admin.register(NewsletterCampaign)