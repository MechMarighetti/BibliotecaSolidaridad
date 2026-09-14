from django.contrib.auth.views import LoginView, LogoutView
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

