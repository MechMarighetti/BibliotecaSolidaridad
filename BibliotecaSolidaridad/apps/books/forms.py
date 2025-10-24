from django import forms
from .models import Book, Category

class BookForm(forms.ModelForm):
    # Campos personalizados para manejar la conversión de datos
    authors_input = forms.CharField(
        label="Autores",
        help_text="Ingresa los autores separados por comas",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Gabriel García Márquez'
        })
    )
    
    isbn_input = forms.CharField(
        label="ISBN",
        required=False,
        help_text="Ingresa uno o más ISBN separados por comas",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 9788437604947, 9788497592378'
        })
    )
    
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False
    )

    class Meta:
        model = Book
        fields = [
            'title', 'authors_input', 'isbn_input', 'publish_date', 
            'number_of_pages', 'cover_url', 'categories', 'stock', 'available'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Título del libro'
            }),
            'publish_date': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Año de publicación'
            }),
            'number_of_pages': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'cover_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://ejemplo.com/portada.jpg'
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'value': '1'
            }),
            'available': forms.CheckboxInput(attrs={
                'class': 'form-check-input', 
            })
        }
        labels = {
            'publish_date': 'Año de Publicación',
            'number_of_pages': 'Número de Páginas',
            'cover_url': 'URL de Portada',
            'stock': 'Cantidad en Stock',
            'available': 'Disponible para Préstamo'
        }
        help_texts = {
            'stock': 'Número total de copias disponibles',
            'available': 'Si está marcado, el libro estará disponible para préstamo'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Si es una instancia existente, cargar datos en los campos personalizados
        if self.instance and self.instance.pk:
            # Convertir lista de autores a string
            if self.instance.authors:
                self.fields['authors_input'].initial = ', '.join(self.instance.authors)
            
            # Convertir lista de ISBN a string
            if self.instance.isbn:
                self.fields['isbn_input'].initial = ', '.join(self.instance.isbn)

    def clean_authors_input(self):
        """Convierte el string de autores en una lista"""
        authors_str = self.cleaned_data.get('authors_input', '')
        if not authors_str:
            raise forms.ValidationError("Este campo es obligatorio")
        
        # Dividir por comas y limpiar espacios
        authors_list = [author.strip() for author in authors_str.split(',') if author.strip()]
        
        if not authors_list:
            raise forms.ValidationError("Debe ingresar al menos un autor")
        
        return authors_list

    def clean_isbn_input(self):
        """Convierte el string de ISBN en una lista"""
        isbn_str = self.cleaned_data.get('isbn_input', '')
        if not isbn_str:
            return []
        
        # Dividir por comas y limpiar espacios
        isbn_list = [isbn.strip() for isbn in isbn_str.split(',') if isbn.strip()]
        return isbn_list

    def clean_stock(self):
        """Valida que el stock no sea negativo"""
        stock = self.cleaned_data.get('stock', 0)
        if stock < 0:
            raise forms.ValidationError("El stock no puede ser negativo")
        return stock

    def clean_number_of_pages(self):
        """Valida que el número de páginas sea positivo"""
        pages = self.cleaned_data.get('number_of_pages')
        if pages and pages < 1:
            raise forms.ValidationError("El número de páginas debe ser mayor a 0")
        return pages

    def save(self, commit=True):
        """Guarda el libro con los datos convertidos"""
        # Obtener la instancia sin guardar aún
        instance = super().save(commit=False)
        
        # Asignar los datos convertidos a los campos JSON
        instance.authors = self.cleaned_data['authors_input']
        instance.isbn = self.cleaned_data['isbn_input']
        
        if commit:
            instance.save()
            self.save_m2m()  # Para guardar las relaciones ManyToMany (categorías)
        
        return instance