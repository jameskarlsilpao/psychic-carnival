from . import views
from django.urls import path

urlpatterns = [
    path('', views.index, name = 'index'),
    path('evaluate_ngas', views.evaluate_ngas, name='evaluate_ngas'),
    path('set_ngas_fees', views.set_ngas_fees, name='set_ngas_fees'),
]