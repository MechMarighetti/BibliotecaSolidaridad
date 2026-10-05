from django.urls import path
from .views import (CulturalEventDetailView, CulturalEventListView,
    CulturalEventCreateView,
    CulturalEventUpdateView,
    CulturalEventDeleteView,
)
urlpatterns = [
    path('', CulturalEventListView.as_view(), name='event_list'),
    path('nuevo/', CulturalEventCreateView.as_view(), name='event_create'),
    path('<int:pk>/editar/', CulturalEventUpdateView.as_view(), name='event_edit'),
    path('<int:pk>/eliminar/', CulturalEventDeleteView.as_view(),name='event_delete'),
    path('<int:pk>/', CulturalEventDetailView.as_view(), name='event_detail'),

]