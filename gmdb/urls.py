from django.urls import path
from gmdb.views import *

app_name = 'gmdb'

urlpatterns = [
    path('', home_page, name='home_page'),
    path('search/', search_movies, name='search_movies'),
    path('movie/<str:name>', movie_detail, name='movie_detail')
]