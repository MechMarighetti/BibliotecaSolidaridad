from datetime import timedelta

from django.db import models
from django.contrib.auth import get_user_model
from apps.books.models import Book
from django.utils import timezone
User = get_user_model()

class LoanQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status='active')


class Loan(models.Model):
    """Préstamo activo de un libro"""
    
    LOAN_TYPES = (
        ('normal', 'Normal (15 días)'),
        ('express', 'Express (3 días)'),
        ('summer', 'Verano (2 meses)'),
    )
    
    objects = LoanQuerySet.as_manager()
    
    LOAN_DURATION = {
        'normal': 15,
        'express': 3,
        'summer': 60,
    }
    
    # Relaciones
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    book = models.ForeignKey('books.Book', on_delete=models.CASCADE, related_name='loans')
    
    # Campos
    loan_type = models.CharField(max_length=10, choices=LOAN_TYPES, default='normal')
    loan_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=(
        ('active', 'Activo'),
        ('returned', 'Devuelto'),
        ('overdue', 'Vencido'),
        ('lost', 'Perdido'),
    ), default='active')
    
    renewal_count = models.IntegerField(default=0)
    max_renewals = models.IntegerField(default=2)
    
    class Meta:
        db_table = 'loans'
        verbose_name = 'Préstamo'
        verbose_name_plural = 'Préstamos'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', '-due_date']),
            models.Index(fields=['return_date']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.book} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Valida datos antes de guardar"""
        if self.due_date and self.loan_date:
            if self.due_date <= self.loan_date:
                raise ValueError("Fecha de vencimiento debe ser posterior a fecha de préstamo")
        
        # Auto-calcular due_date si no está definida
        if not self.due_date and self.loan_date:
            days = self.LOAN_DURATION.get(self.loan_type, 15)
            self.due_date = self.loan_date + timedelta(days=days)
        
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        """Verifica si el préstamo está vencido"""
        if self.status != 'active':
            return False
        return timezone.now().date() > self.due_date
    
    @property
    def days_remaining(self):
        """Días restantes para devolver"""
        if self.status != 'active':
            return 0
        return (self.due_date - timezone.now().date()).days
    
    def renew(self):
        """Renueva el préstamo por otros 15 días"""
        if self.renewal_count >= self.max_renewals:
            raise ValueError("Número máximo de renovaciones alcanzado")
        
        if self.is_overdue:
            raise ValueError("No se puede renovar un préstamo vencido")
        
        old_due_date = self.due_date
        self.due_date = self.due_date + timedelta(days=15)
        self.renewal_count += 1
        self.save()
        
        # Registrar renovación
        Renewal.objects.create(
            loan=self,
            previous_due_date=old_due_date,
            new_due_date=self.due_date
        )
        
        return self
    
    def mark_returned(self):
        """Marca el préstamo como devuelto"""
        self.return_date = timezone.now().date()
        self.status = 'returned'
        self.save()

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
    """Solicitud de préstamo de un usuario (NO duplicar campos)"""
    
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
        ('cancelled', 'Cancelado'),
    ]
    
    LOAN_TYPE_CHOICES = [
        ('normal', 'Normal (15 días)'),
        ('express', 'Express (3 días)'),
        ('summer', 'Verano (2 meses)'),
    ]
    
    # Relaciones
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loan_requests')
    book = models.ForeignKey('books.Book', on_delete=models.CASCADE)
    
    # Campos
    loan_type = models.CharField(
        max_length=10, 
        choices=LOAN_TYPE_CHOICES, 
        default='normal'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    
    # Auditoría
    request_date = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_loan_requests'
    )
    approved_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'loan_requests'
        verbose_name = 'Solicitud de Préstamo'
        verbose_name_plural = 'Solicitudes de Préstamo'
        ordering = ['-request_date']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', '-request_date']),
        ]
    
    def __str__(self):
        return f"Solicitud de {self.user} - {self.book} ({self.status})"
    
    def approve(self, approved_by):
        """Aprueba la solicitud y crea el préstamo"""
        if self.status != 'pending':
            raise ValueError("Solo se pueden aprobar solicitudes pendientes")
        
        # Validaciones
        if not self.user.is_active_member:
            raise ValueError("Usuario no es miembro activo")
        
        active_loans_count = Loan.objects.filter(
            user=self.user, 
            status='active'
        ).count()
        
        if active_loans_count >= self.user.get_loan_limit():
            raise ValueError("Usuario ha alcanzado su límite de préstamos")
        
        # Crear préstamo
        loan = Loan.objects.create(
            user=self.user,
            book=self.book,
            loan_type=self.loan_type,
            status='active'
        )
        
        # Actualizar solicitud
        self.status = 'approved'
        self.approved_by = approved_by
        self.approved_date = timezone.now()
        self.save()
        
        return loan
    
    def reject(self):
        """Rechaza la solicitud"""
        if self.status != 'pending':
            raise ValueError("Solo se pueden rechazar solicitudes pendientes")
        
        self.status = 'rejected'
        self.save()