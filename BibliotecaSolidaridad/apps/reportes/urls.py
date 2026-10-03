from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('libros-prestados/', views.LoanReportView.as_view(), name='libros_prestados'),
    path('libros-prestados/export/csv/', views.export_loans_csv, name='export_loans_csv'),
    path('libros-prestados/export/pdf/', views.export_loans_pdf, name='export_loans_pdf'),
]
