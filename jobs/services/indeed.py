# jobs/services/indeed.py

from curl_cffi import requests
from bs4 import BeautifulSoup
from datetime import timedelta
from django.utils import timezone as django_timezone
from urllib.parse import quote
import logging
import time
import re

logger = logging.getLogger(__name__)


def fetch_jobs_from_indeed(keywords: str, location: str = '') -> list[dict]:
    all_jobs = []

    for page in range(0, 3):
        jobs = _fetch_page(keywords, location, page)
        all_jobs.extend(jobs)

        if len(jobs) < 10:
            break

        time.sleep(2)

    logger.info(f'Indeed retornou {len(all_jobs)} vagas para "{keywords}"')
    return all_jobs


def _fetch_page(keywords: str, location: str, page: int) -> list[dict]:
    url = (
        f'https://br.indeed.com/jobs'
        f'?q={quote(keywords)}'
        f'&l={quote(location)}'
        f'&fromage=7'
        f'&sort=date'
        f'&start={page * 10}'
    )

    try:
        # impersonate="chrome120" replica o handshake TLS do Chrome
        # é isso que derruba o 403 na maioria dos casos
        response = requests.get(url, impersonate="chrome120", timeout=15)
        response.raise_for_status()
    except Exception as e:
        logger.error(f'Erro ao buscar Indeed (página {page}): {e}')
        return []

    return _parse_page(response.text)


def _parse_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, 'lxml')
    jobs = []
    cutoff = django_timezone.now() - timedelta(days=7)

    cards = soup.find_all('div', attrs={'data-jk': True})

    if not cards:
        cards = soup.find_all('td', class_='resultContent')
        logger.warning(f'Seletor principal vazio, fallback retornou {len(cards)}')

    for card in cards:
        try:
            title_tag = (
                card.find('h2', class_=re.compile(r'jobTitle', re.I)) or
                card.find('a', attrs={'data-jk': True})
            )
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            title = re.sub(r'^(novo|new)\s+', '', title, flags=re.I).strip()

            job_key = card.get('data-jk')
            if not job_key:
                jk_tag = card.find(attrs={'data-jk': True})
                job_key = jk_tag.get('data-jk') if jk_tag else None
            if not job_key:
                continue

            url = f'https://br.indeed.com/viewjob?jk={job_key}'

            company_tag = (
                card.find('span', attrs={'data-testid': 'company-name'}) or
                card.find('a', attrs={'data-tn-element': 'companyName'}) or
                card.find(class_=re.compile(r'companyName', re.I))
            )
            company = company_tag.get_text(strip=True) if company_tag else ''

            location_tag = (
                card.find('div', attrs={'data-testid': 'text-location'}) or
                card.find(class_=re.compile(r'companyLocation', re.I))
            )
            location_str = location_tag.get_text(strip=True) if location_tag else ''

            date_tag = (
                card.find('span', attrs={'data-testid': 'myJobsStateDate'}) or
                card.find(class_=re.compile(r'date|posted', re.I))
            )
            published_at = _parse_relative_date(
                date_tag.get_text(strip=True) if date_tag else ''
            )

            if published_at < cutoff:
                continue

            jobs.append({
                'title': title,
                'company': company,
                'location': location_str,
                'description': '',
                'url': url,
                'published_at': published_at,
            })

        except Exception as e:
            logger.warning(f'Erro ao parsear card Indeed: {e}')
            continue

    return jobs


def _parse_relative_date(text: str):
    now = django_timezone.now()
    text = text.lower().strip()

    if not text or 'hoje' in text or 'today' in text or 'agora' in text:
        return now
    if 'ontem' in text or 'yesterday' in text:
        return now - timedelta(days=1)

    match = re.search(r'(\d+)', text)
    if match:
        days = int(match.group(1))
        return now - timedelta(days=days)

    return now