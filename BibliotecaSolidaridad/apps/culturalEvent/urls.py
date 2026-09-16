from django.urls import path
from .views import (CulturalEventListView,
    CulturalEventCreateView,
    CulturalEventUpdateView,
    CulturalEventDeleteView,
)
urlpatterns = [
    path('agenda-cultural/', CulturalEventListView.as_view(), name='cultural_event_list'),
    path('agenda-cultural/nuevo/', CulturalEventCreateView.as_view(), name='cultural_event_create'),
    path('agenda-cultural/<int:pk>/editar/', CulturalEventUpdateView.as_view(), name='cultural_event_update'),
    path('agenda-cultural/<int:pk>/eliminar/', CulturalEventDeleteView.as_view(),name='cultural_event_delete'),
]