# jobs/services/scraper.py

import logging
from django.db import IntegrityError
from jobs.models import Job, SearchLog
from jobs.services.linkedin import fetch_jobs_from_linkedin
from jobs.services.indeed import fetch_jobs_from_indeed

logger = logging.getLogger(__name__)

SCRAPERS = {
    Job.Source.LINKEDIN: fetch_jobs_from_linkedin,
    Job.Source.INDEED: fetch_jobs_from_indeed,
}


def search_and_save(
    keywords: str,
    location: str = 'Brazil',
    sources: list = None,
) -> dict:
    if sources is None:
        sources = list(SCRAPERS.keys())

    logger.info(f'Busca: "{keywords}" | local: "{location}" | fontes: {sources}')

    all_saved_ids = []
    total_new = 0
    results_by_source = {}

    for source in sources:
        scraper_fn = SCRAPERS.get(source)
        if not scraper_fn:
            continue

        logger.info(f'  Raspando {source}...')
        raw_jobs = scraper_fn(keywords, location)

        new_count, saved_ids = _save_jobs(raw_jobs, source)
        total_new += new_count
        all_saved_ids.extend(saved_ids)
        results_by_source[source] = len(saved_ids)

    jobs = Job.objects.filter(id__in=all_saved_ids).order_by('-published_at')

    SearchLog.objects.create(
        keyword=keywords,
        source=','.join(sources),
        results_count=jobs.count(),
    )

    return {
        'jobs': jobs,
        'new_count': total_new,
        'total_count': jobs.count(),
        'by_source': results_by_source,
    }


def _save_jobs(raw_jobs: list[dict], source: str) -> tuple[int, list[int]]:
    new_count = 0
    saved_ids = []

    for job_data in raw_jobs:
        try:
            job = Job.objects.create(source=source, **job_data)
            new_count += 1
            saved_ids.append(job.id)
        except IntegrityError:
            existing = Job.objects.filter(url=job_data['url']).first()
            if existing:
                saved_ids.append(existing.id)
        except Exception as e:
            logger.error(f'Erro ao salvar "{job_data.get("title")}": {e}')

    return new_count, saved_ids