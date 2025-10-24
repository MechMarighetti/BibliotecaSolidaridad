from django.db import models
from django.contrib.auth import get_user_model
from apps.books.models import Book
User = get_user_model()

class LoanQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status='active')


class Loan(models.Model):
    LOAN_TYPES = (
        ('normal', 'Normal (15 días)'),
        ('express', 'Express (3 días)'),
        ('summer', 'Verano (2 meses)'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    loan_type = models.CharField(max_length=10, choices=LOAN_TYPES, default='normal')
    loan_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    renewed = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=(
        ('pending', 'Pendiente'),
        ('active', 'Activo'),
        ('returned', 'Devuelto'),
        ('overdue', 'Vencido'),
        ('lost', 'Perdido')
    ))

    objects = LoanQuerySet.as_manager()

    class Meta:
        db_table = 'loans'
        verbose_name = 'Préstamo'
        verbose_name_plural = 'Préstamos'

    def __str__(self):
        return f"{self.user} - {self.book}"

class Renewal(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    renewal_date = models.DateField(auto_now_add=True)
    previous_due_date = models.DateField()
    new_due_date = models.DateField()
    class Meta:
        db_table = 'renewals'
        verbose_name = 'Renovación'
        verbose_name_plural = 'Renovaciones'
    def __str__(self):
        return f"Renovación de {self.loan} el {self.renewal_date}"

class LoanRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
        ('returned', 'Devuelto'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    loan_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.book.title} ({self.status})"
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    loan_type = models.CharField(max_length=10, choices=Loan.LOAN_TYPES, default='normal')
    request_date = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_loans')
    approved_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'loan_requests'
        verbose_name = 'Solicitud de Préstamo'
        verbose_name_plural = 'Solicitudes de Préstamo'

    def __str__(self):
        return f"Solicitud de {self.user} - {self.book}"
