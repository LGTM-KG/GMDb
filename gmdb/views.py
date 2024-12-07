from SPARQLWrapper import CSV, SPARQLWrapper, JSON
from django.shortcuts import render
import rdflib
from rdflib.plugins.sparql import prepareQuery
import re
import datetime
import requests
import humanize

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
        print(row)
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

DETAIL_NAMESPACES = INITIAL_NAMESPACES + """
    PREFIX wikibase: <http://wikiba.se/ontology#>
    PREFIX bd: <http://www.bigdata.com/rdf#>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX p: <http://www.wikidata.org/prop/>
    PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
    PREFIX ps: <http://www.wikidata.org/prop/statement/>
"""

DETAIL_Q_STR = DETAIL_NAMESPACES + """ 
    SELECT * WHERE {
		?s rdfs:label ?label .
		?s v:hasWikidata ?item .
        OPTIONAL { ?s v:poster ?poster . }
        OPTIONAL { ?s v:genre ?genre . }
        OPTIONAL { ?s v:releaseDate ?releaseDate . }
        OPTIONAL { ?s v:runtime ?runtime . }
        OPTIONAL { ?s v:releasedYear ?releasedYear . }
        OPTIONAL { ?s v:budget ?budget . }
        OPTIONAL { ?s v:certification ?certification . }
        OPTIONAL { ?s v:domesticOpening ?domesticOpening . }
        OPTIONAL { ?s v:domesticSales ?domesticSales . }
        OPTIONAL { ?s v:internationalSales ?internationalSales . }
        OPTIONAL { ?s v:worldWideSales ?worldWideSales . }
        OPTIONAL { ?s v:gross ?gross . }
        OPTIONAL {
            ?s v:metaScore ?metaScore .
        }
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
            OPTIONAL {
                ?item wdt:P344 ?cinematographer .
                ?cinematographer rdfs:label ?cinematographerLabel .
                FILTER(LANG(?cinematographerLabel) = "en")
                OPTIONAL {
                    ?cinematographer ^schema:about ?cinematographerArticle .
                    ?cinematographerArticle schema:isPartOf <https://en.wikipedia.org/>.
                }
                OPTIONAL { ?cinematographer wdt:P18 ?cinematographerImage . }
            }
            OPTIONAL {
                ?item wdt:P1040 ?editor .
                ?editor rdfs:label ?editorLabel .
                FILTER(LANG(?editorLabel) = "en")
                OPTIONAL {
                    ?editor ^schema:about ?editorArticle .
                    ?editorArticle schema:isPartOf <https://en.wikipedia.org/>.
                }
                OPTIONAL { ?editor wdt:P18 ?editorImage . }
            }
            OPTIONAL {
                ?item wdt:P86 ?composer .
                ?composer rdfs:label ?composerLabel .
                FILTER(LANG(?composerLabel) = "en")
                OPTIONAL {
                    ?composer ^schema:about ?composerArticle .
                    ?composerArticle schema:isPartOf <https://en.wikipedia.org/>.
                }
                OPTIONAL { ?composer wdt:P18 ?composerImage . }
            }
            OPTIONAL { ?item wdt:P345 ?imdbId . }
            OPTIONAL { ?item wdt:P4947 ?tmdbId . }
            OPTIONAL { ?item wdt:P12196 ?tvdbId . }
            OPTIONAL { ?item wdt:P1258 ?rottenTomatoesId . }
            OPTIONAL { ?item wdt:P6127 ?leterboxdId . }
            OPTIONAL { ?item wdt:P1712 ?metacriticId . }
		}
    }
"""

import re

# replace ?s with the given URI <uri>

# DETAIL_Q_REP = re.sub(r'\b\?s\b', '<uri>', DETAIL_Q_STR)
# with 

def prepare_query_str(query_str, uri):
    return re.sub(r'\?s\b', uri, query_str)

