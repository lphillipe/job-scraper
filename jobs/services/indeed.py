# jobs/services/indeed.py

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from datetime import timedelta, timezone
from django.utils import timezone as django_timezone
from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
}


def fetch_jobs_from_indeed(keywords: str, location: str = 'Brazil') -> list[dict]:
    """
    Busca vagas no Indeed via RSS público.
    Ainda funciona sem autenticação.
    """
    url = (
        f'https://br.indeed.com/rss'
        f'?q={quote(keywords)}'
        f'&l={quote(location)}'
        f'&fromage=7'  # últimos 7 dias
        f'&sort=date'
    )

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f'Erro ao buscar Indeed RSS: {e}')
        return []

    jobs = _parse_rss(response.text)
    logger.info(f'Indeed retornou {len(jobs)} vagas para "{keywords}"')
    return jobs


def _parse_rss(xml_content: str) -> list[dict]:
    soup = BeautifulSoup(xml_content, 'xml')
    items = soup.find_all('item')
    jobs = []
    cutoff = django_timezone.now() - timedelta(days=7)

    for item in items:
        try:
            title_tag = item.find('title')
            link_tag = item.find('link')
            pub_date_tag = item.find('pubDate')
            desc_tag = item.find('description')

            if not title_tag or not link_tag:
                continue

            # Título vem como "Cargo - Empresa"
            title_parts = title_tag.text.strip().split(' - ', 1)
            title = title_parts[0].strip()
            company = title_parts[1].strip() if len(title_parts) > 1 else ''

            url = link_tag.text.strip() if link_tag.text else ''
            if not url:
                url = item.find('guid').text.strip() if item.find('guid') else ''
            if not url:
                continue

            # Remove parâmetros de tracking
            url = url.split('?')[0] if '?' in url else url

            # Data
            if pub_date_tag:
                published_at = dateparser.parse(pub_date_tag.text)
                if published_at and published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
            else:
                published_at = django_timezone.now()

            if published_at and published_at < cutoff:
                continue

            # Localização vem na description em alguns casos
            description = ''
            location_str = ''
            if desc_tag:
                desc_soup = BeautifulSoup(desc_tag.text, 'html.parser')
                description = desc_soup.get_text(separator=' ').strip()
                # Indeed inclui localização na descrição: "Local: São Paulo, SP"
                for line in description.split('\n'):
                    if 'local:' in line.lower() or 'location:' in line.lower():
                        location_str = line.split(':', 1)[-1].strip()
                        break

            jobs.append({
                'title': title,
                'company': company,
                'location': location_str or location,
                'description': description,
                'url': url,
                'published_at': published_at or django_timezone.now(),
            })

        except Exception as e:
            logger.warning(f'Erro ao parsear item Indeed: {e}')
            continue

    return jobs