from django.shortcuts import render
from django.views.generic import ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Count, Avg
from django.utils import timezone
from django.template.loader import render_to_string
import csv
from io import BytesIO

from apps.loans.models import Loan
from apps.books.models import Book
from apps.users.models import User
from apps.users.mixin import LibrarianRequiredMixin
from .forms import LoanReportForm
from django.db import models


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = '/users/login/'

    def test_func(self):
        user = self.request.user
        # Prefer project's role field, then groups, then is_staff/superuser
        try:
            if hasattr(user, 'role'):
                return user.role in ('admin', 'administrator', 'administrador')
        except Exception:
            pass
        if user.groups.filter(name__iexact='Administrador').exists():
            return True
        return user.is_staff or user.is_superuser

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        return HttpResponse(status=403)


class LoanReportView(LibrarianRequiredMixin, ListView):
    template_name = 'reportes/libros_prestados.html'
    context_object_name = 'loans'
    paginate_by = 25

    def get(self, request, *args, **kwargs):
        form = LoanReportForm(request.GET or None)
        qs = Loan.objects.select_related('user', 'book').all()

        if form.is_valid():
            cd = form.cleaned_data
            if cd.get('fecha_desde'):
                qs = qs.filter(loan_date__gte=cd['fecha_desde'])
            if cd.get('fecha_hasta'):
                qs = qs.filter(loan_date__lte=cd['fecha_hasta'])
            estado = cd.get('estado')
            if estado and estado != 'all':
                qs = qs.filter(status=estado)
            if cd.get('libro'):
                qs = qs.filter(book=cd['libro'])
            if cd.get('usuario'):
                qs = qs.filter(user=cd['usuario'])
            if cd.get('categoria'):
                qs = qs.filter(book__categories=cd['categoria'])
            if cd.get('solo_vencidos'):
                qs = qs.filter(status='overdue')

        # annotate days of delay
        today = timezone.now().date()
        loans = qs.order_by('-loan_date')

        # Aggregates
        total = loans.count()
        activos = loans.filter(status='active').count()
        devueltos = loans.filter(status='returned').count()
        vencidos = loans.filter(status='overdue').count()

        # promedio días de préstamo: calcular usando diferencias y promedio en días
        avg_days = None
        if total:
            # compute average in python to avoid complex DB-specific timedelta averaging
            total_days = 0
            count_for_avg = 0
            for l in loans:
                if l.return_date:
                    days = (l.return_date - l.loan_date).days
                else:
                    days = (today - l.loan_date).days
                total_days += days
                count_for_avg += 1
            avg_days = round(total_days / count_for_avg, 2) if count_for_avg else None

        top_books = Book.objects.filter(loans__in=loans).annotate(count=Count('loans')).order_by('-count')[:5]
        top_users = User.objects.filter(loans__in=loans).annotate(count=Count('loans')).order_by('-count')[:5]

        paginator = Paginator(loans, self.paginate_by)
        page = request.GET.get('page')
        page_obj = paginator.get_page(page)
        context = {
            'form': form,
            'loans': page_obj,
            'page_obj': page_obj,
            'total': total,
            'activos': activos,
            'devueltos': devueltos,
            'vencidos': vencidos,
            'avg_days': avg_days,
            'top_books': top_books,
            'top_users': top_users,
        }
        # compute days_delay for visible loans to simplify template logic
        for l in page_obj.object_list:
            try:
                if l.return_date:
                    l.days_delay = max(0, (l.return_date - l.due_date).days)
                else:
                    l.days_delay = max(0, (today - l.due_date).days)
            except Exception:
                l.days_delay = 0
        context = {
            'form': form,
            'loans': page_obj,
            'page_obj': page_obj,
            'total': total,
            'activos': activos,
            'devueltos': devueltos,
            'vencidos': vencidos,
            'avg_days': avg_days,
            'top_books': top_books,
            'top_users': top_users,
            'today': today,
        }
        return render(request, self.template_name, context)


def export_loans_csv(request):
    # Reuse same access control
    user = request.user
    if not user.is_authenticated:
        return HttpResponseRedirect('/users/login/?next=' + request.path)
    if not (hasattr(user, 'role') and user.role in ('admin', 'administrator', 'administrador')) and not user.is_staff and not user.is_superuser and not user.groups.filter(name__iexact='Administrador').exists():
        return HttpResponse(status=403)

    form = LoanReportForm(request.GET or None)
    qs = Loan.objects.select_related('user', 'book').all()
    if form.is_valid():
        cd = form.cleaned_data
        if cd.get('fecha_desde'):
            qs = qs.filter(loan_date__gte=cd['fecha_desde'])
        if cd.get('fecha_hasta'):
            qs = qs.filter(loan_date__lte=cd['fecha_hasta'])
        estado = cd.get('estado')
        if estado and estado != 'all':
            qs = qs.filter(status=estado)
        if cd.get('libro'):
            qs = qs.filter(book=cd['libro'])
        if cd.get('usuario'):
            qs = qs.filter(user=cd['usuario'])
        if cd.get('categoria'):
            qs = qs.filter(book__categories=cd['categoria'])
        if cd.get('solo_vencidos'):
            qs = qs.filter(status='overdue')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="loans_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Libro', 'Usuario', 'Fecha préstamo', 'Fecha esperada', 'Fecha devolución', 'Estado', 'Días de retraso'])
    today = timezone.now().date()
    for l in qs.order_by('-loan_date'):
        if l.return_date:
            days_delay = max(0, (l.return_date - l.due_date).days)
        else:
            days_delay = max(0, (today - l.due_date).days)
        writer.writerow([l.id, l.book.title, str(l.user), l.loan_date, l.due_date, l.return_date or '', l.status, days_delay])

    return response


def export_loans_pdf(request):
    # Try to use WeasyPrint if installed, otherwise fallback to simple HTML response
    user = request.user
    if not user.is_authenticated:
        return HttpResponseRedirect('/users/login/?next=' + request.path)
    if not (hasattr(user, 'role') and user.role in ('admin', 'administrator', 'administrador')) and not user.is_staff and not user.is_superuser and not user.groups.filter(name__iexact='Administrador').exists():
        return HttpResponse(status=403)

    form = LoanReportForm(request.GET or None)
    qs = Loan.objects.select_related('user', 'book').all()
    if form.is_valid():
        cd = form.cleaned_data
        if cd.get('fecha_desde'):
            qs = qs.filter(loan_date__gte=cd['fecha_desde'])
        if cd.get('fecha_hasta'):
            qs = qs.filter(loan_date__lte=cd['fecha_hasta'])
        estado = cd.get('estado')
        if estado and estado != 'all':
            qs = qs.filter(status=estado)
        if cd.get('libro'):
            qs = qs.filter(book=cd['libro'])
        if cd.get('usuario'):
            qs = qs.filter(user=cd['usuario'])
        if cd.get('categoria'):
            qs = qs.filter(book__categories=cd['categoria'])
        if cd.get('solo_vencidos'):
            qs = qs.filter(status='overdue')

    context = {'loans': qs.order_by('-loan_date')}
    html_string = render_to_string('reportes/libros_prestados_pdf.html', context)

    try:
        from weasyprint import HTML
        pdf_file = HTML(string=html_string).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="loans_report.pdf"'
        return response
    except Exception:
        # If WeasyPrint not available, return HTML view instead
        return HttpResponse(html_string)
