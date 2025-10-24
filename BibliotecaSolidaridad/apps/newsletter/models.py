from django.db import models
from django.utils import timezone

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    user = models.OneToOneField(
        'users.User', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='newsletter_subscription'
    )
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    token = models.CharField(max_length=100, unique=True)
    
    class Meta:
        db_table = 'newsletter_subscribers'
    
    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        if not self.token:
            import secrets
            self.token = secrets.token_urlsafe(50)
        super().save(*args, **kwargs)

class NewsletterCampaign(models.Model):
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=200)
    html_content = models.TextField()
    text_content = models.TextField(blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField(default=False)
    total_recipients = models.IntegerField(default=0)
    total_sent = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'newsletter_campaigns'
    
    def __str__(self):
        return self.title

class NewsletterTemplate(models.Model):
    name = models.CharField(max_length=100)
    html_content = models.TextField()
    text_content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'newsletter_templates'
    
    def __str__(self):
        return self.name