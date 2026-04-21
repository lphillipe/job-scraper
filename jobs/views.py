# jobs/views.py

from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from datetime import timedelta
from jobs.models import Job
from jobs.services.scraper import search_and_save, SCRAPERS

ESTADOS_BR = [
    'Remoto', 'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO',
    'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ',
    'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
]


def index(request):
    return render(request, 'jobs/index.html', {'estados': ESTADOS_BR})


def search(request):
    keywords = request.GET.get('keywords', '').strip()
    location = request.GET.get('location', '').strip()
    sources_param = request.GET.getlist('sources')  # lista de checkboxes
    state_filter = request.GET.get('state', '').strip()

    if not keywords:
        return render(request, 'jobs/index.html', {
            'error': 'Digite uma palavra-chave.',
            'estados': ESTADOS_BR,
        })

    # Se nenhuma fonte selecionada, usa todas
    available_sources = list(SCRAPERS.keys())
    selected_sources = [s for s in sources_param if s in available_sources] or available_sources

    result = search_and_save(keywords, location or 'Brazil', sources=selected_sources)
    jobs = result['jobs']

    # Filtro de estado/localização aplicado sobre o resultado
    if state_filter:
        if state_filter.lower() == 'remoto':
            jobs = jobs.filter(location__icontains='remot')
        else:
            jobs = jobs.filter(location__icontains=state_filter)

    context = {
        'keywords': keywords,
        'location': location,
        'jobs': jobs,
        'new_count': result['new_count'],
        'total_count': jobs.count(),
        'by_source': result['by_source'],
        'estados': ESTADOS_BR,
        'state_filter': state_filter,
        'selected_sources': selected_sources,
        'available_sources': available_sources,
    }
    return render(request, 'jobs/results.html', context)


def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    return render(request, 'jobs/detail.html', {'job': job})