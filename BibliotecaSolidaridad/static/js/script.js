    // Función para escapar HTML (seguridad)
    function escapeHtml(unsafe) {
        if (!unsafe) return '';
        const div = document.createElement('div');
        div.textContent = unsafe;
        return div.innerHTML;
    }


    // ✅ AGREGAR: Función de notificación mejorada
    function showNotification(message, type = 'info') {
        // Buscar o crear contenedor de notificaciones
        let notificationContainer = document.getElementById('notification-container');
        if (!notificationContainer) {
            notificationContainer = document.createElement('div');
            notificationContainer.id = 'notification-container';
            notificationContainer.style.cssText = 'position: fixed; top: 80px; right: 20px; z-index: 1060; min-width: 300px;';
            document.body.appendChild(notificationContainer);
        }

        const alertClass = {
            'success': 'alert-success',
            'error': 'alert-danger',
            'warning': 'alert-warning',
            'info': 'alert-info'
        }[type] || 'alert-info';

        const notification = document.createElement('div');
        notification.className = `alert ${alertClass} alert-dismissible fade show`;
        notification.innerHTML = `
        <i class="${icon} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

        notificationContainer.appendChild(notification);

        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    // ✅ AGREGAR: Manejo de envío del formulario con loading
    document.getElementById('book-form').addEventListener('submit', function (e) {
        const submitBtn = document.getElementById('submit-btn');
        const originalText = submitBtn.innerHTML;

        // Mostrar loading
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
        submitBtn.disabled = true;

        // Validación básica
        const title = document.getElementById('id_title').value.trim();
        const authors = document.getElementById('id_authors_input').value.trim();

        if (!title || !authors) {
            e.preventDefault();
            showNotification('Los campos Título y Autores son obligatorios', 'warning');
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
            return false;
        }

        return true;
    });


    document.getElementById('search-openlibrary').addEventListener('submit', async function (e) {
        e.preventDefault();
        const query = document.getElementById('search-query').value.trim();
        if (!query) return;

        const resultsDiv = document.getElementById('search-results');
        const resultsList = document.getElementById('results-list');

        resultsList.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border text-primary" role="status"></div>
            <p class="mt-2 text-muted">Buscando en OpenLibrary...</p>
        </div>`;
        resultsDiv.style.display = 'block';

        try {
            const resp = await fetch(`/books/api/search-openlibrary/?q=${encodeURIComponent(query)}`);
            const data = await resp.json();
            if (data.error) throw new Error(data.error);

            if (data.mode === 'isbn') {
                if (!data.edition) {
                    resultsList.innerHTML = `<div class="alert alert-info">${escapeHtml(data.message)}</div>`;
                } else {
                    resultsList.innerHTML = '<h6 class="mb-2">Edición encontrada por ISBN:</h6>';
                    resultsList.appendChild(buildEditionCard(data.edition, data.edition.title));
                }
            } else {
                renderWorksList(data.books || []);
            }
        } catch (err) {
            console.error(err);
            resultsList.innerHTML = `<div class="alert alert-danger">Error: ${escapeHtml(err.message)}</div>`;
        }
    });

    // ============================================================
    // Render de lista de obras (colapsables)
    // ============================================================
    function renderWorksList(books) {
        const resultsList = document.getElementById('results-list');
        resultsList.innerHTML = '';

        if (books.length === 0) {
            resultsList.innerHTML = `<div class="text-center text-muted py-3">Sin resultados</div>`;
            return;
        }

        books.forEach((book, idx) => {
            const authors = Array.isArray(book.author_name)
                ? book.author_name.join(', ')
                : (book.author_name || 'Autor desconocido');

            const workKey = book.work_key || book.openlibrary_id;

            const item = document.createElement('div');
            item.className = 'list-group-item';
            item.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1 me-3">
                    <h6 class="mb-1">${escapeHtml(book.title || 'Sin título')}</h6>
                    <p class="mb-1 text-muted small">${escapeHtml(authors)}</p>
                    <small class="text-muted">
                        ${book.publish_year ? `Primera edición: ${book.publish_year}` : ''}
                    </small>
                </div>
                <button type="button" class="btn btn-sm btn-outline-secondary btn-toggle-editions">
                    <i class="fas fa-chevron-down"></i> Ver ediciones
                </button>
            </div>
            <div class="editions-container mt-3" style="display:none;"></div>
        `;

            const toggleBtn = item.querySelector('.btn-toggle-editions');
            const editionsContainer = item.querySelector('.editions-container');
            let loaded = false;

            toggleBtn.addEventListener('click', async () => {
                // Toggle
                const isOpen = editionsContainer.style.display !== 'none';
                if (isOpen) {
                    editionsContainer.style.display = 'none';
                    toggleBtn.innerHTML = '<i class="fas fa-chevron-down"></i> Ver ediciones';
                    return;
                }
                editionsContainer.style.display = 'block';
                toggleBtn.innerHTML = '<i class="fas fa-chevron-up"></i> Ocultar';

                if (loaded) return;
                loaded = true;

                editionsContainer.innerHTML = `
                <div class="text-center py-2">
                    <div class="spinner-border spinner-border-sm text-primary"></div>
                    <small class="text-muted ms-2">Cargando ediciones...</small>
                </div>`;

                try {
                    const r = await fetch(`/books/api/work-editions/?work_id=${encodeURIComponent(workKey)}`);
                    const payload = await r.json();

                    if (!payload.editions || payload.editions.length === 0) {
                        editionsContainer.innerHTML = `
                        <div class="alert alert-warning py-2 mb-0 small">
                            No hay ediciones registradas para esta obra.
                        </div>`;
                        return;
                    }

                    editionsContainer.innerHTML = '';
                    payload.editions.forEach(ed => {
                        editionsContainer.appendChild(buildEditionCard(ed, book.title, book.author_name, book.publish_year));
                    });
                } catch (err) {
                    console.error(err);
                    editionsContainer.innerHTML = `<div class="alert alert-danger py-2 small">Error al cargar ediciones.</div>`;
                    loaded = false;
                }
            });

            resultsList.appendChild(item);
        });
    }

    // ============================================================
    // Card individual de edición
    // ============================================================
    function buildEditionCard(edition, fallbackTitle, fallbackAuthor, fallbackYear) {
        const publishers = (edition.publishers || []).join(', ');
        const isbn = edition.isbn || (edition.isbn_all && edition.isbn_all[0]) || '';

        const card = document.createElement('div');
        card.className = 'border rounded p-2 mb-2 bg-light';
        card.innerHTML = `
        <div class="d-flex justify-content-between align-items-start">
            <div class="flex-grow-1 me-2">
                <div class="fw-bold small">${escapeHtml(edition.title || fallbackTitle)}</div>
                <div class="text-muted small">
                    ${edition.publish_date ? escapeHtml(edition.publish_date) : 'Sin fecha'}
                    ${publishers ? ` · ${escapeHtml(publishers)}` : ''}
                    ${edition.number_of_pages ? ` · ${edition.number_of_pages} pág.` : ''}
                    ${edition.physical_format ? ` · ${escapeHtml(edition.physical_format)}` : ''}
                </div>
                ${isbn ? `<div class="small mt-1"><strong>ISBN:</strong> ${escapeHtml(isbn)}</div>` : '<div class="small mt-1 text-warning">Sin ISBN registrado</div>'}
            </div>
            <button type="button" class="btn btn-sm btn-primary btn-pick-edition">
                <i class="fas fa-check"></i> Usar
            </button>
        </div>
    `;

        card.querySelector('.btn-pick-edition').addEventListener('click', function () {
            fillBookFormFromEdition(edition, fallbackTitle, fallbackAuthor, fallbackYear);
            this.innerHTML = '<i class="fas fa-check-double"></i> Cargado';
            this.disabled = true;
        });

        return card;
    }

    // ============================================================
    // Llenar el form con la edición elegida
    // ============================================================
    function fillBookFormFromEdition(edition, fallbackTitle, fallbackAuthor, fallbackYear) {
        const set = (id, value) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = value ?? '';
    el.dispatchEvent(new Event('input', { bubbles: true }));   // ← clave
};

        const isbn = edition.isbn
            || (edition.isbn_all && edition.isbn_all[0])
            || (edition.isbn_13 && edition.isbn_13[0])
            || (edition.isbn_10 && edition.isbn_10[0])
            || '';

        const authors = Array.isArray(edition.authors)
            ? edition.authors.join(', ')
            : '';

        set('id_title', edition.title || fallbackTitle || '');
        set('id_authors_input', authors || fallbackAuthor || '');
        set('id_isbn_input', isbn);
        set('id_publish_date', edition.publish_date || '');
        set('id_cover_url', edition.cover_url || '');
        set('id_number_of_pages', edition.number_of_pages || '');
        set('id_openlibrary_id', edition.olid || '');

        document.getElementById('search-results').style.display = 'none';
        showAlert(`Edición cargada: ${edition.title || fallbackTitle}`, 'success');
        document.getElementById('book-form').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    (function () {
    const input = document.getElementById('id_cover_url');
    const preview = document.getElementById('cover-preview');
    const wrapper = document.getElementById('cover-preview-wrapper');
    const emptyMsg = document.getElementById('cover-empty-msg');
    const errorMsg = wrapper ? wrapper.querySelector('.cover-error') : null;
    if (!input || !preview || !wrapper) return;

    function updatePreview() {
        const url = (input.value || '').trim();
        if (errorMsg) errorMsg.classList.add('d-none');

        if (!url) {
            wrapper.classList.add('d-none');
            emptyMsg.classList.remove('d-none');
            preview.src = '';
            return;
        }
        wrapper.classList.remove('d-none');
        emptyMsg.classList.add('d-none');
        preview.classList.remove('d-none');
        preview.src = url;
    }

    input.addEventListener('input', updatePreview);
    input.addEventListener('change', updatePreview);
    updatePreview();   // ← esto corre al cargar y decide qué mostrar
})();