DETAIL_OTHER_ROLES_Q_STR = DETAIL_NAMESPACES + """
    SELECT * WHERE {
        ?s v:hasWikidata ?item .
        SERVICE <https://query.wikidata.org/sparql> {
            OPTIONAL {
                ?item wdt:P344 ?cinematographer .
                ?cinematographer rdfs:label ?cinematographerLabel .
                FILTER(LANG(?cinematographerLabel) = "en")
                OPTIONAL {
                    ?cinematographer ^schema:about ?cinematographerArticle .
                    ?cinematographerArticle schema:isPartOf <https://en.wikipedia.org/>.
                }
                OPTIONAL { ?cinematographer wdt:P18 ?cinematographerImage . }
            }
            OPTIONAL {
                ?item wdt:P1040 ?editor .
                ?editor rdfs:label ?editorLabel .
                FILTER(LANG(?editorLabel) = "en")
                OPTIONAL {
                    ?editor ^schema:about ?editorArticle .
                    ?editorArticle schema:isPartOf <https://en.wikipedia.org/>.
                }
                OPTIONAL { ?editor wdt:P18 ?editorImage . }
            }
            OPTIONAL {
                ?item wdt:P86 ?composer .
                ?composer rdfs:label ?composerLabel .
                FILTER(LANG(?composerLabel) = "en")
                OPTIONAL {
                    ?composer ^schema:about ?composerArticle .
                    ?composerArticle schema:isPartOf <https://en.wikipedia.org/>.
                }
                OPTIONAL { ?composer wdt:P18 ?composerImage . }
            }       
        }
    }
    """

# DETAIL_Q = prepareQuery(DETAIL_Q_STR + "}")

DETAIL_STAR_Q_STR = DETAIL_NAMESPACES + """
    SELECT * WHERE {
        ?s v:hasFilmCrew ?starCast .
        ?starCast v:hasRole v:Star .
        ?starCast v:filmCrew ?starCastCast .
        ?starCastCast rdfs:label ?starCastName .
    }
    """

# DETAIL_STAR_Q = prepareQuery(DETAIL_STAR_Q_STR)

DETAIL_IMDB_RATING_Q_STR = DETAIL_NAMESPACES + """
    SELECT ?imdbRating ?imdbVotes WHERE {
        ?s v:imdbScore ?imdbScore .
        ?imdbScore v:rating ?imdbRating .
        ?imdbScore v:numOfVotes ?imdbVotes .    
    }
    """

# DETAIL_IMDB_RATING_Q = prepareQuery(DETAIL_IMDB_RATING_Q_STR)

DETAIL_PRODUCER_Q_STR = DETAIL_NAMESPACES + """ 
    SELECT * WHERE {
        ?s v:hasWikidata ?item .
        SERVICE <https://query.wikidata.org/sparql> {
            OPTIONAL {
                ?item wdt:P162 ?producer .
                ?producer rdfs:label ?producerLabel .
                FILTER(LANG(?producerLabel) = "en")
                OPTIONAL {
                    ?producer ^schema:about ?producerArticle .
                    ?producerArticle schema:isPartOf <https://en.wikipedia.org/>.
                }
                OPTIONAL { ?producer wdt:P18 ?producerImage . }
            }
        }
    }
    """

DETAIL_SCREENWRITER_Q_STR = DETAIL_NAMESPACES + """ 
    SELECT * WHERE {
        ?s v:hasWikidata ?item .
        SERVICE <https://query.wikidata.org/sparql> {
            OPTIONAL {
                ?item wdt:P58 ?screenwriter .
                ?screenwriter rdfs:label ?screenwriterLabel .
                FILTER(LANG(?screenwriterLabel) = "en")
                OPTIONAL {
                    ?screenwriter ^schema:about ?screenwriterArticle .
                    ?screenwriterArticle schema:isPartOf <https://en.wikipedia.org/>.
                }
                OPTIONAL { ?screenwriter wdt:P18 ?screenwriterImage . }
            }
        }
    }
    """

DETAIL_DIRECTOR_Q_STR = DETAIL_NAMESPACES + """ 
    SELECT * WHERE {
        ?s v:hasWikidata ?item .
        SERVICE <https://query.wikidata.org/sparql> {
            OPTIONAL {
                ?item wdt:P57 ?director .
                ?director rdfs:label ?directorLabel .
                FILTER(LANG(?directorLabel) = "en")
                OPTIONAL {
                    ?director ^schema:about ?directorArticle .
                    ?directorArticle schema:isPartOf <https://en.wikipedia.org/>.
                }
                OPTIONAL { ?director wdt:P18 ?directorImage . }
            }
        }
    }
    """

