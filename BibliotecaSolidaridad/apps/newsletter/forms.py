from django import forms
from .models import NewsletterSubscriber

class NewsletterSubscriptionForm(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'tu.email@ejemplo.com'
        }),
        label="Email"
    )
    
    class Meta:
        model = NewsletterSubscriber
        fields = ['email']
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if NewsletterSubscriber.objects.filter(email=email, is_active=True).exists():
            raise forms.ValidationError("Este email ya está suscrito a nuestro newsletter.")
        return email