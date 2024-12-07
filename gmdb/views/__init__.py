from SPARQLWrapper import SPARQLWrapper, JSON
from django.shortcuts import render
import rdflib
import re

local_g = rdflib.Graph()
# local_g.parse('Integrated_Movies_Triples.ttl')

sparql = SPARQLWrapper(
    "http://localhost:7200/repositories/GMDb"
)
sparql.setReturnFormat(JSON)

def query_remote(query_str):
    sparql.setQuery(query_str)
    return sparql.query().convert()

INITIAL_NAMESPACES = """
PREFIX : <http://example.com/data/> 
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX v: <http://example.com/vocab#>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX schema: <http://schema.org/>
"""

def query_home_page(query_str, *args):
    returned_data = []
    q_data = query_remote(INITIAL_NAMESPACES + query_str)

    for row in q_data['results']['bindings']:
        poster_url = re.sub(r'_U[XY]\d+.*?AL_', '_UX300_AL_', row['poster']['value'])
        data = {
            "id": row['s']['value'].split('http://example.com/data/')[1],
            "entity_url": row['s']['value'],
            "movieName": row['movieName']['value'],      
            "poster": poster_url,
        }

        returned_data.append(data)
    return returned_data

def query_search(query_str, *args):
    returned_data = []
    q_data = query_remote(INITIAL_NAMESPACES + query_str)

    for row in q_data['results']['bindings']:
        if 'poster' in row:
            poster_url = re.sub(r'_U[XY]\d+.*?AL_', '_UX300_AL_', row['poster']['value'])
        else:
            poster_url = None
        runtime = int(row['runtime']['value'])
        if 'director' in row:
            directorLabel = re.sub(r'(?<!^)(?=[A-Z])', ' ', row['director']['value'].split('http://example.com/data/')[1])
            directorUrl = re.sub(r'(?<!^)(?=[A-Z])', '_', row['director']['value'].split('http://example.com/data/')[1])
        else:
            directorLabel = "Unknown"
            directorUrl = "Unknown"
    
        data = {
            "id": row['s']['value'].split('http://example.com/data/')[1],
            "entity_url": row['s']['value'],
            "movieName": row['movieName']['value'],      
            "poster": poster_url,
            "imdbRating": row['imdbRating']['value'] if 'imdbRating' in row else "N/A",
            "runtime": f"{runtime // 60} h {runtime % 60} m",
            "releasedYear": row['releasedYear']['value'],
            "directorLabel": directorLabel,
            "directorUrl": f"https://en.wikipedia.org/wiki/{directorUrl}"
        }

        returned_data.append(data)
    return returned_data

def query_genre(genre):
    return query_home_page("""
    SELECT DISTINCT ?s ?movieName ?poster where {
        ?s rdfs:label ?movieName ;
        v:poster ?poster ;
        v:genre ?genre .
                 
    FILTER CONTAINS(?genre,\"""" + genre + """\")
    } LIMIT 20
    """)

# Create your views here.
def home_page(request):
    # Top 20 Highest Rating Movies
    top_20_rating_list = query_home_page("""
    SELECT DISTINCT ?s ?movieName ?poster where {
        ?s rdfs:label ?movieName ;
        v:poster ?poster .
    } LIMIT 20
    """)

    # Top 20 Highest Grossing Movies
    top_20_grossing_list = query_home_page("""
    SELECT DISTINCT ?s ?movieName ?poster ?worldWideSales WHERE {
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
    search_args = build_search_args(request.GET)

    if request.GET.get("q"):
        raw_results = query_search("""
        SELECT DISTINCT ?s ?movieName ?poster ?overview ?imdbRating ?runtime ?releasedYear ?director where {
            ?s rdfs:label ?movieName ;
                v:releasedYear ?releasedYear ;
                v:runtime ?runtime ;
                v:overview ?overview .
                OPTIONAL { ?s v:hasFilmCrew [
                    v:hasRole v:Director ;
                    v:filmCrew ?director
                ] . }
                OPTIONAL { ?s v:poster ?poster }
                OPTIONAL { ?s v:imdbScore ?imdbNode .
                ?imdbNode v:rating ?imdbRating . }
        """ + search_args.get('search_filter') + """
        }
        # GROUP BY ?movieName
        """ + search_args.get('sort_filter'))

        # Filter out duplicate movies

        results = []
        added_result_id = []

        for result in raw_results:
            if result['id'] not in added_result_id:
                results.append(result)
                added_result_id.append(result['id'])

    else:
        results = []

    print(results)

    context = {
        'search_query': search_args.get('search_query'),
        'search_type': search_args.get('search_type'),
        'sort_type': search_args.get('sort_type'),
        'results': results
    }

    return render(request, "search.html", context)

search_types = ["title", "extended"]
sort_types = ["title", "rating", "oldest", "newest"]

def build_search_args(request_data):
    search_query = request_data.get("q")
    search_type = request_data.get("searchBy")
    sort_type = request_data.get("sortBy")

    if not search_type or search_type not in search_types:
        search_type = "title"
    if not sort_type or sort_type not in sort_types:
        sort_type = "title"

    if search_type == "extended":
        search_filter = f"FILTER ( CONTAINS(lcase(?movieName), \"{search_query.lower()}\") || CONTAINS(lcase(?overview), \"{search_query.lower()}\") )"
    else:
        search_filter = f"FILTER CONTAINS(lcase(?movieName), \"{search_query.lower()}\")"

    if sort_type == "rating":
        sort_filter = "ORDER BY DESC(?imdbRating)"
    elif sort_type == "oldest":
        sort_filter = "ORDER BY ASC(?releasedYear)"
    elif sort_type == "newest":
        sort_filter = "ORDER BY DESC(?releasedYear)"
    else:
        sort_filter = "ORDER BY ASC(?movieName)"
    
    return {
        'search_query': search_query,
        'search_type': search_type,
        'sort_type': sort_type,
        'search_filter': search_filter,
        'sort_filter': sort_filter
    }