DETAIL_CAST_Q_STR = DETAIL_NAMESPACES + """ 
    SELECT * WHERE {
		?s v:hasWikidata ?item .
		SERVICE <https://query.wikidata.org/sparql> {
            OPTIONAL {
                ?item p:P161 ?castStatement .
                ?castStatement ps:P161 ?cast .
                ?cast rdfs:label ?castLabel .
                FILTER(LANG(?castLabel) = "en")
                OPTIONAL {
                    ?cast ^schema:about ?castArticle .
                    ?castArticle schema:isPartOf <https://en.wikipedia.org/>.
                }
                OPTIONAL {
                    ?castStatement pq:P453 ?castCharacter .
                    ?castCharacter rdfs:label ?castCharacterLabel .
                    FILTER(LANG(?castCharacterLabel) = "en")
                }
                OPTIONAL {
                    ?item pq:P4633 ?castCharacterName .
                }
                OPTIONAL { ?cast wdt:P18 ?castImage . }
            }
		}
	}"""

DETAIL_DBPEDIA_Q_STR = INITIAL_NAMESPACES + """
    PREFIX dbo: <http://dbpedia.org/ontology/>

    SELECT * WHERE {
        SERVICE <https://dbpedia.org/sparql> {
            ?dbpediaItem foaf:isPrimaryTopicOf ?article .
            ?dbpediaItem dbo:abstract ?abstract .
            FILTER(LANG(?abstract) = "en")
        }
    } LIMIT 1
    """

DETAIL_COMPANY_Q_STR = DETAIL_NAMESPACES + """ 
    SELECT * WHERE {
		?s v:hasWikidata ?item .
		SERVICE <https://query.wikidata.org/sparql> {
            OPTIONAL {
                ?item wdt:P272 ?productionCompany .
                ?productionCompany rdfs:label ?productionCompanyLabel .
                FILTER(LANG(?productionCompanyLabel) = "en")
                OPTIONAL {
                    ?productionCompany ^schema:about ?productionCompanyArticle .
                    ?productionCompanyArticle schema:isPartOf <https://en.wikipedia.org/>.
                }
            }
            OPTIONAL {
                ?item wdt:P750 ?distributor .
                ?distributor rdfs:label ?distributorLabel .
                FILTER(LANG(?distributorLabel) = "en")
                OPTIONAL {
                    ?distributor ^schema:about ?distributorArticle .
                    ?distributorArticle schema:isPartOf <https://en.wikipedia.org/>.
                }
            }
		}
	}"""

DETAIL_STREAMING_Q_STR = DETAIL_NAMESPACES + """
    SELECT * WHERE {
        ?s v:hasWikidata ?item .
        SERVICE <https://query.wikidata.org/sparql> {
            OPTIONAL { ?item wdt:P1874 ?netflixId . }
            OPTIONAL { ?item wdt:P5749 ?amazonId . }
            OPTIONAL { ?item wdt:P9586 ?appleTvId . }
            OPTIONAL { ?item wdt:P6562 ?googlePlayId . }
            OPTIONAL { ?item wdt:P5990 ?moviesAnywhereId . }
            OPTIONAL { ?item wdt:P1651 ?youtubeId . }
            OPTIONAL { ?item wdt:P7595 ?disneyPlus . }
            OPTIONAL { ?item wdt:P11460 ?plexId . }
            OPTIONAL { ?item wdt:P8298 ?hboMaxId . }
            OPTIONAL { ?item wdt:P6466 ?huluId . }
            OPTIONAL { ?item wdt:P7970 ?fandangoNowId . }
        }
    }
    """

GROUPED_VARS = [
    ('country', 'countryLabel', 'countryArticle', 'countryArticleName'),
    ('originalLanguage', 'originalLanguageLabel', 'originalLanguageArticle', 'originalLanguageArticleName'),
    ('director', 'directorLabel', 'directorArticle', 'directorArticleName', 'directorImage'),
    ('screenwriter', 'screenwriterLabel', 'screenwriterArticle', 'screenwriterArticleName', 'screenwriterImage'),
    ('producer', 'producerLabel', 'producerArticle', 'producerArticleName', 'producerImage'),
    ('cast', 'castLabel', 'castArticle', 'castArticleName', 'castCharacterLabel', 'castCharacterName', 'castImage'),
    ('productionCompany', 'productionCompanyLabel', 'productionCompanyArticle', 'productionCompanyArticleName'),
    ('distributor', 'distributorLabel', 'distributorArticle', 'distributorArticleName'),
    ('cinematographer', 'cinematographerLabel', 'cinematographerArticle', 'cinematographerArticleName', 'cinematographerImage'),
    ('editor', 'editorLabel', 'editorArticle', 'editorArticleName', 'editorImage'),
    ('composer', 'composerLabel', 'composerArticle', 'composerArticleName'),
    ('starCast', 'starCastName', 'starCastCast'),
]

