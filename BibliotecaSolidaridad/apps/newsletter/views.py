from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from .forms import NewsletterSubscriptionForm
from .models import NewsletterSubscriber
from .services import NewsletterService
from django.utils import timezone
from django.template.loader import render_to_string

def subscribe_newsletter(request):
    if request.method == 'POST':
        form = NewsletterSubscriptionForm(request.POST)
        if form.is_valid():
            subscriber = form.save(commit=False)
            subscriber.save()
            
            # Enviar email de bienvenida
            if settings.EMAIL_HOST_USER:  # Solo si el email está configurado
                try:
                    subject = "¡Bienvenido a nuestro newsletter!"
                    html_content = render_to_string('newsletter/welcome.html', {
                        'site_url': settings.SITE_URL,
                        'unsubscribe_url': NewsletterService.get_unsubscribe_url(subscriber.email),
                        'current_year': timezone.now().year
                    })
                    text_content = "¡Bienvenido a nuestro newsletter!"
                    
                    NewsletterService.send_newsletter(
                        subject=subject,
                        html_content=html_content,
                        text_content=text_content,
                        recipient_list=[subscriber.email]
                    )
                except Exception as e:
                    # No romper el flujo si falla el email
                    print(f"Error enviando email de bienvenida: {e}")
            
            messages.success(request, "¡Te has suscrito exitosamente a nuestro newsletter!")
            return redirect('home')
    else:
        form = NewsletterSubscriptionForm()
    
    return render(request, 'newsletter/subscribe.html', {'form': form})

@require_POST
def unsubscribe_newsletter(request, token):
    subscriber = get_object_or_404(NewsletterSubscriber, token=token)
    subscriber.is_active = False
    subscriber.unsubscribed_at = timezone.now()
    subscriber.save()
    
    messages.info(request, "Te has desuscrito exitosamente de nuestro newsletter.")
    return redirect('home')

def unsubscribe_by_email(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            subscriber = NewsletterSubscriber.objects.get(email=email, is_active=True)
            subscriber.is_active = False
            subscriber.unsubscribed_at = timezone.now()
            subscriber.save()
            messages.info(request, "Te has desuscrito exitosamente.")
        except NewsletterSubscriber.DoesNotExist:
            messages.error(request, "No encontramos una suscripción activa con ese email.")
    
    return render(request, 'newsletter/unsubscribe.html')