import logging
import requests
from django.utils.text import slugify
from django.core.cache import cache
from requests.exceptions import Timeout, ConnectionError, HTTPError

logger = logging.getLogger(__name__)

class OpenLibraryService:
    """Servicio para interactuar con la API de OpenLibrary"""
    
    BASE_URL = "https://openlibrary.org"
    TIMEOUT = 10
    CACHE_TTL = 3600  # 1 hora
    MAX_RETRIES = 3
    
    @staticmethod
    def search_books(query: str, limit: int = 10) -> list:
        """
        Busca libros en OpenLibrary
        
        Args:
            query (str): Término de búsqueda
            limit (int): Número máximo de resultados
            
        Returns:
            list: Lista de libros con estructura standarizada
            
        Raises:
            ValueError: Si query está vacío
        """
        if not query or not query.strip():
            raise ValueError("Query no puede estar vacío")
        
        # Verificar caché primero
        cache_key = f"openlibrary_search_{slugify(query.lower())}_{limit}"
        cached_results = cache.get(cache_key)
        if cached_results is not None:
            logger.info(f"OpenLibrary search from cache: {query}")
            return cached_results
        
        try:
            response = requests.get(
                f"{OpenLibraryService.BASE_URL}/search.json",
                params={'q': query, 'limit': limit},
                timeout=OpenLibraryService.TIMEOUT
            )
            response.raise_for_status()
            
            results = OpenLibraryService._parse_response(response.json())
            
            # Guardar en caché
            cache.set(cache_key, results, OpenLibraryService.CACHE_TTL)
            
            logger.info(f"OpenLibrary search successful: {query} ({len(results)} results)")
            return results
            
        except Timeout:
            logger.error(f"OpenLibrary timeout for query: {query}")
            return []
        except ConnectionError:
            logger.error(f"OpenLibrary connection error for query: {query}")
            return []
        except HTTPError as e:
            logger.error(f"OpenLibrary HTTP error: {e.response.status_code} for query: {query}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in OpenLibrary search: {str(e)}")
            return []
    
    @staticmethod
    def _parse_response(data: dict) -> list:
        """Parsea la respuesta de OpenLibrary a formato estándar"""
        results = []
        for doc in data.get('docs', []):
            results.append({
                'title': doc.get('title', ''),
                'authors': ', '.join(doc.get('author_name', [])),
                'publish_year': doc.get('first_publish_year', ''),
                'isbn': ', '.join(doc.get('isbn', [])[:1]) if doc.get('isbn') else '',
                'openlibrary_id': doc.get('edition_key', [None])[0] or doc.get('key'),
                'cover_url': (
                    f"https://covers.openlibrary.org/b/id/{doc.get('cover_i')}-M.jpg"
                    if doc.get('cover_i') else None
                ),
                'number_of_pages': doc.get('number_of_pages'),
                'description': doc.get('description', ''),
            })
        return results

    