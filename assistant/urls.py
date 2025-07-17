from django.urls import path
from .views import analyze_query, index

urlpatterns = [
    path('', index, name='index'),
    path('analyze/', analyze_query, name='analyze_query'),
]