GROUPED_VARS_FLAT = [var for group in GROUPED_VARS for var in group]


def add_infobox_link(label, url, icon=None, infobox_links=[]):
    if not url:
        return
    
    data_to_add = {
        'label': label,
        'url': url,
        'icon': icon if icon else 'fa6-solid:globe'
    }

    infobox_links.append(data_to_add)

def add_streaming_data(label, urls, icon=None, color=None, theme=None, streaming_data={}):
    if not urls:
        return
    
    data_to_add = {
        'label': label,
        'urls': urls,
        'icon': icon if icon else 'fa6-solid:globe',
        'color': color if color else '',
        'theme': theme if theme else 'dark'
    }

    streaming_data.append(data_to_add)


def to_infobox_list(key, label_key, url_key=None, img_key=None, result_data={}):
    if key not in result_data:
        return []
    infobox_list_data = []
    for item in result_data[key]:
        item_data = result_data[key][item]
        data_to_add = {}
        data_to_add['label'] = item_data[label_key]
        if url_key and item_data.get(url_key):
            data_to_add['url'] = item_data[url_key]
        if img_key and item_data.get(img_key):
            data_to_add['img'] = item_data[img_key]
        infobox_list_data.append(data_to_add)
    return infobox_list_data


def movie_detail(request, id):
    result = None
    result_data = {}

    for group_var in GROUPED_VARS:
        result_data[group_var[0]] = {}

    infobox_data = []

    # Querying from local database and Wikidata
    # ────────────────────────────────────────

    query_result = query_remote(prepare_query_str(DETAIL_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data_remote(result_data, query_result)
    result = extract_and_group_results_remote(result, result_data, query_result)

    print("Query 1 done.")

    query_director_result = query_remote(prepare_query_str(DETAIL_DIRECTOR_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data_remote(result_data, query_director_result)
    extract_and_group_results_remote(result, result_data, query_director_result)

    print("Query 2 done.")

    query_screenwriter_result = query_remote(prepare_query_str(DETAIL_SCREENWRITER_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data_remote(result_data, query_screenwriter_result)
    extract_and_group_results_remote(result, result_data, query_screenwriter_result)

    print("Query 3 done.")

    query_producer_result = query_remote(prepare_query_str(DETAIL_PRODUCER_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data_remote(result_data, query_producer_result)
    extract_and_group_results_remote(result, result_data, query_producer_result)

    print("Query 4 done.")

    query_cast_result = query_remote(prepare_query_str(DETAIL_CAST_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data_remote(result_data, query_cast_result)
    extract_and_group_results_remote(result, result_data, query_cast_result)

    print("Query 5 done.")

    query_imdb_rating_result = query_remote(prepare_query_str(DETAIL_IMDB_RATING_Q_STR, f'<http://example.com/data/{id}>'))

    for row in query_imdb_rating_result['results']['bindings']:
        result_data['imdbRating'] = row['imdbRating']['value']
        result_data['imdbVotes'] = row['imdbVotes']['value']

    print("Query 6 done.")

    query_company_result = query_remote(prepare_query_str(DETAIL_COMPANY_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data_remote(result_data, query_company_result)
    extract_and_group_results_remote(result, result_data, query_company_result)

    print("Query 7 done.")

    query_star_result = query_remote(prepare_query_str(DETAIL_STAR_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data_remote(result_data, query_star_result)
    extract_and_group_results_remote(result, result_data, query_star_result)

    print("Query 8 done.")

    query_streaming_result = query_remote(prepare_query_str(DETAIL_STREAMING_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data_remote(result_data, query_streaming_result)
    extract_and_group_results_remote(result, result_data, query_streaming_result)

    print("Query 9 done.")

    query_other_roles_result = query_remote(prepare_query_str(DETAIL_OTHER_ROLES_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data_remote(result_data, query_other_roles_result)
    extract_and_group_results_remote(result, result_data, query_other_roles_result)

    print("Query 10 done.")

    # Querying from DBpedia
    # ────────────────────────────────────────

    query_dbpedia_result = query_remote(prepare_query_str(DETAIL_DBPEDIA_Q_STR, f'<http://example.com/data/{id}>'))

    for row in query_dbpedia_result['results']['bindings']:
        result_data['abstract'] = row['abstract']['value']
        break

    print("Query DBpedia done.")

    # Compiling obtained data
    # ────────────────────────────────────────

    # Release year and date

    release_year = result.get('releasedYear')
    if result.get('releaseDate'):
        release_year = datetime.datetime.strptime(result.get('releaseDate'), "%Y-%m-%d").year

    release_date = result.get('releaseDate')
    if release_date:
        release_date = datetime.datetime.strptime(release_date, "%Y-%m-%d").strftime("%d %B %Y")
    elif release_year:
        release_date = str(release_year)

    # Runtime

    if result.get('runtime'):
        runtime_minutes = int(result['runtime'])
        runtime = {
            'hours': runtime_minutes // 60,
            'minutes': runtime_minutes % 60,
            'total_minutes': runtime_minutes,
            'text': f"{runtime_minutes // 60} h {runtime_minutes % 60} m"
        }

    # Poster

    if result.get('poster'):
        poster = result['poster']
        if poster:
            poster = re.sub(r'_U[XY]\d+.*?AL_', '_UX300_AL_', poster)
            request_poster = requests.head(poster)
            if request_poster.status_code != 200:
                poster = None

    # Abstract

    # From Wikipedia
    # wp_name = result_data['articleName'][0]
    # # abstract_response = requests.get(f"https://en.wikipedia.org/w/api.php?action=parse&format=json&prop=text&section=0&formatversion=2&page={wp_name}")
    # # abstract_data = abstract_response.json()
    # # abstract = abstract_data['parse']['text']
    # abstract_response = requests.get(f"https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extracts&formatversion=2&exsentences=10&exlimit=1&explaintext=1&exsectionformat=wiki&titles={wp_name}")
    # abstract_data = abstract_response.json()
    # abstract = abstract_data['query']['pages'][0]['extract'].split(' ==')[0]
    
    abstract = result_data['abstract']
    # get first 5 sentences
    if len(abstract.split('. ')) > 5:
        abstract = '. '.join(abstract.split('. ')[:5]) + '.'

    # Countries

    countries = to_infobox_list('country', 'countryLabel', 'countryArticle', result_data=result_data)

    # Languages

    languages = to_infobox_list('originalLanguage', 'originalLanguageLabel', 'originalLanguageArticle', result_data=result_data)

    # Director

    directors = to_infobox_list('director', 'directorLabel', 'directorArticle', 'directorImage', result_data=result_data)
        
    # Screenwriter

    screenwriters = to_infobox_list('screenwriter', 'screenwriterLabel', 'screenwriterArticle', 'screenwriterImage', result_data=result_data)

    # Producer

    producers = to_infobox_list('producer', 'producerLabel', 'producerArticle', 'producerImage', result_data=result_data)

    # Cast

    casts = []

    for cast_member in result_data['cast']:
        cast_data = result_data['cast'][cast_member]
        casts.append({
            'label': cast_data.get('castLabel'),
            'url': cast_data.get('castArticle'),
            'role': cast_data.get('castCharacterLabel') or cast_data.get('castCharacterName'),
            'img': cast_data.get('castImage')
        })

    # Production company

    production_companies = to_infobox_list('productionCompany', 'productionCompanyLabel', 'productionCompanyArticle', result_data=result_data)

    # Distributor

    distributors = to_infobox_list('distributor', 'distributorLabel', 'distributorArticle', result_data=result_data)

    # Cinematorgrapher

    cinematographers = to_infobox_list('cinematographer', 'cinematographerLabel', 'cinematographerArticle', 'cinematographerImage', result_data=result_data)

    # Editor

    editors = to_infobox_list('editor', 'editorLabel', 'editorArticle', 'editorImage', result_data=result_data)

    # Composer

    composers = to_infobox_list('composer', 'composerLabel', 'composerArticle', 'composerImage', result_data=result_data)

    star_casts = []

    if 'starCast' in result_data:
        for star_cast in result_data['starCast']:
            star_cast_data = result_data['starCast'][star_cast]
            cast_data_in_wdb = next((cast_data for cast_data in casts if cast_data['label'] == star_cast_data['starCastName']), None)
            star_casts.append({
                'label': star_cast_data['starCastName'],
                'url': cast_data_in_wdb.get('url') if cast_data_in_wdb else None,
            })

    # Compiling infobox data
    # ────────────────────────────────────────

    print(result_data.get('disneyPlus'))

    streaming_data = []

    add_streaming_data('Amazon Prime Video', ['https://www.amazon.com/dp/' + x for x in result_data.get('amazonId', [])], 'simple-icons:primevideo', '#1F2E3E', 'dark', streaming_data=streaming_data)
    
    add_streaming_data('Apple TV', ['https://tv.apple.com/movie/' + x for x in result_data.get('appleTvId', [])], 'simple-icons:appletv', '#000000', 'dark', streaming_data=streaming_data)
    
    add_streaming_data('Disney+', ['https://www.disneyplus.com/movies/wd/' + str(x) for x in result_data.get('disneyPlus', [])], None, '#176678', 'dark', streaming_data=streaming_data)
    
    add_streaming_data('Fandango Now', ['https://www.fandangonow.com/details/' + x for x in result_data.get('fandangoNowId', [])], None, '#000000', 'dark', streaming_data=streaming_data)
    
    add_streaming_data('Google Play Movies', ['https://play.google.com/store/movies/details?id=' + x for x in result_data.get('googlePlayId', [])], 'simple-icons:googleplay', '#414141', 'dark', streaming_data=streaming_data)
    
    add_streaming_data('Hulu', ['https://www.hulu.com/movie/' + str(x) for x in result_data.get('huluId', [])], None, '#3bb53b', 'dark', streaming_data=streaming_data)
    
    add_streaming_data('Max', ['https://play.max.com/show/' + str(x) for x in result_data.get('hboMaxId', [])], 'simple-icons:hbo', '#000000', 'dark', streaming_data=streaming_data)
    
    add_streaming_data('Movies Anywhere', ['https://moviesanywhere.com/movie/' + x for x in result_data.get('moviesAnywhereId', [])], streaming_data=streaming_data)
    
    add_streaming_data('Netflix', ['https://www.netflix.com/title/' + str(x) for x in result_data.get('netflixId', [])], 'simple-icons:netflix', '#E50914', 'dark', streaming_data=streaming_data)
    
    add_streaming_data('Plex', ['https://app.plex.tv/desktop/#!/provider/tv.plex.provider.metadata/details?key=/library/metadata/' + x for x in result_data.get('plexId', [])], 'simple-icons:plex', '#EBAF00', 'light', streaming_data=streaming_data)
    
    add_streaming_data('YouTube', ['https://www.youtube.com/watch?v=' + x for x in result_data.get('youtubeId', [])], 'simple-icons:youtube', '#FF0000', 'dark', streaming_data=streaming_data)

    cast_data = [
        {
            'label': 'Director',
            'data': directors
        },
        {
            'label': 'Screenwriter',
            'data': screenwriters
        },
        {
            'label': 'Producer',
            'data': producers
        },
        {
            'label': 'Cinematorgrapher',
            'data': cinematographers
        },
        {
            'label': 'Editor',
            'data': editors
        },
        {
            'label': 'Composer',
            'data': composers
        },
        {
            'label': 'Cast',
            'data': casts
        }
    ]

    # if result.genre:
    if result.get('genre'):
        infobox_data.append({
            'label': 'Genre',
            # 'data': result.genre.split(',')
            'data': result['genre'].split(',')
        })

    if directors:
        infobox_data.append({
            'label': 'Directed by',
            'data': directors
        })

    if screenwriters:
        infobox_data.append({
            'label': 'Screenplay by',
            'data': screenwriters
        })

    if producers:
        infobox_data.append({
            'label': 'Producer',
            'data': producers
        })

    if star_casts:
        infobox_data.append({
            'label': 'Starring',
            'data': star_casts
        })

    if cinematographers:
        infobox_data.append({
            'label': 'Cinematography',
            'data': cinematographers
        })

    if editors:
        infobox_data.append({
            'label': 'Edited by',
            'data': editors
        })

    if composers:
        infobox_data.append({
            'label': 'Music by',
            'data': composers
        })

    if production_companies:
        infobox_data.append({
            'label': 'Production company',
            'data': production_companies
        })

    if distributors:
        infobox_data.append({
            'label': 'Distributed by',
            'data': distributors
        })

    if release_date:
        infobox_data.append({
            'label': 'Release date',
            'data': release_date
        })

    if runtime:
        infobox_data.append({
            'label': 'Runtime',
            'data': f'{runtime_minutes} minutes'
        })

    if result.get('certification'):
        infobox_data.append({
            'label': 'Certification',
            'data': result['certification']
        })

    if countries:
        infobox_data.append({
            'label': 'Country',
            'data': countries
        })

    if languages:
        infobox_data.append({
            'label': 'Language',
            'data': languages
        })

    if result.get('budget'):
        infobox_data.append({
            'label': 'Budget',
            'data': '$' + humanize.intword(result.get('budget'))
        })

    if result.get('domesticOpening'):
        infobox_data.append({
            'label': 'Domestic opening',
            'data': '$' + humanize.intword(result.get('domesticOpening'))
        })

    if result.get('domesticSales'):
        infobox_data.append({
            'label': 'Domestic sales',
            'data': '$' + humanize.intword(result.get('domesticSales'))
        })

    if result.get('internationalSales'):
        infobox_data.append({
            'label': 'International sales',
            'data': '$' + humanize.intword(result.get('internationalSales'))
        })

    if result.get('worldWideSales') or result.get('gross'):
        infobox_data.append({
            'label': 'Worldwide sales',
            'data': '$' + humanize.intword(result.get('worldWideSales') or result.get('gross'))
        })

    infobox_links = []

    add_infobox_link('Wikipedia', result.get('article'), 'simple-icons:wikipedia', infobox_links)

    add_infobox_link('Wikidata', result.get('item'), 'simple-icons:wikidata', infobox_links)

    add_infobox_link('IMDb', f"https://www.imdb.com/title/{result.get('imdbId')}", 'simple-icons:imdb', infobox_links)

    add_infobox_link('TMDB', f"https://www.themoviedb.org/movie/{result.get('tmdbId')}", 'simple-icons:themoviedatabase', infobox_links)

    add_infobox_link('TheTVDB', f"https://thetvdb.com/dereferrer/movie/{result.get('tvdbId')}", infobox_links=infobox_links)

    add_infobox_link('Rotten Tomatoes', f"https://www.rottentomatoes.com/{result.get('rottenTomatoesId')}", 'simple-icons:rottentomatoes', infobox_links)

    add_infobox_link('Letterboxd', f"https://letterboxd.com/film/{result.get('leterboxdId')}", 'simple-icons:letterboxd', infobox_links)

    add_infobox_link('Metacritic', f"https://www.metacritic.com/movie/{result.get('metacriticId')}", 'simple-icons:metacritic', infobox_links)

    subtitle = []

    if release_year:
        subtitle.append(str(release_year))

    if runtime:
        subtitle.append(runtime['text'])

    if result.get('certification'):
        subtitle.append(result['certification'])

    if result.get('genre'):
        subtitle.append(', '.join(result['genre'].split(',')))

    subtitle_text = ' · '.join(subtitle)

    context = {
        'movie_id': id,
        'movie_name': result.get('itemLabel') or result.get('label'),
        'poster': poster,
        'abstract': abstract,
        'overview': result.get('overview'),
        'rating': {
            'imdb_rating': str(result_data.get('imdbRating', '')),
            'imdb_votes': str(result_data.get('imdbVotes', '')),
            'meta_score': str(result_data.get('metaScore', [''])[0])
        },

        'infobox_data': infobox_data,
        'infobox_links': infobox_links,
        'cast_data': cast_data,
        'streaming_data': streaming_data,
        'result': result,
        'subtitle': subtitle_text
    }

    return render(request, "movie-detail.html", context)

def initialize_result_data(result_data, query_2_result):
    for var in query_2_result.vars:
        var_str = str(var)
        if var_str in result_data:
            continue
        if var_str in GROUPED_VARS_FLAT:
            continue
        result_data[var_str] = []

def extract_and_group_results(result, result_data, query_result):
    for row in query_result:
        if result is None:
            result = row
            
        pending_value_group = {}

        for index, value in enumerate(row):
            value_str = str(value) if value else None
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
    return result

# when querying from remote using sparqlwrapper
def extract_and_group_results_remote(result, result_data, query_result):
    for row in query_result['results']['bindings']:
        if result is None:
            result = {}
            
        pending_value_group = {}

        for key, value in row.items():
            value_str = value['value'] if value else None
            key_str = key

            if not key_str in result:
                result[key_str] = value_str

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
    return result

def initialize_result_data_remote(result_data, query_2_result):
    for var in query_2_result['head']['vars']:
        var_str = var
        if var_str in result_data:
            continue
        if var_str in GROUPED_VARS_FLAT:
            continue
        result_data[var_str] = []