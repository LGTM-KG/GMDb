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

DETAIL_Q = prepareQuery(
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
                ?country ^schema:about ?countryArticle .
                ?countryArticle schema:isPartOf <https://en.wikipedia.org/>.
            }
            OPTIONAL { 
                ?item wdt:P364 ?originalLanguage .
                ?originalLanguage rdfs:label ?originalLanguageLabel .
                FILTER(LANG(?originalLanguageLabel) = "en")
                ?originalLanguage ^schema:about ?originalLanguageArticle .
                ?originalLanguageArticle schema:isPartOf <https://en.wikipedia.org/>.
            }
            OPTIONAL { ?item wdt:P345 ?imdbId . }
            OPTIONAL { ?item wdt:P4947 ?tmdbId . }
            OPTIONAL { ?item wdt:P12196 ?tvdbId . }
            OPTIONAL { ?item wdt:P1258 ?rottenTomatoesId . }
		}
	}"""
)

DETAIL_DBPEDIA_Q = prepareQuery(
    INITIAL_NAMESPACES + """
    PREFIX dbo: <http://dbpedia.org/ontology/>

    SELECT * WHERE {
        SERVICE <https://dbpedia.org/sparql> {
            ?dbpediaItem foaf:isPrimaryTopicOf ?article .
            ?dbpediaItem dbo:abstract ?abstract .
            FILTER(LANG(?abstract) = "en")
        }
    } LIMIT 1
    """
)

GROUPED_VARS = [
    ('country', 'countryLabel', 'countryArticle', 'countryArticleName'),
    ('originalLanguage', 'originalLanguageLabel', 'originalLanguageArticle', 'originalLanguageArticleName')
]

GROUPED_VARS_FLAT = [var for group in GROUPED_VARS for var in group]

def movie_detail(request, id):
    query_result = local_g.query(DETAIL_Q, initBindings={'s': rdflib.URIRef('http://example.com/data/' + id)})
    
    result = None
    result_data = {}
    
    for var in query_result.vars:
        var_str = str(var)
        if var_str not in GROUPED_VARS_FLAT:
            result_data[var_str] = []
    
    for group_var in GROUPED_VARS:
        result_data[group_var[0]] = {}

    for row in query_result:
        if result is None:
            result = row
            
        pending_value_group = {}

        for index, value in enumerate(row):
            value_str = str(value)
            key = query_result.vars[index]
            key_str = str(key)

            # find group_var that has key_str
            group_var = next((group_var for group_var in GROUPED_VARS if key_str in group_var), None)

            if group_var:
                if group_var not in pending_value_group:
                    pending_value_group[group_var] = {}
                pending_value_group[group_var][key_str] = value_str
            else:
                if value_str not in result_data[key_str]:
                    result_data[key_str].append(value_str)

        for group_var, group_value in pending_value_group.items():
            group_var_key = group_var[0]
            group_value_key = group_value[group_var_key]

            if group_var_key not in result_data:
                result_data[group_var_key] = dict()

            if group_value_key not in result_data[group_var_key]:
                result_data[group_var_key][group_value_key] = group_value

    query_dbpedia_result = local_g.query(DETAIL_DBPEDIA_Q, initBindings={'article': rdflib.URIRef(result.article.replace('https', 'http'))})
    print(rdflib.URIRef(result.article.replace('https', 'http')))
    print(len(query_dbpedia_result))

    for row in query_dbpedia_result:
        result_data['abstract'] = row.abstract

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
    # wp_name = result_data['articleName'][0]
    # # abstract_response = requests.get(f"https://en.wikipedia.org/w/api.php?action=parse&format=json&prop=text&section=0&formatversion=2&page={wp_name}")
    # # abstract_data = abstract_response.json()
    # # abstract = abstract_data['parse']['text']
    # abstract_response = requests.get(f"https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extracts&formatversion=2&exsentences=10&exlimit=1&explaintext=1&exsectionformat=wiki&titles={wp_name}")
    # abstract_data = abstract_response.json()
    # abstract = abstract_data['query']['pages'][0]['extract'].split(' ==')[0]
    abstract = result_data['abstract']

    countries = []

    for country in result_data['country']:
        country_data = result_data['country'][country]
        countries.append({
            'label': country_data['countryLabel'],
            'url': country_data['countryArticle']
        })

    languages = []

    for language in result_data['originalLanguage']:
        language_data = result_data['originalLanguage'][language]
        languages.append({
            'label': language_data['originalLanguageLabel'],
            'url': language_data['originalLanguageArticle']
        })

    infobox_data = [
        {
            'label': 'Release date',
            'data': result.releasedDate or release_year
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
            'data': countries
        },
        {
            'label': 'Language',
            'data': languages
        }
    ]

    infobox_links = [
        {
            'icon': 'simple-icons:wikipedia',
            'label': 'Wikipedia',
            'url': result.article
        },
        {
            'icon': 'simple-icons:wikidata',
            'label': 'Wikidata',
            'url': result.item
        }
    ]

    if result.imdbId:
        infobox_links.append({
            'icon': 'simple-icons:imdb',
            'label': 'IMDb',
            'url': f"https://www.imdb.com/title/{result.imdbId}"
        })

    if result.tmdbId:
        infobox_links.append({
            'icon': 'simple-icons:themoviedatabase',
            'label': 'TMDB',
            'url': f"https://www.themoviedb.org/movie/{result.tmdbId}"
        })

    if result.tvdbId:
        infobox_links.append({
            'label': 'TheTVDB',
            'url': f"https://thetvdb.com/dereferrer/movie/{result.tvdbId}"
        })

    if result.rottenTomatoesId:
        infobox_links.append({
            'icon': 'simple-icons:rottentomatoes',
            'label': 'Rotten Tomatoes',
            'url': f"https://www.rottentomatoes.com/{result.rottenTomatoesId}"
        })

    print(result.overview)

    # check if poster is available
    request_poster = requests.head(poster)
    if request_poster.status_code != 200:
        poster = None

    context = {
        'movie_id': id,
        'movie_name': result.itemLabel or result.label,
        'release_year': release_year,
        'runtime': runtime,
        'certification': result.certification,
        'poster': poster,
        'abstract': abstract,
        'overview': result.overview,

        'infobox_data': infobox_data,
        'infobox_links': infobox_links,
        'result': result
    }

    return render(request, "movie-detail.html", context)