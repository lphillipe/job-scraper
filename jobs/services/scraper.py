# jobs/services/scraper.py

import logging
from django.db import IntegrityError
from jobs.models import Job, SearchLog
from jobs.services.linkedin import fetch_jobs_from_linkedin

logger = logging.getLogger(__name__)


def search_and_save(keywords: str, location: str = 'Brazil') -> dict:
    logger.info(f'Iniciando busca: "{keywords}" em "{location}"')

    raw_jobs = fetch_jobs_from_linkedin(keywords, location)

    new_count = 0
    saved_ids = []

    for job_data in raw_jobs:
        try:
            job = Job.objects.create(
                source=Job.Source.LINKEDIN,
                **job_data,
            )
            new_count += 1
            saved_ids.append(job.id)
        except IntegrityError:
            # Vaga já existe — busca pelo ID para incluir nos resultados
            existing = Job.objects.filter(url=job_data['url']).first()
            if existing:
                saved_ids.append(existing.id)
        except Exception as e:
            logger.error(f'Erro ao salvar vaga "{job_data.get("title")}": {e}')

    # Retorna exatamente as vagas dessa busca (novas + já existentes)
    jobs = Job.objects.filter(id__in=saved_ids)

    SearchLog.objects.create(
        keyword=keywords,
        source='linkedin',
        results_count=jobs.count(),
    )

    logger.info(f'Busca concluída: {new_count} novas, {jobs.count()} total retornado')

    return {
        'jobs': jobs,
        'new_count': new_count,
        'total_count': jobs.count(),
    }