from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


def is_librarian(user):
    """True si el usuario es bibliotecario o admin."""
    return (
        user.is_authenticated
        and getattr(user, 'role', None) in ('librarian', 'admin')
    )


def is_admin(user):
    return (
        user.is_authenticated
        and getattr(user, 'role', None) == 'admin'
    )


def is_member(user):
    """Miembros (incluye bibliotecarios y admin por conveniencia)."""
    return (
        user.is_authenticated
        and getattr(user, 'role', None) in ('member', 'librarian', 'admin')
    )


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Base para mixins de rol. Devuelve 403 en vez de redirigir a login
    cuando el usuario está autenticado pero no tiene permiso.
    """
    allowed_roles = ()
    raise_exception = True

    def test_func(self):
        user = self.request.user
        return (
            user.is_authenticated
            and getattr(user, 'role', None) in self.allowed_roles
        )


class LibrarianRequiredMixin(RoleRequiredMixin):
    allowed_roles = ('librarian', 'admin')


class AdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = ('admin',)


class MemberRequiredMixin(RoleRequiredMixin):
    allowed_roles = ('member', 'librarian', 'admin')