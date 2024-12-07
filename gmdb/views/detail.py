import datetime
import re

import humanize
import requests
from django.shortcuts import render

from gmdb.views import query_remote
from gmdb.views.detail_queries import DETAIL_EXEC_PRODUCER_Q_STR, DETAIL_OTHER_CREW_Q_STR, DETAIL_Q_STR, prepare_query_str, DETAIL_OTHER_ROLES_Q_STR, DETAIL_STAR_Q_STR, DETAIL_IMDB_RATING_Q_STR, DETAIL_PRODUCER_Q_STR, DETAIL_SCREENWRITER_Q_STR, DETAIL_DIRECTOR_Q_STR, DETAIL_CAST_Q_STR, DETAIL_VA_Q_STR, DETAIL_DBPEDIA_Q_STR, DETAIL_COMPANY_Q_STR, DETAIL_STREAMING_Q_STR, GROUPED_VARS
from gmdb.views.detail_utils import add_infobox_link, add_streaming_data, to_infobox_list, extract_and_group_results, initialize_result_data


def movie_detail(request, id):
    result = None
    result_data = {}

    for group_var in GROUPED_VARS:
        result_data[group_var[0]] = {}

    infobox_data = []

    # Querying from local database and Wikidata
    # ────────────────────────────────────────

    query_result = query_remote(prepare_query_str(DETAIL_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data(result_data, query_result)
    result = extract_and_group_results(result, result_data, query_result)

    print("Query 1 done.")

    query_director_result = query_remote(prepare_query_str(DETAIL_DIRECTOR_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data(result_data, query_director_result)
    extract_and_group_results(result, result_data, query_director_result)

    print("Query 2 done.")

    query_screenwriter_result = query_remote(prepare_query_str(DETAIL_SCREENWRITER_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data(result_data, query_screenwriter_result)
    extract_and_group_results(result, result_data, query_screenwriter_result)

    print("Query 3 done.")

    query_producer_result = query_remote(prepare_query_str(DETAIL_PRODUCER_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data(result_data, query_producer_result)
    extract_and_group_results(result, result_data, query_producer_result)

    print("Query 4 done.")

    query_cast_result = query_remote(prepare_query_str(DETAIL_CAST_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data(result_data, query_cast_result)
    extract_and_group_results(result, result_data, query_cast_result)

    print("Query 5 done.")

    query_imdb_rating_result = query_remote(prepare_query_str(DETAIL_IMDB_RATING_Q_STR, f'<http://example.com/data/{id}>'))

    for row in query_imdb_rating_result['results']['bindings']:
        result_data['imdbRating'] = row['imdbRating']['value']
        result_data['imdbVotes'] = row['imdbVotes']['value']

    print("Query 6 done.")

    query_company_result = query_remote(prepare_query_str(DETAIL_COMPANY_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data(result_data, query_company_result)
    extract_and_group_results(result, result_data, query_company_result)

    print("Query 7 done.")

    query_star_result = query_remote(prepare_query_str(DETAIL_STAR_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data(result_data, query_star_result)
    extract_and_group_results(result, result_data, query_star_result)

    print("Query 8 done.")

    query_streaming_result = query_remote(prepare_query_str(DETAIL_STREAMING_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data(result_data, query_streaming_result)
    extract_and_group_results(result, result_data, query_streaming_result)

    print("Query 9 done.")

    query_other_roles_result = query_remote(prepare_query_str(DETAIL_OTHER_ROLES_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data(result_data, query_other_roles_result)
    extract_and_group_results(result, result_data, query_other_roles_result)

    print("Query 10 done.")

    query_va_result = query_remote(prepare_query_str(DETAIL_VA_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data(result_data, query_va_result)
    extract_and_group_results(result, result_data, query_va_result)

    print("Query 11 done.")

    query_va_result = query_remote(prepare_query_str(DETAIL_EXEC_PRODUCER_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data(result_data, query_va_result)
    extract_and_group_results(result, result_data, query_va_result)

    print("Query 12 done.")

    query_all_crew_result = query_remote(prepare_query_str(DETAIL_OTHER_CREW_Q_STR, f'<http://example.com/data/{id}>'))

    initialize_result_data(result_data, query_all_crew_result)
    extract_and_group_results(result, result_data, query_all_crew_result)
 

    # Querying from DBpedia
    # ────────────────────────────────────────

    # query_dbpedia_result = local_g.query(DETAIL_DBPEDIA_Q, initBindings={'article': rdflib.URIRef(result.article.replace('https', 'http'))})
    query_dbpedia_result = query_remote(prepare_query_str(DETAIL_DBPEDIA_Q_STR, '<' + result['article'].replace('https', 'http') + '>', 'article'))

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

    runtime = None
    runtime_minutes = {}
    if result.get('runtime'):
        runtime_minutes = int(result['runtime'])
        runtime = {
            'hours': runtime_minutes // 60,
            'minutes': runtime_minutes % 60,
            'total_minutes': runtime_minutes,
            'text': f"{runtime_minutes // 60} h {runtime_minutes % 60} m"
        }

    # Poster

    poster = None
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
            'id': cast_data.get('cast'),
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

    # Compiled

    cast_data = []

    if directors:
        cast_data.append({
            'label': 'Director',
            'data': directors
        })

    if screenwriters:
        cast_data.append({
            'label': 'Screenwriter',
            'data': screenwriters
        })

    if producers:
        cast_data.append({
            'label': 'Producer',
            'data': producers
        })

    if cinematographers:
        cast_data.append({
            'label': 'Cinematography',
            'data': cinematographers
        })

    if editors:
        cast_data.append({
            'label': 'Editor',
            'data': editors
        })

    if composers:
        cast_data.append({
            'label': 'Composer',
            'data': composers
        })

    if casts:
        cast_data.append({
            'label': 'Cast',
            'data': casts
        })
        
    # Other crew

    existed_crew_ids = []

    for cast_section in cast_data:
        for crew in cast_section['data']:
            existed_crew_ids.append(crew['id'])

    other_crew = []

    for crew in result_data['crew']:
        if crew in existed_crew_ids:
            continue

        crew_data = result_data['crew'][crew]
        other_crew.append({
            'id': crew_data['crew'],
            'label': crew_data['crewLabel'],
            'url': crew_data.get('crewArticle'),
            'role': crew_data.get('crewPropLabel'),
            'img': crew_data.get('crewImage')
        })

    other_crew = sorted(other_crew, key=lambda x: (x['img'] is None, x['role'], x['label']))
    
    if other_crew:
        cast_data.append({
            'label': 'Other crew',
            'data': other_crew
        })

    # Star cast

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

    streaming_data = []

    add_streaming_data('Amazon Prime Video', ['https://www.amazon.com/dp/' + x for x in result_data.get('amazonId', [])], 'simple-icons:primevideo', '#1F2E3E', 'dark', streaming_data=streaming_data)

    add_streaming_data('Apple TV', ['https://tv.apple.com/movie/' + x for x in result_data.get('appleTvId', [])], 'simple-icons:appletv', '#000000', 'dark', streaming_data=streaming_data)

    add_streaming_data('Disney+', ['https://www.disneyplus.com/movies/wd/' + str(x) for x in result_data.get('disneyPlus', [])], 'cbi:disney-plus', '#176678', 'dark', streaming_data=streaming_data)

    add_streaming_data('Fandango Now', ['https://www.fandangonow.com/details/' + x for x in result_data.get('fandangoNowId', [])], None, '#000000', 'dark', streaming_data=streaming_data)

    add_streaming_data('Google Play Movies', ['https://play.google.com/store/movies/details?id=' + x for x in result_data.get('googlePlayId', [])], 'simple-icons:googleplay', '#414141', 'dark', streaming_data=streaming_data)

    add_streaming_data('Hulu', ['https://www.hulu.com/movie/' + str(x) for x in result_data.get('huluId', [])], None, '#3bb53b', 'dark', streaming_data=streaming_data)

    add_streaming_data('Max', ['https://play.max.com/show/' + str(x) for x in result_data.get('hboMaxId', [])], 'simple-icons:hbo', '#000000', 'dark', streaming_data=streaming_data)

    add_streaming_data('Microsoft Store', ['https://apps.microsoft.com/detail/' + x for x in result_data.get('microsoftStoreId', [])], 'simple-icons:microsoft', streaming_data=streaming_data)

    add_streaming_data('Movies Anywhere', ['https://moviesanywhere.com/movie/' + x for x in result_data.get('moviesAnywhereId', [])], streaming_data=streaming_data)

    add_streaming_data('Netflix', ['https://www.netflix.com/title/' + str(x) for x in result_data.get('netflixId', [])], 'simple-icons:netflix', '#E50914', 'dark', streaming_data=streaming_data)

    add_streaming_data('Plex', ['https://app.plex.tv/desktop/#!/provider/tv.plex.provider.metadata/details?key=/library/metadata/' + x for x in result_data.get('plexId', [])], 'simple-icons:plex', '#EBAF00', 'light', streaming_data=streaming_data)

    add_streaming_data('YouTube', ['https://www.youtube.com/watch?v=' + x for x in result_data.get('youtubeId', [])], 'simple-icons:youtube', '#FF0000', 'dark', streaming_data=streaming_data)

    if result.get('genre'):
        infobox_data.append({
            'label': 'Genre',
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

    add_infobox_link('Metacritic', f"https://www.metacritic.com/{result.get('metacriticId')}", 'simple-icons:metacritic', infobox_links)

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

    rating_obj = {}

    if result_data.get('imdbRating'):
        rating_obj['imdbRating'] = result_data['imdbRating']

    if result_data.get('imdbVotes'):
        rating_obj['imdbVotes'] = result_data['imdbVotes']

    if result_data.get('metaScore'):
        rating_obj['metaScore'] = result_data['metaScore'][0]

    context = {
        'movie_id': id,
        'movie_name': result.get('itemLabel') or result.get('label'),
        'poster': poster,
        'abstract': abstract,
        'overview': result.get('overview'),
        'rating': rating_obj,

        'infobox_data': infobox_data,
        'infobox_links': infobox_links,
        'cast_data': cast_data,
        'streaming_data': streaming_data,
        'result': result,
        'subtitle': subtitle_text
    }

    return render(request, "detail.html", context)


