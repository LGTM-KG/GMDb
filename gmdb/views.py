from django.shortcuts import render
from rdflib import Graph
import re

local_g = Graph()
local_g.parse('Integrated_Movies_Triples.ttl')

def query(query_str):
    returned_data = []
    q_data = local_g.query("""
                           PREFIX : <http://example.com/data/> 
                           PREFIX foaf: <http://xmlns.com/foaf/0.1/>
                           PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                           PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                           PREFIX v: <http://example.com/vocab#>""" + query_str)
    for row in q_data:
        poster_url = re.sub(r'_U[XY]\d+.*?AL_', '_UX300_AL_', str(row.poster))
        data = {
            "movieName": str(row.movieName),      
            "poster": poster_url,    
        }

        returned_data.append(data)
    return returned_data

def query_genre(genre):
    return query("""
    SELECT ?movieName ?poster where {
        ?s rdfs:label ?movieName ;
        v:poster ?poster ;
        v:genre ?genre .
                 
    FILTER CONTAINS(?genre,\"""" + genre + """\")
    } LIMIT 20
    """)

# Create your views here.
def home_page(request):
    # Top 20 Highest Rating Movies
    top_20_rating_list = query("""
    SELECT ?movieName ?poster where {
        ?s rdfs:label ?movieName ;
        v:poster ?poster .
    } LIMIT 20
    """)

    # Top 20 Highest Grossing Movies
    top_20_grossing_list = query("""
    SELECT ?movieName ?poster ?worldWideSales WHERE {
        ?s rdfs:label ?movieName ;
        v:worldWideSales ?worldWideSales ;
        v:poster ?poster .
	} 
	ORDER BY DESC(?worldWideSales) 
	LIMIT 20
    """)

    # Group all data
    context = {
        "sections": [
            {
                "title": "Top 20 Highest Rating Movies",
                "items": top_20_rating_list
            },
            {
                "title": "Top 20 Highest Grossing Movies",
                "items": top_20_grossing_list
            },
            {
                "title": "Romance Movies",
                "items": query_genre("Romance")
            },
            {
                "title": "Comedy Movies",
                "items": query_genre("Comedy")
            },
            {
                "title": "Action Movies",
                "items": query_genre("Action")
            }
        ]
    }
    
    return render(request, "home.html", context)

def search_movies(request):
    search_query = request.GET.get("q")

    results = query("""
    SELECT DISTINCT ?movieName ?poster where {
        ?s rdfs:label ?movieName ;
            v:poster ?poster ;
            v:genre ?genre .

    FILTER CONTAINS(lcase(?movieName),\"""" + search_query.lower() + """\")
    }
    """)

    context = {
        'search_query': search_query,
        'results': results
    }

    return render(request, "search.html", context)

def movie_detail(request, name):
    return render(request, "movie-detail.html")