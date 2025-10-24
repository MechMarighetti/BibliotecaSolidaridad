from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from newsletter.models import NewsletterSubscriber, NewsletterCampaign
from newsletter.services import NewsletterService

class Command(BaseCommand):
    help = 'Envía newsletters a todos los suscriptores activos'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--campaign-id',
            type=int,
            help='ID de la campaña a enviar',
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Enviar solo a emails de prueba',
        )
    
    def handle(self, *args, **options):
        campaign_id = options.get('campaign_id')
        test_mode = options.get('test')
        
        if campaign_id:
            campaign = NewsletterCampaign.objects.get(id=campaign_id)
            self.send_campaign(campaign, test_mode)
        else:
            # Enviar campañas programadas
            campaigns = NewsletterCampaign.objects.filter(
                is_sent=False,
                scheduled_for__lte=timezone.now()
            )
            for campaign in campaigns:
                self.send_campaign(campaign, test_mode)
    
    def send_campaign(self, campaign, test_mode=False):
        self.stdout.write(f"Enviando campaña: {campaign.title}")
        
        if test_mode:
            recipients = ['tu.email@gmail.com']  # Email de prueba
        else:
            subscribers = NewsletterSubscriber.objects.filter(is_active=True)
            recipients = [sub.email for sub in subscribers]
        
        success_count, failed_count = NewsletterService.send_newsletter(
            subject=campaign.subject,
            html_content=campaign.html_content,
            text_content=campaign.text_content,
            recipient_list=recipients
        )
        
        if not test_mode:
            campaign.is_sent = True
            campaign.sent_at = timezone.now()
            campaign.total_recipients = len(recipients)
            campaign.total_sent = success_count
            campaign.save()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Campaña enviada: {success_count} exitosos, {failed_count} fallidos'
            )
        )