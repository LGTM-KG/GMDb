from django.shortcuts import render
from rdflib import Graph
import re

local_g = Graph()
local_g.parse('Integrated_Movies_Triples.ttl')

def query(query_str):
    list_of_data = []
    q_data = local_g.query(query_str) # Execute the SPARQL query
    for row in q_data:
        poster_url = re.sub(r'_U[XY]\d+.*?AL_', '_UX300_AL_', str(row.poster))
        data = {
            "movieName": str(row.movieName),      
            "poster": poster_url,    
        }

        list_of_data.append(data)
    return list_of_data

# Create your views here.
def home_page(request):
    # Top 20 Highest Rating Movies
    top_20_rating_list = query("""
    PREFIX : <http://example.com/data/> 
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX v: <http://example.com/vocab#>

    SELECT ?movieName ?poster where {
        ?s rdfs:label ?movieName ;
            v:poster ?poster .
    } LIMIT 20
    """)

    # Top 20 Highest Grossing Movies
    top_20_grossing_list = query("""
    PREFIX : <http://example.com/data/> 
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX v: <http://example.com/vocab#>

    SELECT ?movieName ?poster ?worldWideSales WHERE {
        ?s rdfs:label ?movieName ;
    	    v:worldWideSales ?worldWideSales ;
    	    v:poster ?poster .

        # Aladdin doesn't have a poster (even though there is a link), so this filter will pass it
        FILTER (?movieName != "Aladdin")
	} 
	ORDER BY DESC(?worldWideSales) 
	LIMIT 20
    """)

    # Romance Movies
    top_20_romance_list = query("""
    PREFIX : <http://example.com/data/> 
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX v: <http://example.com/vocab#>

    SELECT ?movieName ?poster where {
        ?s rdfs:label ?movieName ;
            v:poster ?poster ;
            v:genre ?genre .

    FILTER CONTAINS(?genre,"Romance")
    } LIMIT 20
    """)

    # Comedy Movies
    top_20_comedy_list = query("""
    PREFIX : <http://example.com/data/> 
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX v: <http://example.com/vocab#>

    SELECT ?movieName ?poster where {
        ?s rdfs:label ?movieName ;
            v:poster ?poster ;
            v:genre ?genre .

    FILTER CONTAINS(?genre,"Comedy")
    } LIMIT 20
    """)

    # Action Movies
    top_20_action_list = query("""
    PREFIX : <http://example.com/data/> 
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX v: <http://example.com/vocab#>

    SELECT ?movieName ?poster where {
        ?s rdfs:label ?movieName ;
            v:poster ?poster ;
            v:genre ?genre .

    FILTER CONTAINS(?genre,"Action")
    } LIMIT 20
    """)

    # Group all data
    context = {
        'top_20_rating': top_20_rating_list,
        'top_20_grossing': top_20_grossing_list,
        'romance': top_20_romance_list,
        'comedy': top_20_comedy_list,
        'action': top_20_action_list
    }
    
    return render(request, "home.html", context)

def search_movies(request):
    search_query = request.GET.get("q")

    results = query("""
    PREFIX : <http://example.com/data/> 
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX v: <http://example.com/vocab#>

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
