from django.shortcuts import render
from rdflib import Graph

local_g = Graph()
local_g.parse('Integrated_Movies_Triples.ttl')

# Create your views here.
def home_page(request):
    return render(request, "home.html")