import re
from django.core.exceptions import ValidationError

def validate_dni(value):
    """Valida formato DNI argentino (8-10 dígitos con guión opcional)"""
    if not re.match(r'^\d{7,8}(?:-\d)?$', value):
        raise ValidationError("DNI debe ser válido (Ej: 12345678 o 12.345.678)")