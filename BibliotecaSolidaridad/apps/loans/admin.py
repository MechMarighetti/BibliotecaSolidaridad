from django.contrib import admin
from .models import Loan, Renewal, LoanRequest

admin.site.register(Loan)
admin.site.register(Renewal)
admin.site.register(LoanRequest)
