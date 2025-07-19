from django.urls import path
from .views import analyze_query, index, predict_price

urlpatterns = [
    path('', index, name='index'),
    path('analyze/', analyze_query, name='analyze_query'),
    path('predict/', predict_price, name='predict_price'), 
]