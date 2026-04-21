from django.contrib import admin
from .models import Job, SearchLog


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'location', 'source', 'published_at']
    list_filter = ['source', 'published_at']
    search_fields = ['title', 'company']
    ordering = ['-published_at']


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'source', 'results_count', 'searched_at']
    ordering = ['-searched_at']
