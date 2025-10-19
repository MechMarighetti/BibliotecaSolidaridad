from django.contrib import admin
from .models import DashboardMetric, Notification

admin.site.register(DashboardMetric)
admin.site.register(Notification)
