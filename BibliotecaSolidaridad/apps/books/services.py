import re
import logging

import requests
from django.core.cache import cache
from django.utils.text import slugify
from requests.exceptions import Timeout, ConnectionError, HTTPError

logger = logging.getLogger(__name__)

class OpenLibraryService:
    """Servicio para interactuar con la API de OpenLibrary."""

    BASE_URL = "https://openlibrary.org"
    COVERS_URL = "https://covers.openlibrary.org"
    TIMEOUT = 10
    CACHE_TTL = 3600  # 1 hora

    # ⚠️ IMPORTANTE: identificarse con OpenLibrary. Poné tu email real.
    HEADERS = {
        "User-Agent": "BibliotecaSolidaridad/1.0 (contacto@tudominio.com)"
    }

    # =================================================================
    # Autores
    # =================================================================

    @staticmethod
    def get_author_details(olid: str) -> dict:
        """Obtiene los datos de un autor desde OpenLibrary."""
        if not olid or not olid.strip():
            raise ValueError("El identificador del autor no puede estar vacío")

        author_id = olid.strip().rsplit('/', 1)[-1]
        cache_key = f"openlibrary_author_{slugify(author_id)}"
        cached_author = cache.get(cache_key)
        if cached_author is not None:
            return cached_author

        try:
            response = requests.get(
                f"{OpenLibraryService.BASE_URL}/authors/{author_id}.json",
                headers=OpenLibraryService.HEADERS,
                timeout=OpenLibraryService.TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            author = {
                'openlibrary_id': data.get('key', f'/authors/{author_id}'),
                'name': data.get('name', ''),
                'bio': data.get('bio', ''),
                'birth_date': data.get('birth_date'),
                'death_date': data.get('death_date'),
                'photo_ids': data.get('photos', []),
                'works_count': data.get('work_count', 0),
            }
            cache.set(cache_key, author, OpenLibraryService.CACHE_TTL)
            return author
        except (Timeout, ConnectionError, HTTPError, ValueError) as error:
            logger.error("Error fetching OpenLibrary author %s: %s", author_id, error)
            return {}

    # =================================================================
    # Búsqueda general
    # =================================================================

    @staticmethod
    def search_books(query: str, limit: int = 10) -> list:
        """Busca libros en OpenLibrary. Devuelve obras (no ediciones)."""
        if not query or not query.strip():
            raise ValueError("Query no puede estar vacío")

        cache_key = f"openlibrary_search_{slugify(query.lower())}_{limit}"
        cached_results = cache.get(cache_key)
        if cached_results is not None:
            logger.info("OpenLibrary search from cache: %s", query)
            return cached_results

        try:
            response = requests.get(
                f"{OpenLibraryService.BASE_URL}/search.json",
                params={'q': query, 'limit': limit},
                headers=OpenLibraryService.HEADERS,
                timeout=OpenLibraryService.TIMEOUT,
            )
            response.raise_for_status()

            results = OpenLibraryService._parse_response(response.json())
            cache.set(cache_key, results, OpenLibraryService.CACHE_TTL)
            logger.info(
                "OpenLibrary search successful: %s (%s results)",
                query, len(results),
            )
            return results

        except Timeout:
            logger.error("OpenLibrary timeout for query: %s", query)
            return []
        except ConnectionError:
            logger.error("OpenLibrary connection error for query: %s", query)
            return []
        except HTTPError as e:
            logger.error(
                "OpenLibrary HTTP error %s for query: %s",
                e.response.status_code, query,
            )
            return []
        except Exception as e:
            logger.error("Unexpected error in OpenLibrary search: %s", e)
            return []

    @staticmethod
    def _parse_response(data: dict) -> list:
        """Parsea la respuesta de /search.json a formato estándar."""
        results = []
        for doc in data.get('docs', []):
            isbn_list = doc.get('isbn', []) or []
            author_names = doc.get('author_name', []) or []
            author_keys = doc.get('author_key', []) or []
            pages = doc.get('number_of_pages_median')

            cover_id = doc.get('cover_i')
            cover_url = (
                f"{OpenLibraryService.COVERS_URL}/b/id/{cover_id}-M.jpg"
                if cover_id else None
            )

            edition_keys = doc.get('edition_key') or []
            edition_key = edition_keys[0] if edition_keys else None
            work_key = doc.get('key', '')

            description = doc.get('first_sentence', '')
            if isinstance(description, list):
                description = description[0] if description else ''

            results.append({
                'title': doc.get('title', ''),
                'author_name': author_names,
                'author_key': author_keys,
                'publish_year': doc.get('first_publish_year', ''),
                'isbn': isbn_list[:3],
                'edition_key': edition_key,          # puede ser None
                'work_key': work_key,                # siempre presente
                'openlibrary_id': edition_key or work_key,
                'cover_url': cover_url,
                'number_of_pages': pages,
                'description': description,
            })
        return results

    # =================================================================
    # Detección y consulta por ISBN
    # =================================================================

    @staticmethod
    def looks_like_isbn(query: str) -> str | None:
        """
        Detecta si el query parece un ISBN.

        Returns:
            El ISBN limpio (sin guiones ni espacios) si parece ISBN.
            None si parece un título o autor.
        """
        if not query:
            return None

        cleaned = re.sub(r'[\s\-]', '', query.strip()).upper()

        # ISBN-10: 9 dígitos + dígito o X
        if len(cleaned) == 10 and re.fullmatch(r'\d{9}[\dX]', cleaned):
            return cleaned

        # ISBN-13: 13 dígitos, debe empezar con 978 o 979
        if len(cleaned) == 13 and re.fullmatch(r'\d{13}', cleaned):
            if cleaned.startswith(('978', '979')):
                return cleaned

        return None

    @staticmethod
    def get_edition_by_isbn(isbn: str) -> dict:
        """Obtiene una edición específica por ISBN."""
        isbn = re.sub(r'[\s\-]', '', isbn)
        cache_key = f"ol_isbn_{isbn}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            response = requests.get(
                f"{OpenLibraryService.BASE_URL}/isbn/{isbn}.json",
                headers=OpenLibraryService.HEADERS,
                timeout=OpenLibraryService.TIMEOUT,
            )
            if response.status_code == 404:
                return {}
            response.raise_for_status()
            raw = response.json()

            # Obra asociada
            work_key = None
            if raw.get('works'):
                work_key = raw['works'][0]['key']

            # Autores: vienen como referencias, hay que resolverlos
            authors = []
            for author_ref in raw.get('authors', []):
                key = author_ref.get('key', '')
                if key:
                    details = OpenLibraryService.get_author_details(key)
                    if details.get('name'):
                        authors.append(details['name'])

            # Portada
            covers = raw.get('covers') or []
            valid_covers = [c for c in covers if isinstance(c, int) and c > 0]
            cover_url = (
                f"{OpenLibraryService.COVERS_URL}/b/id/{valid_covers[0]}-L.jpg"
                if valid_covers else None
            )

            data = {
                'olid': raw.get('key', '').split('/')[-1],
                'title': raw.get('title', ''),
                'subtitle': raw.get('subtitle', ''),
                'publish_date': raw.get('publish_date', ''),
                'publishers': raw.get('publishers', []),
                'number_of_pages': raw.get('number_of_pages'),
                'isbn_10': raw.get('isbn_10', []),
                'isbn_13': raw.get('isbn_13', []),
                'isbn': isbn,
                'covers': covers,
                'cover_url': cover_url,
                'physical_format': raw.get('physical_format', ''),
                'authors': authors,
                'work_key': work_key,
            }
            cache.set(cache_key, data, OpenLibraryService.CACHE_TTL)
            return data

        except Exception as e:
            logger.error("Error obteniendo ISBN %s: %s", isbn, e)
            return {}

    # =================================================================
    # Ediciones de una obra
    # =================================================================

    @staticmethod
    def get_work_editions(work_id: str, limit: int = 50) -> list:
        """
        Dado un work (OL...W), devuelve TODAS sus ediciones con los datos
        que el bibliotecario necesita para identificar el ejemplar físico:
        año, editorial, formato, páginas, ISBN.
        """
        work_id = work_id.strip().rsplit('/', 1)[-1]
        cache_key = f"ol_work_editions_{work_id}_{limit}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            response = requests.get(
                f"{OpenLibraryService.BASE_URL}/works/{work_id}/editions.json",
                params={"limit": limit},
                headers=OpenLibraryService.HEADERS,
                timeout=OpenLibraryService.TIMEOUT,
            )
            response.raise_for_status()
            entries = response.json().get('entries', [])

            editions = []
            for ed in entries:
                # ISBN: preferir el 13, si no el 10
                isbn = None
                if ed.get('isbn_13'):
                    isbn = ed['isbn_13'][0]
                elif ed.get('isbn_10'):
                    isbn = ed['isbn_10'][0]

                # Portada
                covers = ed.get('covers') or []
                valid_covers = [c for c in covers if isinstance(c, int) and c > 0]
                cover_url = (
                    f"{OpenLibraryService.COVERS_URL}/b/id/{valid_covers[0]}-M.jpg"
                    if valid_covers else None
                )

                editions.append({
                    'olid': ed.get('key', '').split('/')[-1],
                    'title': ed.get('title', ''),
                    'subtitle': ed.get('subtitle', ''),
                    'publish_date': ed.get('publish_date', ''),
                    'publishers': ed.get('publishers', []),
                    'number_of_pages': ed.get('number_of_pages'),
                    'physical_format': ed.get('physical_format', ''),
                    'isbn': isbn,
                    'isbn_all': (ed.get('isbn_13', []) + ed.get('isbn_10', []))[:3],
                    'cover_url': cover_url,
                    'languages': ed.get('languages', []),
                })

            # Ordenar: las que tienen más datos primero
            editions.sort(
                key=lambda e: (
                    bool(e['isbn']),
                    bool(e['number_of_pages']),
                    bool(e['publish_date']),
                ),
                reverse=True,
            )

            cache.set(cache_key, editions, OpenLibraryService.CACHE_TTL)
            return editions

        except Exception as e:
            logger.error("Error obteniendo ediciones de %s: %s", work_id, e)
            return []