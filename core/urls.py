from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('collection/', views.view_collection, name='view_collection'),
    path('search/', views.search_pokemon, name='search_pokemon'),
]
