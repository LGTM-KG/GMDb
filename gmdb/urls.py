from django.urls import path
from gmdb.views import *

app_name = 'gmdb'

urlpatterns = [
    path('', home_page, name='home_page')
]