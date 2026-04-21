# jobs/urls.py

from django.urls import path
from jobs import views

app_name = 'jobs'

urlpatterns = [
    path('', views.index, name='index'),
    path('search/', views.search, name='search'),
    path('job/<int:job_id>/', views.job_detail, name='detail'),
]