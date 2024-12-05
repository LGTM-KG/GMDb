from django.shortcuts import render
import rdflib
from rdflib.plugins.sparql import prepareQuery
import re
import datetime
import requests

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

def query_home_page(query_str, *args):
    returned_data = []
    q_data = local_g.query(INITIAL_NAMESPACES + query_str, *args)
    for row in q_data:
        poster_url = re.sub(r'_U[XY]\d+.*?AL_', '_UX300_AL_', str(row.poster))
    
        data = {
            "id": str(row.s).split('http://example.com/data/')[1],
            "entity_url": str(row.s),
            "movieName": str(row.movieName),      
            "poster": poster_url,
        }

        returned_data.append(data)
    return returned_data

def query_search(query_str, *args):
    returned_data = []
    q_data = local_g.query(INITIAL_NAMESPACES + query_str, *args)
    for row in q_data:
        poster_url = re.sub(r'_U[XY]\d+.*?AL_', '_UX300_AL_', str(row.poster))
        runtime = int(row.runtime)
        directorLabel = re.sub(r'(?<!^)(?=[A-Z])', ' ', str(row.director).split('http://example.com/data/')[1])
        directorUrl = re.sub(r'(?<!^)(?=[A-Z])', '_', str(row.director).split('http://example.com/data/')[1])
    
        data = {
            "id": str(row.s).split('http://example.com/data/')[1],
            "entity_url": str(row.s),
            "movieName": str(row.movieName),      
            "poster": poster_url,
            "imdbRating": str(row.imdbRating),
            "runtime": f"{runtime // 60} h {runtime % 60} m",
            "releasedYear": str(row.releasedYear),
            "directorLabel": directorLabel,
            "directorUrl": f"https://dbpedia.org/resource/{directorUrl}"
        }

        returned_data.append(data)
    return returned_data

def query_genre(genre):
    return query_home_page("""
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
    top_20_rating_list = query_home_page("""
    SELECT ?s ?movieName ?poster where {
        ?s rdfs:label ?movieName ;
        v:poster ?poster .
    } LIMIT 20
    """)

    # Top 20 Highest Grossing Movies
    top_20_grossing_list = query_home_page("""
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
    search_args = build_search_args(request.GET)

    if request.GET.get("q"):
        results = query_search("""
        SELECT DISTINCT ?s ?movieName ?poster ?overview ?imdbRating ?runtime ?releasedYear ?director where {
            ?s rdfs:label ?movieName ;
                v:releasedYear ?releasedYear ;
                v:runtime ?runtime ;
                v:overview ?overview ;
                v:hasFilmCrew [
                    v:hasRole v:Director ;
                    v:filmCrew ?director
                ] .
                OPTIONAL { ?s v:poster ?poster }
                OPTIONAL { ?s v:imdbScore ?imdbNode.
                ?imdbNode v:rating ?imdbRating. }
        """ + search_args.get('search_filter') + """
        }
        GROUP BY ?movieName
        """)
    else:
        results = []
        
    print(results)

    context = {
        'search_query': search_args.get('search_query'),
        'results': results
    }

    return render(request, "search.html", context)

def build_search_args(request_data):
    search_query = request_data.get("q")

    if request_data.get("searchBy") == "extended":
        search_filter = f"FILTER ( CONTAINS(lcase(?movieName), \"{search_query.lower()}\") || CONTAINS(lcase(?overview), \"{search_query.lower()}\") )"
    else:
        search_filter = f"FILTER CONTAINS(lcase(?movieName), \"{search_query.lower()}\")"
    
    return {
        'search_query': search_query,
        'search_filter': search_filter
    }

detail_q = prepareQuery(
    INITIAL_NAMESPACES + """ 
    PREFIX wikibase: <http://wikiba.se/ontology#>
    PREFIX bd: <http://www.bigdata.com/rdf#>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>

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
        OPTIONAL { ?s v:overview ?overview . }
		SERVICE <https://query.wikidata.org/sparql> {
			?item rdfs:label ?itemLabel .
			FILTER(LANG(?itemLabel) = "en")
			?item ^schema:about ?article .
			?article schema:isPartOf <https://en.wikipedia.org/>.
			?article schema:name ?articleName .
            OPTIONAL { 
                ?item wdt:P495 ?country .
                ?country rdfs:label ?countryLabel .
                FILTER(LANG(?countryLabel) = "en")
            }
            OPTIONAL { 
                ?item wdt:P364 ?originalLanguage .
                ?originalLanguage rdfs:label ?originalLanguageLabel .
                FILTER(LANG(?originalLanguageLabel) = "en")
            }
		}
	}"""
)

def movie_detail(request, id):
    query_result = local_g.query(detail_q, initBindings={'s': rdflib.URIRef('http://example.com/data/' + id)})

    print(len(query_result))
    
    result = None
    result_data = {}
    
    for var in query_result.vars:
        var_str = str(var)
        result_data[var_str] = []
    
    for row in query_result:
        if result is None:
            result = row
        for index, value in enumerate(row):
            key = query_result.vars[index]
            key_str = str(key)
            value_str = str(value)
            if value_str not in result_data[key_str]:
                result_data[key_str].append(value_str)

    print(result, result_data)

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

    # wikipedia lead
    wp_name = result_data['articleName'][0]
    # wp_lead_response = requests.get(f"https://en.wikipedia.org/w/api.php?action=parse&format=json&prop=text&section=0&formatversion=2&page={wp_name}")
    # wp_lead_data = wp_lead_response.json()
    # wp_lead = wp_lead_data['parse']['text']
    wp_lead_response = requests.get(f"https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extracts&formatversion=2&exsentences=10&exlimit=1&explaintext=1&exsectionformat=wiki&titles={wp_name}")
    wp_lead_data = wp_lead_response.json()
    wp_lead = wp_lead_data['query']['pages'][0]['extract']


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
            'data': result.certification
        },
        {
            'label': 'Country',
            'data': result_data['countryLabel']
        },
        {
            'label': 'Language',
            'data': result_data['originalLanguageLabel']
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

    print(result.overview)

    context = {
        'movie_id': id,
        'movie_name': result.label,
        'release_year': release_year,
        'runtime': runtime,
        'certification': result.certification,
        'poster': poster,
        'wp_lead': wp_lead,
        'overview': result.overview,

        'infobox_data': infobox_data,
        'infobox_links': infobox_links,
        'result': result
    }

    return render(request, "movie-detail.html", context)