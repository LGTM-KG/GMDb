from django.urls import path
from gmdb.views import *

app_name = 'gmdb'

urlpatterns = [
    path('', home_page, name='home_page'),
    path('movie/<str:id>', movie_detail, name='movie_detail'),
    path('search-results?query=', movie_detail, name='search_results')
]