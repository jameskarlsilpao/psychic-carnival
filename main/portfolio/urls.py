from . import views
from django.urls import path

urlpatterns = [
    path('', views.index, name = 'index'),
    path('evaluate_ngas', views.evaluate_ngas, name='evaluate_ngas'),
    path('evaluate_default', views.evaluate_default, name='evaluate_default'),
    path('set_ngas_fees', views.set_ngas_fees, name='set_ngas_fees'),
    path('evaluate_car', views.evaluate_car, name='evaluate_car'),
    path('contact', views.contact, name='contact'),
]