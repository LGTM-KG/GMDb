from django.shortcuts import render
import rdflib
from rdflib.plugins.sparql import prepareQuery
import re
import datetime

local_g = rdflib.Graph()
local_g.parse('Integrated_Movies_Triples.ttl')

INITIAL_NAMESPACES = """
PREFIX : <http://example.com/data/> 
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX v: <http://example.com/vocab#>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX schema: <http://schema.org/>
"""

def query_search(query_str, *args):
    returned_data = []
    q_data = local_g.query(INITIAL_NAMESPACES + query_str, *args)
    for row in q_data:
        poster_url = re.sub(r'_U[XY]\d+.*?AL_', '_UX300_AL_', str(row.poster))
        id = str(row.s)
        print(1, id)
        data = {
            "id": str(row.s).split('http://example.com/data/')[1],
            "entity_url": str(row.s),
            "movieName": str(row.movieName),      
            "poster": poster_url,    
        }

        returned_data.append(data)
    return returned_data

def query_genre(genre):
    return query_search("""
    SELECT ?s ?movieName ?poster where {
        ?s rdfs:label ?movieName ;
        v:poster ?poster ;
        v:genre ?genre .
                 
    FILTER CONTAINS(?genre,\"""" + genre + """\")
    } LIMIT 20
    """)

# Create your views here.
def home_page(request):
    # Top 20 Highest Rating Movies
    top_20_rating_list = query_search("""
    SELECT ?s ?movieName ?poster where {
        ?s rdfs:label ?movieName ;
        v:poster ?poster .
    } LIMIT 20
    """)

    # Top 20 Highest Grossing Movies
    top_20_grossing_list = query_search("""
    SELECT ?s ?movieName ?poster ?worldWideSales WHERE {
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

    results = query_search("""
    SELECT DISTINCT ?s ?movieName ?poster where {
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

detail_q = prepareQuery(
    INITIAL_NAMESPACES + """ 
    SELECT * WHERE {
		?s rdfs:label ?label.
		?s v:hasWikidata ?item .
        OPTIONAL { ?s v:poster ?poster . }
        OPTIONAL { ?s v:genre ?genre . }
        OPTIONAL { ?s v:worldWideSales ?worldWideSales . }
        OPTIONAL { ?s v:releaseDate ?releaseDate . }
        OPTIONAL { ?s v:runtime ?runtime . }
        OPTIONAL { ?s v:releasedYear ?releasedYear . }
        OPTIONAL { ?s v:releasedDate ?releasedDate . }
        OPTIONAL { ?s v:certification ?certification . }
		SERVICE <https://query.wikidata.org/sparql> {
			?item rdfs:label ?itemLabel .
			FILTER(LANG(?itemLabel) = "en")
			?item ^schema:about ?article .
			?article schema:isPartOf <https://en.wikipedia.org/>.
			?article schema:name ?articlename .
		}
	} LIMIT 1"""
)

def movie_detail(request, id):
    query_result = local_g.query(detail_q, initBindings={'s': rdflib.URIRef('http://example.com/data/' + id)})

    print(len(query_result))
    for row in query_result:
        result = row
        break

    release_year = result.releasedYear
    if result.releasedDate:
        release_year = datetime.datetime.strptime(result.releasedDate, "%Y-%m-%d").year

    runtime_minutes = int(result.runtime)
    runtime = {
        'hours': runtime_minutes // 60,
        'minutes': runtime_minutes % 60,
        'total_minutes': runtime_minutes,
        'text': f"{runtime_minutes // 60} h {runtime_minutes % 60} m"
    }

    poster = re.sub(r'_U[XY]\d+.*?AL_', '_UX300_AL_', str(result.poster))

    infobox_data = [
        {
            'label': 'Release date',
            'data': result.releasedDate
        },
        {
            'label': 'Runtime',
            'data': runtime['text']
        },
        {
            'label': 'Certification',
            'data': str(result.certification)
        }
    ]

    infobox_links = [
        {
            'label': 'Wikipedia',
            'url': result.article
        },
        {
            'label': 'Wikidata',
            'url': result.item
        }
    ]

    print(infobox_data)

    context = {
        'movie_id': id,
        'movie_name': result.label,
        'release_year': release_year,
        'runtime': runtime,
        'certification': result.certification,
        'poster': poster,
        'infobox_data': infobox_data,
        'infobox_links': infobox_links,

        'result': result
    }

    return render(request, "movie-detail.html", context)