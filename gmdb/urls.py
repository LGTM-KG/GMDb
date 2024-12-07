from django.urls import path
from gmdb.views.__init__ import *
from gmdb.views.detail import movie_detail

app_name = 'gmdb'

urlpatterns = [
    path('', home_page, name='home_page'),
    path('search/', search_movies, name='search_movies'),
    path('movie/<str:id>', movie_detail, name='movie_detail')
]