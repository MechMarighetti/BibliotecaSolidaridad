from django import forms
from .models import CulturalEvent



class CulturalEventForm(forms.ModelForm):

    class Meta:
        model = CulturalEvent
        fields = [
            'title',
            'description',
            'event_type',
            'date',
            'start_time',
            'end_time',
            'location',
            'capacity',
            'status',
        ]

        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del evento'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descripción del evento'
            }),

            'event_type': forms.Select(attrs={
                'class': 'form-control'
            }),

            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),

            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),

            'end_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),

            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Sala de lectura'
            }),

            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'Opcional'
            }),

            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
        }