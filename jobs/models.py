# jobs/models.py

from django.db import models


class Job(models.Model):

    class Source(models.TextChoices):
        LINKEDIN = 'linkedin', 'LinkedIn'
        INDEED = 'indeed', 'Indeed'

    # Informações principais da vaga
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True, default='')
    location = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True, default='')
    url = models.URLField(max_length=1000, unique=True)

    # Controle de origem e data
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.LINKEDIN,
    )
    published_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'Vaga'
        verbose_name_plural = 'Vagas'

    def __str__(self):
        return f'{self.title} — {self.company}'


class SearchLog(models.Model):
    keyword = models.CharField(max_length=255)
    source = models.CharField(max_length=20, default='linkedin')
    results_count = models.IntegerField(default=0)
    searched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-searched_at']
        verbose_name = 'Busca'
        verbose_name_plural = 'Buscas'

    def __str__(self):
        return f'"{self.keyword}" ({self.results_count} resultados)'