
from django import forms
from .models import Book, Category, Author, ISBN


class BookForm(forms.ModelForm):


    authors_input = forms.CharField(
        label="Autores",
        help_text="Ingresá los autores separados por comas",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Gabriel García Márquez, Jorge Luis Borges'
        })
    )

    isbn_input = forms.CharField(
        label="ISBN",
        required=False,
        help_text="Ingresá uno o más ISBN separados por comas",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 9788437604947, 9788497592378'
        })
    )

    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False,
        label="Categorías",
    )

    class Meta:
        model = Book
        fields = [
            'title', 'publish_date', 'description', 'number_of_pages',
            'cover_url', 'categories', 'stock', 'available', 'authors', 'isbn', 'number_of_pages'
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
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Sinopsis o descripción del libro'
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
            }),
            'available': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
        labels = {
            'publish_date': 'Año de Publicación',
            'number_of_pages': 'Número de Páginas',
            'cover_url': 'URL de Portada',
            'stock': 'Cantidad en Stock',
            'available': 'Disponible para Préstamo',
        }
        help_texts = {
            'stock': 'Número total de copias disponibles',
            'available': 'Si está marcado, el libro estará disponible para préstamo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Cargar valores iniciales cuando editamos una instancia existente
        if self.instance and self.instance.pk:
            self.fields['authors_input'].initial = ', '.join(
                self.instance.authors.values_list('name', flat=True)
            )
            self.fields['isbn_input'].initial = ', '.join(
                self.instance.isbns.values_list('isbn', flat=True)
            )

    # -------------------- Validaciones --------------------

    def clean_authors_input(self):
        authors_str = self.cleaned_data.get('authors_input', '') or ''
        authors_list = [a.strip() for a in authors_str.split(',') if a.strip()]
        if not authors_list:
            raise forms.ValidationError("Debe ingresar al menos un autor.")
        return authors_list

    def clean_isbn_input(self):
        isbn_str = self.cleaned_data.get('isbn_input', '') or ''
        isbn_list = [i.strip() for i in isbn_str.split(',') if i.strip()]
        return isbn_list

    def clean_stock(self):
        stock = self.cleaned_data.get('stock', 0)
        if stock is None or stock < 0:
            raise forms.ValidationError("El stock no puede ser negativo.")
        return stock

    def clean_number_of_pages(self):
        pages = self.cleaned_data.get('number_of_pages')
        if pages is not None and pages < 1:
            raise forms.ValidationError("El número de páginas debe ser mayor a 0.")
        return pages

    # -------------------- Guardado --------------------

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()
            # Guarda M2M declarados como campos del ModelForm (categories)
            self.save_m2m()

            # Autores: crear si no existen y asignar M2M
            author_objs = []
            for name in self.cleaned_data['authors_input']:
                author, _ = Author.objects.get_or_create(name=name)
                author_objs.append(author)
            instance.authors.set(author_objs)

            # ISBNs: reemplazar los existentes por los del formulario
            isbn_list = self.cleaned_data.get('isbn_input', [])
            instance.isbns.all().delete()
            for isbn_str in isbn_list:
                ISBN.objects.get_or_create(
                    isbn=isbn_str,
                    defaults={'book': instance}
                )

        return instance