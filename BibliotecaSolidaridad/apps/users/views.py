from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import User


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

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "dni",
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
        user.role = "reader"  # todos los nuevos usuarios son lectores por defecto
        user.score = 5.0
        if commit:
            user.save()
        return user


class RegisterView(CreateView):
    model = User
    form_class = RegisterForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('login')
