from django import forms
from django.utils import timezone
from apps.books.models import Book, Category
from apps.users.models import User


STATE_CHOICES = [
    ('all', 'Todos'),
    ('active', 'Prestado'),
    ('returned', 'Devuelto'),
    ('overdue', 'Vencido'),
]


class LoanReportForm(forms.Form):
    fecha_desde = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    fecha_hasta = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    estado = forms.ChoiceField(choices=STATE_CHOICES, required=False, initial='all')
    libro = forms.ModelChoiceField(queryset=Book.objects.all(), required=False)
    usuario = forms.ModelChoiceField(queryset=User.objects.all(), required=False)
    categoria = forms.ModelChoiceField(queryset=Category.objects.all(), required=False)
    solo_vencidos = forms.BooleanField(required=False)

    def clean(self):
        cleaned = super().clean()
        fecha_desde = cleaned.get('fecha_desde')
        fecha_hasta = cleaned.get('fecha_hasta')
        if fecha_desde and fecha_hasta:
            if fecha_desde > fecha_hasta:
                raise forms.ValidationError('La fecha desde debe ser anterior o igual a fecha hasta')
        # set defaults
        if not fecha_hasta:
            cleaned['fecha_hasta'] = timezone.now().date()
        return cleaned
