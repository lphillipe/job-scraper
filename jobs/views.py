# jobs/views.py

from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from datetime import timedelta
from jobs.models import Job
from jobs.services.scraper import search_and_save


def index(request):
    """Página inicial com o formulário de busca."""
    return render(request, 'jobs/index.html')


def search(request):
    """
    Recebe o formulário, aciona o scraper e exibe os resultados.
    Usa GET para que a busca seja compartilhável por URL.
    """
    keywords = request.GET.get('keywords', '').strip()
    location = request.GET.get('location', 'Brazil').strip()

    if not keywords:
        return render(request, 'jobs/index.html', {'error': 'Digite uma palavra-chave.'})

    result = search_and_save(keywords, location)

    context = {
        'keywords': keywords,
        'location': location,
        'jobs': result['jobs'],
        'new_count': result['new_count'],
        'total_count': result['total_count'],
    }
    return render(request, 'jobs/results.html', context)


def job_detail(request, job_id):
    """Exibe os detalhes de uma vaga específica."""
    job = get_object_or_404(Job, id=job_id)
    return render(request, 'jobs/detail.html', {'job': job})
