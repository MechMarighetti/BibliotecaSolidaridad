# 📚 Biblioteca Solidaridad - Sistema de Gestión de Biblioteca

Una aplicación web moderna desarrollada en Django para la gestión completa de una biblioteca, incluyendo catálogo de libros, préstamos, usuarios y integración con OpenLibrary.

## ✨ Características Principales

### 📖 Gestión de Libros
- **Catálogo completo** de libros con información detallada
- **Búsqueda avanzada** por título, autor, categorías
- **Integración con OpenLibrary API** para importar libros
- **Sistema de reseñas y calificaciones**
- **Marcar libros como favoritos**
- **Gestión de stock y disponibilidad**

### 👥 Gestión de Usuarios
- **Sistema de registro y autenticación**
- **Perfiles de usuario personalizados**
- **Historial de préstamos**
- **Sistema de miembros activos**

### 🔄 Sistema de Préstamos
- **Solicitudes de préstamo** con estados (pendiente, aprobado, rechazado)
- **Control de fechas** de préstamo y devolución
- **Seguimiento de préstamos activos**
- **Renovaciones y devoluciones**

### 📊 Dashboard Administrativo
- **Estadísticas en tiempo real**
- **Métricas de uso de la biblioteca**
- **Gestión de categorías y stock**
- **Reportes de actividad**

## 🛠️ Tecnologías Utilizadas

### Backend
- **Django 5.2.7** - Framework principal
- **Python 3.13** - Lenguaje de programación
- **SQLite** - Base de datos (desarrollo)
- **Requests** - Para consumo de APIs externas

### Frontend
- **Bootstrap 5.3** - Framework CSS
- **Font Awesome 6.4** - Iconografía
- **JavaScript ES6** - Interactividad
- **HTML5 & CSS3** - Estructura y estilos

### APIs Externas
- **OpenLibrary API** - Para búsqueda e importación de libros

## 🚀 Instalación y Configuración

### Prerrequisitos
- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Git

### Pasos de Instalación

1. **Clonar el repositorio**
   ```bash
   git clone <url-del-repositorio>
   cd BibliotecaSolidaridad
   ```

2. **Crear entorno virtual**
   ```bash
   python -m venv env
   # Windows:
   env\Scripts\activate
   # Linux/Mac:
   source env/bin/activate
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar base de datos**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Crear superusuario**
   ```bash
   python manage.py createsuperuser
   ```

6. **Ejecutar servidor de desarrollo**
   ```bash
   python manage.py runserver
   ```

7. **Acceder a la aplicación**
   ```
   http://127.0.0.1:8000/
   ```

## 📁 Estructura del Proyecto

```
BibliotecaSolidaridad/
├── apps/
│   ├── books/           # Gestión de libros y catálogo
│   ├── users/           # Autenticación y perfiles
│   ├── loans/           # Sistema de préstamos
│   ├── culturalevents/  # Cartelera de Eventos
│   └── dashboard/       # Panel administrativo
│   └── reportes/        # Descarga de reportes en csv y xlsx
├── static/
│   ├── css/            # Estilos personalizados
│   ├── js/             # Scripts JavaScript
│   └── images/         # Imágenes y recursos
├── templates/          # Plantillas HTML base
├── media/             # Archivos subidos por usuarios
└── requirements.txt   # Dependencias del proyecto
```

## 🎯 Funcionalidades Detalladas

### Módulo de Libros
- **Agregar libros** manualmente o desde OpenLibrary
- **Búsqueda en tiempo real** en el catálogo local
- **Detalles completos** de cada libro
- **Sistema de categorías** para organización
- **Reseñas y calificaciones** de usuarios

### Módulo de Préstamos
- **Solicitud de préstamos** en línea
- **Aprobación/Rechazo** por administradores
- **Control de fechas** y vencimientos
- **Historial completo** de préstamos por usuario
- **Notificaciones** de estado

### Módulo de Usuarios
- **Registro** con validación de datos
- **Perfiles personalizables**
- **Lista de libros favoritos**
- **Historial personal** de actividad

- ### Módulo de Eventos Culturales
- **Formulario de eventos** con calendario planificador
- **Detalles de los eventos**
- **Lista de Próximos Eventos**

### Dashboard
- **Métricas clave**: libros totales, miembros activos, préstamos
- **Gráficos y estadísticas**
- **Gestión rápida** de solicitudes pendientes
- **Reportes** descargables en csv y xlsx

## 🔧 Configuración de Entorno

### Variables de Entorno
Crear archivo `.env` en la raíz del proyecto:

```env
DEBUG=True
SECRET_KEY=tu-clave-secreta-aqui
DATABASE_URL=sqlite:///db.sqlite3
```

### Configuración de Base de Datos
El proyecto usa SQLite por defecto en desarrollo. Para producción, configurar en `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'biblioteca_db',
        'USER': 'usuario',
        'PASSWORD': 'contraseña',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## 👨‍💻 Desarrollo

### Comandos Útiles

```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Recopilar archivos estáticos
python manage.py collectstatic
```

### Estructura de una App Django

Cada app sigue la estructura estándar de Django:
- `models.py` - Modelos de datos
- `views.py` - Lógica de vistas
- `urls.py` - Rutas de la app
- `forms.py` - Formularios
- `mixins.py` - Mixins
- `templates/` - Plantillas HTML

## 🌐 Despliegue en Producción

### Configuración para Producción

1. **Configurar `DEBUG=False`**
2. **Configurar base de datos PostgreSQL**
3. **Configurar servidor web: PythonAnywhere**
4. **Configurar dominio y SSL**

### Comandos de Producción

```bash
# Recopilar archivos estáticos
python manage.py collectstatic --noinput

# Aplicar migraciones
python manage.py migrate

# Cargar datos iniciales
python manage.py loaddata categorias_iniciales.json
```

## 🤝 Contribución

1. Fork el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## 📝 Licencia

Este proyecto es desarrollado exclusivamente por los contribuyentes, estudiantes de la carrera Tecnicatura Superior en Desarrollo de Software, del IFTS 18 de la Ciudad de Buenos Aires.

## 🆘 Soporte

Si encuentras algún problema o tienes preguntas:

1. Revisa la documentación
2. Abre un issue en el repositorio
3. Contacta al equipo de desarrollo

## 🔄 Estado del Proyecto

**Estado**:  En Desarrollo Activo  
**Versión**: 1.0.0-beta  
**Última Actualización**: Octubre 2026

---

**Desarrollado con ❤️ para la comunidad bibliotecaria**
