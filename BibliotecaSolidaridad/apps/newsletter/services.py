from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class NewsletterService:
    @staticmethod
    def send_newsletter(subject, html_content, text_content, recipient_list, from_email=None):
        """
        Envía un newsletter a una lista de destinatarios
        """
        if not from_email:
            from_email = settings.DEFAULT_FROM_EMAIL
        
        success_count = 0
        failed_count = 0
        
        for recipient in recipient_list:
            try:
                # Personalizar el contenido para cada destinatario
                context = {
                    'recipient_email': recipient,
                    'unsubscribe_url': NewsletterService.get_unsubscribe_url(recipient),
                    'current_year': timezone.now().year,
                    'site_name': 'Biblioteca de la Solidaridad'
                }
                
                # Renderizar contenido personalizado
                personalized_html = NewsletterService.render_template(html_content, context)
                personalized_text = NewsletterService.render_template(text_content, context)
                
                # Crear email
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=personalized_text,
                    from_email=from_email,
                    to=[recipient],
                    reply_to=[settings.NEWSLETTER_CONFIG.get('REPLY_TO', from_email)]
                )
                email.attach_alternative(personalized_html, "text/html")
                
                # Enviar email
                email.send()
                success_count += 1
                logger.info(f"Newsletter enviado exitosamente a: {recipient}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Error enviando newsletter a {recipient}: {str(e)}")
        
        return success_count, failed_count
    
    @staticmethod
    def render_template(template_content, context):
        """
        Renderiza una plantilla de string con el contexto
        """
        from django.template import Template, Context
        template = Template(template_content)
        return template.render(Context(context))
    
    @staticmethod
    def get_unsubscribe_url(email):
        """
        Genera URL para desuscribirse
        """
        from newsletter.models import NewsletterSubscriber
        try:
            subscriber = NewsletterSubscriber.objects.get(email=email)
            return f"{settings.SITE_URL}/newsletter/unsubscribe/{subscriber.token}/"
        except NewsletterSubscriber.DoesNotExist:
            return f"{settings.SITE_URL}/newsletter/unsubscribe/"