import re
from django.core.exceptions import ValidationError

def validate_isbn(value):
    """Valida formato ISBN-10 o ISBN-13"""
    # Eliminar guiones y espacios
    clean_isbn = value.replace('-', '').replace(' ', '')
    
    # ISBN-13: 13 dígitos
    if len(clean_isbn) == 13 and clean_isbn.isdigit():
        return
    
    # ISBN-10: 10 caracteres (9 dígitos + check digit que puede ser X)
    if len(clean_isbn) == 10 and clean_isbn[:-1].isdigit() and clean_isbn[-1] in '0123456789X':
        return
    
    raise ValidationError("ISBN debe ser válido (ISBN-10 o ISBN-13)")