from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()

class DashboardMetric(models.Model):
    name = models.CharField(max_length=100)
    value = models.IntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}: {self.value}"
    class Meta:
        db_table = 'dashboard_metrics'
        verbose_name = 'Métrica del Tablero'
        verbose_name_plural = 'Métricas del Tablero'

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notificación para {self.user.username} - {'Leída' if self.read else 'No Leída'}"
    class Meta:
        db_table = 'notifications'
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
