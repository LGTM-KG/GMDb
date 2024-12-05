from django.shortcuts import render
import rdflib
from rdflib.plugins.sparql import prepareQuery
import re
import datetime
import requests
import humanize

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
        if row.director:
            directorLabel = re.sub(r'(?<!^)(?=[A-Z])', ' ', str(row.director).split('http://example.com/data/')[1])
            directorUrl = re.sub(r'(?<!^)(?=[A-Z])', '_', str(row.director).split('http://example.com/data/')[1])
        else:
            directorLabel = "Unknown"
            directorUrl = "Unknown"
    
        data = {
            "id": str(row.s).split('http://example.com/data/')[1],
            "entity_url": str(row.s),
            "movieName": str(row.movieName),      
            "poster": poster_url,
            "imdbRating": str(row.imdbRating) if row.imdbRating else "N/A",
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
        GROUP BY ?movieName
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


DETAIL_Q = prepareQuery(
    DETAIL_NAMESPACES + """ 
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
            }
            OPTIONAL {
                ?item wdt:P1040 ?editor .
                ?editor rdfs:label ?editorLabel .
                FILTER(LANG(?editorLabel) = "en")
                OPTIONAL {
                    ?editor ^schema:about ?editorArticle .
                    ?editorArticle schema:isPartOf <https://en.wikipedia.org/>.
                }
            }
            OPTIONAL {
                ?item wdt:P86 ?composer .
                ?composer rdfs:label ?composerLabel .
                FILTER(LANG(?composerLabel) = "en")
                OPTIONAL {
                    ?composer ^schema:about ?composerArticle .
                    ?composerArticle schema:isPartOf <https://en.wikipedia.org/>.
                }
            }
            OPTIONAL { ?item wdt:P345 ?imdbId . }
            OPTIONAL { ?item wdt:P4947 ?tmdbId . }
            OPTIONAL { ?item wdt:P12196 ?tvdbId . }
            OPTIONAL { ?item wdt:P1258 ?rottenTomatoesId . }
            OPTIONAL { ?item wdt:P6127 ?leterboxdId . }
            OPTIONAL { ?item wdt:P1712 ?metacriticId . }
		}
	}"""
)

DETAIL_STAR_Q = prepareQuery(
    DETAIL_NAMESPACES + """
    SELECT * WHERE {
        ?s v:hasFilmCrew ?starCast .
        ?starCast v:hasRole v:Star .
        ?starCast v:filmCrew ?starCastCast .
        ?starCastCast rdfs:label ?starCastName .
    }
    """
)

        
DETAIL_IMDB_RATING_Q = prepareQuery(
    DETAIL_NAMESPACES + """
    SELECT ?imdbRating ?imdbVotes WHERE {
        ?s v:imdbScore ?imdbScore .
        ?imdbScore v:rating ?imdbRating .
        ?imdbScore v:numOfVotes ?imdbVotes .    
    }
    """
)

DETAIL_PRODUCER_Q = prepareQuery(
    DETAIL_NAMESPACES + """ 
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
)

DETAIL_SCREENWRITER_Q = prepareQuery(
    DETAIL_NAMESPACES + """ 
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
)

DETAIL_DIRECTOR_Q = prepareQuery(
    DETAIL_NAMESPACES + """ 
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
)

DETAIL_CAST_Q = prepareQuery(
    DETAIL_NAMESPACES + """ 
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

DETAIL_COMPANY_Q = prepareQuery(
    DETAIL_NAMESPACES + """ 
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
)

DETAIL_STREAMING_Q = prepareQuery(
    DETAIL_NAMESPACES + """
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
)

GROUPED_VARS = [
    ('country', 'countryLabel', 'countryArticle', 'countryArticleName'),
    ('originalLanguage', 'originalLanguageLabel', 'originalLanguageArticle', 'originalLanguageArticleName'),
    ('director', 'directorLabel', 'directorArticle', 'directorArticleName', 'directorImage'),
    ('screenwriter', 'screenwriterLabel', 'screenwriterArticle', 'screenwriterArticleName', 'screenwriterImage'),
    ('producer', 'producerLabel', 'producerArticle', 'producerArticleName', 'producerImage'),
    ('cast', 'castLabel', 'castArticle', 'castArticleName', 'castCharacterLabel', 'castCharacterName', 'castImage'),
    ('productionCompany', 'productionCompanyLabel', 'productionCompanyArticle', 'productionCompanyArticleName'),
    ('distributor', 'distributorLabel', 'distributorArticle', 'distributorArticleName'),
    ('cinematographer', 'cinematographerLabel', 'cinematographerArticle', 'cinematographerArticleName'),
    ('editor', 'editorLabel', 'editorArticle', 'editorArticleName'),
    ('composer', 'composerLabel', 'composerArticle', 'composerArticleName'),
    ('starCast', 'starCastName', 'starCastCast'),
]

GROUPED_VARS_FLAT = [var for group in GROUPED_VARS for var in group]

def movie_detail(request, id):
    result = None
    result_data = {}

    for group_var in GROUPED_VARS:
        result_data[group_var[0]] = {}

    infobox_data = []

    # Querying from local database and Wikidata
    # ────────────────────────────────────────

    query_result = local_g.query(DETAIL_Q, initBindings={'s': rdflib.URIRef('http://example.com/data/' + id)})

    initialize_result_data(result_data, query_result)
    result = extract_and_group_results(result, result_data, query_result)

    print("Query 1 done.")

    query_director_result = local_g.query(DETAIL_DIRECTOR_Q, initBindings={'s': rdflib.URIRef('http://example.com/data/' + id)})

    initialize_result_data(result_data, query_director_result)
    extract_and_group_results(result, result_data, query_director_result)

    print("Query 2 done.")

    query_screenwriter_result = local_g.query(DETAIL_SCREENWRITER_Q, initBindings={'s': rdflib.URIRef('http://example.com/data/' + id)})

    initialize_result_data(result_data, query_screenwriter_result)
    extract_and_group_results(result, result_data, query_screenwriter_result)

    print("Query 3 done.")

    query_producer_result = local_g.query(DETAIL_PRODUCER_Q, initBindings={'s': rdflib.URIRef('http://example.com/data/' + id)})

    initialize_result_data(result_data, query_producer_result)
    extract_and_group_results(result, result_data, query_producer_result)

    print("Query 4 done.")
    
    query_cast_result = local_g.query(DETAIL_CAST_Q, initBindings={'s': rdflib.URIRef('http://example.com/data/' + id)})

    initialize_result_data(result_data, query_cast_result)
    extract_and_group_results(result, result_data, query_cast_result)

    print("Query 5 done.")

    query_imdb_rating_result = local_g.query(DETAIL_IMDB_RATING_Q, initBindings={'s': rdflib.URIRef('http://example.com/data/' + id)})

    for row in query_imdb_rating_result:
        result_data['imdbRating'] = row.imdbRating
        result_data['imdbVotes'] = row.imdbVotes

    print("Query 6 done.")

    query_company_result = local_g.query(DETAIL_COMPANY_Q, initBindings={'s': rdflib.URIRef('http://example.com/data/' + id)})

    initialize_result_data(result_data, query_company_result)
    extract_and_group_results(result, result_data, query_company_result)

    print("Query 7 done.")

    query_star_result = local_g.query(DETAIL_STAR_Q, initBindings={'s': rdflib.URIRef('http://example.com/data/' + id)})

    initialize_result_data(result_data, query_star_result)
    extract_and_group_results(result, result_data, query_star_result)

    print("Query 8 done.")

    query_streaming_result = local_g.query(DETAIL_STREAMING_Q, initBindings={'s': rdflib.URIRef('http://example.com/data/' + id)})

    initialize_result_data(result_data, query_streaming_result)
    extract_and_group_results(result, result_data, query_streaming_result)

    print("Query 9 done.")

    # Querying from DBpedia
    # ────────────────────────────────────────

    query_dbpedia_result = local_g.query(DETAIL_DBPEDIA_Q, initBindings={'article': rdflib.URIRef(result.article.replace('https', 'http'))})

    for row in query_dbpedia_result:
        result_data['abstract'] = row.abstract

    print("Query DBpedia done.")

    # Compiling obtained data
    # ────────────────────────────────────────

    # Release year and date

    release_year = result.releasedYear
    if result.releaseDate:
        release_year = datetime.datetime.strptime(result.releaseDate, "%Y-%m-%d").year

    release_date = result.releaseDate
    if release_date:
        release_date = datetime.datetime.strptime(release_date, "%Y-%m-%d").strftime("%d %B %Y")
    elif release_year:
        release_date = str(release_year)

    # Runtime

    runtime_minutes = int(result.runtime)
    runtime = {
        'hours': runtime_minutes // 60,
        'minutes': runtime_minutes % 60,
        'total_minutes': runtime_minutes,
        'text': f"{runtime_minutes // 60} h {runtime_minutes % 60} m"
    }

    # Poster

    if result.poster:
        poster = re.sub(r'_U[XY]\d+.*?AL_', '_UX300_AL_', str(result.poster))
        request_poster = requests.head(poster)
        if request_poster.status_code != 200:
            poster = None
    else:
        poster = None

    # Abstract

    # wikipedia lead
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

    countries = []

    for country in result_data['country']:
        country_data = result_data['country'][country]
        countries.append({
            'label': country_data['countryLabel'],
            'url': country_data['countryArticle']
        })

    # Languages

    languages = []

    for language in result_data['originalLanguage']:
        language_data = result_data['originalLanguage'][language]
        languages.append({
            'label': language_data['originalLanguageLabel'],
            'url': language_data['originalLanguageArticle']
        })

    # Director

    directors = []

    for director in result_data['director']:
        director_data = result_data['director'][director]
        directors.append({
            'label': director_data['directorLabel'],
            'url': director_data['directorArticle'],
            'img': director_data['directorImage']
        })
        
    # Screenwriter

    screenwriters = []

    for screenwriter in result_data['screenwriter']:
        screenwriter_data = result_data['screenwriter'][screenwriter]
        screenwriters.append({
            'label': screenwriter_data['screenwriterLabel'],
            'url': screenwriter_data['screenwriterArticle'],
            'img': screenwriter_data['screenwriterImage']
        })

    # Producer

    producers = []

    for producer in result_data['producer']:
        producer_data = result_data['producer'][producer]
        producers.append({
            'label': producer_data['producerLabel'],
            'url': producer_data['producerArticle'],
            'img': producer_data['producerImage'] if producer_data['producerImage'] and producer_data['producerImage'] != None else None
        })

    # Cast

    casts = []

    for cast_member in result_data['cast']:
        cast_data = result_data['cast'][cast_member]
        casts.append({
            'label': cast_data['castLabel'],
            'url': cast_data['castArticle'],
            'role': cast_data['castCharacterLabel'] or cast_data['castCharacterName'],
            'img': cast_data['castImage']
        })

    # Production company

    production_companies = []

    for production_company in result_data['productionCompany']:
        production_company_data = result_data['productionCompany'][production_company]
        production_companies.append({
            'label': production_company_data['productionCompanyLabel'],
            'url': production_company_data['productionCompanyArticle']
        })

    # Distributor

    distributors = []

    for distributor in result_data['distributor']:
        distributor_data = result_data['distributor'][distributor]
        distributors.append({
            'label': distributor_data['distributorLabel'],
            'url': distributor_data['distributorArticle']
        })

    # Cinematorgrapher

    cinematographers = []

    for cinematographer in result_data['cinematographer']:
        cinematographer_data = result_data['cinematographer'][cinematographer]
        cinematographers.append({
            'label': cinematographer_data['cinematographerLabel'],
            'url': cinematographer_data['cinematographerArticle']
        })

    # Editor

    editors = []

    for editor in result_data['editor']:
        editor_data = result_data['editor'][editor]
        editors.append({
            'label': editor_data['editorLabel'],
            'url': editor_data['editorArticle']
        })

    # Composer

    composers = []

    for composer in result_data['composer']:
        composer_data = result_data['composer'][composer]
        composers.append({
            'label': composer_data['composerLabel'],
            'url': composer_data['composerArticle']
        })

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

    streaming_data = [
        {
            'label': 'Netflix',
            'urls': ['https://www.netflix.com/title/' + str(x) for x in result_data['netflixId']] if next(filter(lambda x: x, result_data.get('netflixId')), None) else [],
            'icon': 'simple-icons:netflix',
            'color': '#E50914',
            'theme': 'dark'
        },
        {
            'label': 'Amazon Prime Video',
            'id': result_data['amazonId'],
            'urls': ['https://www.amazon.com/dp/' + x for x in result_data['amazonId']] if next(filter(lambda x: x, result_data.get('amazonId')), None) else [],
            'icon': 'simple-icons:primevideo',
            'color': '#1F2E3E',
            'theme': 'dark'
        },
        {
            'label': 'Apple TV',
            'id': result_data['appleTvId'],
            'urls': ['https://tv.apple.com/movie/' + x for x in result_data['appleTvId']] if next(filter(lambda x: x, result_data.get('appleTvId')), None) else [],
            'icon': 'simple-icons:appletv',
            'color': '#000000',
            'theme': 'dark'
        },
        {
            'label': 'Google Play Movies',
            'id': result_data['googlePlayId'],
            'urls': ['https://play.google.com/store/movies/details?id=' + x for x in result_data['googlePlayId']] if next(filter(lambda x: x, result_data.get('googlePlayId')), None) else [],
            'icon': 'simple-icons:googleplay',
            'color': '#414141',
            'theme': 'dark'
        },
        {
            'label': 'Movies Anywhere',
            'id': result_data['moviesAnywhereId'],
            'urls': ['https://moviesanywhere.com/movie/' + x for x in result_data['moviesAnywhereId']] if next(filter(lambda x: x, result_data.get('moviesAnywhereId')), None) else [],
            'color': '#FFFFFF',
            'theme': 'light'
        },
        {
            'label': 'YouTube',
            'id': result_data['youtubeId'],
            'urls': ['https://www.youtube.com/watch?v=' + x for x in result_data['youtubeId']] if next(filter(lambda x: x, result_data.get('youtubeId')), None) else [],
            'icon': 'simple-icons:youtube',
            'color': '#FF0000',
            'theme': 'dark'
        },
        {
            'label': 'Disney+',
            'id': result_data['disneyPlus'],
            'urls': ['https://www.disneyplus.com/movies/wd/' + str(x) for x in result_data['disneyPlus']] if next(filter(lambda x: x, result_data.get('disneyPlus')), None) else [],
            'color': '#176678',
            'theme': 'dark'
        },
        {
            'label': 'Plex',
            'id': result_data['plexId'],
            'urls': ['https://app.plex.tv/desktop/#!/provider/tv.plex.provider.metadata/details?key=/library/metadata/' + x for x in result_data['plexId']] if next(filter(lambda x: x, result_data.get('plexId')), None) else [],
            'icon': 'simple-icons:plex',
            'color': '#EBAF00',
            'theme': 'light'
        },
        {
            'label': 'Max',
            'id': result_data['hboMaxId'],
            'urls': ['https://play.max.com/show/' + str(x) for x in result_data['hboMaxId']] if next(filter(lambda x: x, result_data.get('hboMaxId')), None) else [],
            'icon': 'simple-icons:hbo',
            'color': '#000000',
            'theme': 'dark'
        },
        {
            'label': 'Hulu',
            'id': result_data['huluId'],
            'urls': ['https://www.hulu.com/movie/' + str(x) for x in result_data['huluId']] if next(filter(lambda x: x, result_data.get('huluId')), None) else [],
            'color': '#3bb53b',
            'theme': 'dark'
        },
        {
            'label': 'Fandango Now',
            'id': result_data['fandangoNowId'],
            'urls': ['https://www.fandangonow.com/details/' + x for x in result_data['fandangoNowId']] if next(filter(lambda x: x, result_data.get('fandangoNowId')), None) else [],
            'color': '#000000',
            'theme': 'dark'
        }
    ]

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

    if result.genre:
        infobox_data.append({
            'label': 'Genre',
            'data': result.genre.split(',')
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

    if result.certification:
        infobox_data.append({
            'label': 'Certification',
            'data': result.certification
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

    if result.budget:
        infobox_data.append({
            'label': 'Budget',
            'data': '$' + humanize.intword(result.budget)
        })

    if result.domesticOpening:
        infobox_data.append({
            'label': 'Domestic opening',
            'data': '$' + humanize.intword(result.domesticOpening)
        })

    if result.domesticSales:
        infobox_data.append({
            'label': 'Domestic sales',
            'data': '$' + humanize.intword(result.domesticSales)
        })

    if result.internationalSales:
        infobox_data.append({
            'label': 'International sales',
            'data': '$' + humanize.intword(result.internationalSales)
        })

    if result.worldWideSales or result.gross:
        infobox_data.append({
            'label': 'Worldwide sales',
            'data': '$' + humanize.intword(result.worldWideSales or result.gross)
        })


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

    if result.leterboxdId:
        infobox_links.append({
            'icon': 'simple-icons:letterboxd',
            'label': 'Letterboxd',
            'url': f"https://letterboxd.com/film/{result.leterboxdId}"
        })

    if result.metacriticId:
        infobox_links.append({
            'icon': 'simple-icons:metacritic',
            'label': 'Metacritic',
            'url': f"https://www.metacritic.com/movie/{result.metacriticId}"
        })

    context = {
        'movie_id': id,
        'movie_name': result.itemLabel or result.label,
        'release_year': release_year,
        'runtime': runtime,
        'certification': result.certification,
        'poster': poster,
        'abstract': abstract,
        'overview': result.overview,
        'rating': {
            'imdb_rating': str(result_data.get('imdbRating', '')),
            'imdb_votes': str(result_data.get('imdbVotes', '')),
            'meta_score': str(result_data.get('metaScore', [''])[0])
        },
        'genre': result.genre.split(',') if result.genre else [],
        'infobox_data': infobox_data,
        'infobox_links': infobox_links,
        'cast_data': cast_data,
        'streaming_data': streaming_data,
        'result': result
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