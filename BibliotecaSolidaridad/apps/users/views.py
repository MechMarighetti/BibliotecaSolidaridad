from django.contrib.auth.views import LoginView, LogoutView
from django.db.models.aggregates import Sum
from django.views.generic import CreateView, DetailView
from django.urls import reverse_lazy
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import AVATAR_CHOICES, User, UserProfile
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views import View
from django.templatetags.static import static
from apps.books.models import Book
from apps.loans.models import Loan

class CustomLoginView(LoginView):
    template_name = 'users/login.html'


class CustomLogoutView(LogoutView):
    template_name = 'users/logged_out.html'


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(label="Nombre", max_length=100)
    last_name = forms.CharField(label="Apellido", max_length=100)
    email = forms.EmailField(label="Correo electrónico", required=True)
    dni = forms.CharField(label="DNI", max_length=20)
    address = forms.CharField(label="Dirección", widget=forms.Textarea(attrs={"rows": 2}))
    phone = forms.CharField(label="Teléfono", max_length=20)
    profile_picture = forms.ChoiceField(
        label="Avatar",
        choices=AVATAR_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_profile_picture'})
        
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "dni",
            "profile_picture",
            "phone",
            "address",
            "password1",
            "password2",
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.dni = self.cleaned_data["dni"]
        user.address = self.cleaned_data["address"]
        user.phone = self.cleaned_data["phone"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.profile_picture = self.cleaned_data["profile_picture"]
        user.role = "reader"  # todos los nuevos usuarios son lectores por defecto
        user.score = 5.0
        if commit:
            user.save()
        return user


class RegisterView(CreateView):
    model = User
    form_class = RegisterForm
    template_name = "users/register.html"
    success_url = reverse_lazy("login")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # { "images/avatar1.png": "/static/images/avatar1.abc123.png", ... }
        ctx["avatar_urls"] = {value: static(value) for value, _ in AVATAR_CHOICES}
        ctx["default_avatar_url"] = static("images/Armibiblio-.png")
        return ctx

class ToggleFavoriteView(LoginRequiredMixin, View):
    def post(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        profile = get_object_or_404(UserProfile, user=request.user)

        if book in profile.favorite_books.all():
            profile.favorite_books.remove(book)
            messages.info(request, f'El libro "{book.title}" fue eliminado de tus favoritos.')
        else:
            profile.favorite_books.add(book)
            messages.success(request, f'El libro "{book.title}" fue agregado a tus favoritos.')

        return redirect(request.META.get('HTTP_REFERER', '/'))


class RemoveFavoriteView(LoginRequiredMixin, View):
    def post(self, request, book_id):
        profile = get_object_or_404(UserProfile, user=request.user)
        book = get_object_or_404(Book, id=book_id)

        if book in profile.favorite_books.all():
            profile.favorite_books.remove(book)
            messages.success(request, f'El libro "{book.title}" fue eliminado de tus favoritos.')
        else:
            messages.warning(request, 'Este libro no estaba en tus favoritos.')

        return redirect('profile')


class ProfileView(LoginRequiredMixin, DetailView):
    model = UserProfile
    template_name = 'users/profile.html'
    context_object_name = 'profile'

    def get_object(self):
        return get_object_or_404(UserProfile, user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = self.get_object()
        ctx['user_favorites'] = profile.favorite_books.all()
        ctx['active_loans'] = self.request.user.loans.filter(
            status='active'
        ).select_related('book')
        ctx['loan_history'] = self.request.user.loans.exclude(
            status='active'
        ).select_related('book')
        return ctx

# =========================================================
# Reglas de puntaje
# =========================================================
POINTS_ON_TIME = 5      # devolución a tiempo
POINTS_LATE = -10       # devolución con retraso
POINTS_LOST = -20       # libro perdido / no devuelto
POINTS_ACTIVE = 0       # en préstamo, todavía sin evaluar


def calculate_loan_points(loan) -> int:
    """
    Calcula los puntos de un préstamo según su estado y fechas.
    
    - Devuelto a tiempo → +5
    - Devuelto con retraso → -10
    - Perdido → -20
    - Activo → 0 (todavía no se evalúa)
    """
    # Ajustá estos valores a los choices reales de tu modelo Loan
    if loan.status == 'returned':
        # ¿Se devolvió después de la fecha límite?
        if loan.return_date and loan.due_date and loan.return_date > loan.due_date:
            return POINTS_LATE
        return POINTS_ON_TIME

    if loan.status == 'lost':
        return POINTS_LOST

    # status == 'active' u otros
    return POINTS_ACTIVE


# =========================================================
# Vista
# =========================================================
class CarnetView(LoginRequiredMixin, DetailView):
    """
    Carnet virtual del socio autenticado.
    Muestra datos personales, puntaje e historial de préstamos.
    """
    model = UserProfile
    template_name = 'users/carnet-virtual.html'
    context_object_name = 'profile'

    def get_object(self):
        return get_object_or_404(
            UserProfile.objects.select_related('user'),
            user=self.request.user,
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = self.object
        user = profile.user

        # ---------------------------------------------------------
        # Préstamos
        # ---------------------------------------------------------
        loans = list(
            Loan.objects
            .filter(user=user)
            .select_related('book')
            .prefetch_related('book__authors')
            .order_by('-loan_date')
        )

        # ---------------------------------------------------------
        # Calcular puntos por préstamo (en Python, no en SQL)
        # ---------------------------------------------------------
        total_points = 0
        for loan in loans:
            loan.points = calculate_loan_points(loan)
            total_points += loan.points

        # ---------------------------------------------------------
        # Separar activos de históricos
        # ---------------------------------------------------------
        active_loans = [l for l in loans if l.status == 'active']
        past_loans = [l for l in loans if l.status != 'active']

        ctx.update({
            'user': user,
            'loans': loans,
            'active_loans': active_loans,
            'past_loans': past_loans,
            'total_points': total_points,
            'loans_count': len(loans),
            'active_loans_count': len(active_loans),
        })
        return ctx
    
    