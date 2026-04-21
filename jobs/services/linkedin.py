# jobs/services/linkedin.py

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from datetime import timedelta
from django.utils import timezone as django_timezone
import logging
import time

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
}


def fetch_jobs_from_linkedin(keywords: str, location: str = 'Brazil') -> list[dict]:
    """
    Busca vagas na página pública de jobs do LinkedIn.
    Não requer autenticação — usa a listagem pública.
    Faz até 3 páginas (75 vagas) para ter volume suficiente.
    """
    all_jobs = []

    for start in range(0, 75, 25):
        jobs = _fetch_page(keywords, location, start)
        all_jobs.extend(jobs)

        if len(jobs) < 25:
            # LinkedIn não tem mais páginas para esse termo
            break

        # Pausa entre requisições para não ser bloqueado
        time.sleep(1.5)

    logger.info(f'LinkedIn retornou {len(all_jobs)} vagas para "{keywords}"')
    return all_jobs


def _fetch_page(keywords: str, location: str, start: int) -> list[dict]:
    """
    Busca uma página de resultados (25 vagas por página).
    """
    from urllib.parse import quote

    url = (
        'https://www.linkedin.com/jobs/search'
        f'?keywords={quote(keywords)}'
        f'&location={quote(location)}'
        f'&f_TPR=r604800'   # últimos 7 dias
        f'&start={start}'
    )

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f'Erro ao buscar LinkedIn (start={start}): {e}')
        return []

    return _parse_page(response.text)


def _parse_page(html: str) -> list[dict]:
    """
    Parseia o HTML da listagem e extrai os dados de cada card de vaga.
    """
    soup = BeautifulSoup(html, 'lxml')
    cutoff = django_timezone.now() - timedelta(days=7)
    jobs = []

    # Cada vaga fica num <div> ou <li> com a classe base-card
    cards = soup.find_all('div', class_='base-card')

    if not cards:
        # Fallback: tenta seletor alternativo que o LinkedIn usa às vezes
        cards = soup.find_all('li', class_='jobs-search__results-list')
        logger.warning(f'Seletor principal não encontrou cards, fallback retornou {len(cards)}')

    for card in cards:
        try:
            # Título
            title_tag = (
                card.find('h3', class_='base-search-card__title') or
                card.find('span', class_='sr-only')
            )
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)

            # Empresa
            company_tag = card.find('h4', class_='base-search-card__subtitle')
            company = company_tag.get_text(strip=True) if company_tag else ''

            # Localização
            location_tag = card.find('span', class_='job-search-card__location')
            location = location_tag.get_text(strip=True) if location_tag else ''

            # URL — está no href do <a> principal do card
            link_tag = card.find('a', class_='base-card__full-link')
            if not link_tag or not link_tag.get('href'):
                continue
            # Remove parâmetros de tracking da URL
            url = link_tag['href'].split('?')[0]

            # Data de publicação — LinkedIn usa <time datetime="2025-04-14">
            time_tag = card.find('time')
            if time_tag and time_tag.get('datetime'):
                published_at = dateparser.parse(time_tag['datetime'])
                if published_at and published_at.tzinfo is None:
                    from datetime import timezone
                    published_at = published_at.replace(tzinfo=timezone.utc)
            else:
                # Se não achar a data, assume agora (melhor do que descartar a vaga)
                published_at = django_timezone.now()

            # Descarta vagas mais antigas que 7 dias
            if published_at < cutoff:
                continue

            jobs.append({
                'title': title,
                'company': company,
                'location': location,
                'description': '',   # descrição completa vem da página individual
                'url': url,
                'published_at': published_at,
            })

        except Exception as e:
            logger.warning(f'Erro ao parsear card: {e}')
            continue

    return jobs