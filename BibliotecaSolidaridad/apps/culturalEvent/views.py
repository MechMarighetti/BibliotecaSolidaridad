from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import CulturalEvent
from .forms import CulturalEventForm
from django.contrib import messages
from apps.users.mixin import LibrarianRequiredMixin


# ---------------------------------------------------------------------------
# Agenda Cultural
# ---------------------------------------------------------------------------

class CulturalEventListView(ListView):
    """Muestra la agenda cultural de la biblioteca."""
    model = CulturalEvent
    template_name = 'culturalEvent/agendaCultural.html'
    context_object_name = 'events'

    def get_queryset(self):
        return CulturalEvent.objects.all().order_by(
            'date',
            'start_time'
        )


class CulturalEventCreateView(LibrarianRequiredMixin, CreateView):
    """Permite al bibliotecario crear eventos culturales."""
    model = CulturalEvent
    form_class = CulturalEventForm
    template_name = 'culturalEvent/add_event.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)

        messages.success(
            self.request,
            f'El evento "{self.object.title}" fue creado correctamente.'
        )

        return response

    def get_success_url(self):
        return reverse_lazy('cultural_event_list')


class CulturalEventUpdateView(LibrarianRequiredMixin, UpdateView):
    """Permite al bibliotecario modificar un evento."""
    model = CulturalEvent
    form_class = CulturalEventForm
    template_name = 'books/cultural_event_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)

        messages.success(
            self.request,
            f'El evento "{self.object.title}" fue actualizado correctamente.'
        )

        return response

    def get_success_url(self):
        return reverse_lazy('cultural_event_list')


class CulturalEventDeleteView(LibrarianRequiredMixin, DeleteView):
    """Permite al bibliotecario eliminar un evento."""
    model = CulturalEvent
    template_name = 'books/cultural_event_confirm_delete.html'
    success_url = reverse_lazy('cultural_event_list')

    def form_valid(self, form):
        title = self.object.title
        response = super().form_valid(form)

        messages.success(
            self.request,
            f'El evento "{title}" fue eliminado correctamente.'
        )

        return response

# Create your views here.
