# jobs/management/commands/fetch_jobs.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from jobs.services.scraper import search_and_save


# Termos de busca padrão — rodados quando nenhum keyword é passado
DEFAULT_KEYWORDS = [
    'desenvolvedor python',
    'django developer',
    'python backend',
    'fastapi developer',
]


class Command(BaseCommand):
    help = 'Busca vagas no LinkedIn e salva no banco de dados.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keywords',
            type=str,
            help='Palavra-chave para buscar (ex: --keywords "python django")',
        )
        parser.add_argument(
            '--location',
            type=str,
            default='Brazil',
            help='Localização da busca (padrão: Brazil)',
        )
        parser.add_argument(
            '--all-defaults',
            action='store_true',
            help='Roda todos os termos padrão definidos no comando',
        )

    def handle(self, *args, **options):
        start_time = timezone.now()
        self.stdout.write(
            self.style.HTTP_INFO(f'\n🔍 Iniciando fetch_jobs em {start_time.strftime("%d/%m/%Y %H:%M")}\n')
        )

        # Define quais keywords rodar
        if options['keywords']:
            keywords_list = [options['keywords']]
        elif options['all_defaults']:
            keywords_list = DEFAULT_KEYWORDS
        else:
            # Sem argumentos: pede input interativo
            keyword = input('Digite a palavra-chave para buscar: ').strip()
            if not keyword:
                self.stdout.write(self.style.ERROR('Nenhuma palavra-chave informada. Encerrando.'))
                return
            keywords_list = [keyword]

        location = options['location']
        total_new = 0
        total_found = 0

        for keyword in keywords_list:
            self.stdout.write(f'  Buscando: "{keyword}" em "{location}"...')

            try:
                result = search_and_save(keyword, location)
                total_new += result['new_count']
                total_found += result['total_count']

                # Feedback visual por keyword
                status = self.style.SUCCESS(f"✓ {result['total_count']} vagas")
                if result['new_count'] > 0:
                    status += self.style.WARNING(f" ({result['new_count']} novas)")

                self.stdout.write(f'    {status}')

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'    ✗ Erro ao buscar "{keyword}": {e}')
                )

        # Resumo final
        elapsed = (timezone.now() - start_time).seconds
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Concluído em {elapsed}s — '
                f'{total_found} vagas encontradas, '
                f'{total_new} novas salvas.\n'
            )
        )