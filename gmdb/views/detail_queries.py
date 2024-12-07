from gmdb.views import INITIAL_NAMESPACES

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
            OPTIONAL { ?item wdt:P345 ?imdbId . }
            OPTIONAL { ?item wdt:P4947 ?tmdbId . }
            OPTIONAL { ?item wdt:P12196 ?tvdbId . }
            OPTIONAL { ?item wdt:P1258 ?rottenTomatoesId . }
            OPTIONAL { ?item wdt:P6127 ?leterboxdId . }
            OPTIONAL { ?item wdt:P1712 ?metacriticId . }
		}
    }
"""
DETAIL_STAR_Q_STR = DETAIL_NAMESPACES + """
    SELECT * WHERE {
        ?s v:hasFilmCrew ?starCast .
        ?starCast v:hasRole v:Star .
        ?starCast v:filmCrew ?starCastCast .
        ?starCastCast rdfs:label ?starCastName .
    }
    """
DETAIL_IMDB_RATING_Q_STR = DETAIL_NAMESPACES + """
    SELECT ?imdbRating ?imdbVotes WHERE {
        ?s v:imdbScore ?imdbScore .
        ?imdbScore v:rating ?imdbRating .
        ?imdbScore v:numOfVotes ?imdbVotes .    
    }
    """
DETAIL_CAST_Q_STR = DETAIL_NAMESPACES + """ 
    SELECT * WHERE {
		?s v:hasWikidata ?item .
		SERVICE <https://query.wikidata.org/sparql> {
            OPTIONAL {
                # ?item p:P161 ?castStatement .
                # ?castStatement ps:P161 ?cast .
                {
                    ?item p:P161 ?castStatement .
                    ?castStatement ps:P161 ?cast .
                } UNION {
                    ?item p:P725 ?castStatement .
                    ?castStatement ps:P725 ?cast .
                }
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
# https://stackoverflow.com/questions/46383784/wikidata-get-all-properties-with-labels-and-values-of-an-item
DETAIL_CREW_Q_STR = DETAIL_NAMESPACES + """ 
    SELECT * WHERE {
        ?s v:hasWikidata ?item .
        SERVICE <https://query.wikidata.org/sparql> {
            OPTIONAL {
                ?item ?crewProperty ?crew .
            
                ?crew wdt:P31 wd:Q5 .
                ?crew rdfs:label ?crewLabel .
                FILTER(LANG(?crewLabel) = "en")

                OPTIONAL {
                ?crew ^schema:about ?crewArticle .
                ?crewArticle schema:isPartOf <https://en.wikipedia.org/>.
                }
                OPTIONAL { ?crew wdt:P18 ?crewImage . }
            
            #   OPTIONAL {
            #     ?item ?anyProp ?crewRoleStatement .
            #     ?crewRoleStatement ps:P3831 ?crewRole .  
            #   }
            
                # hint:Query hint:optimizer "None" .
                ?crewProp wikibase:directClaim ?crewProperty .
            
            #     {
            #       ?prop wdt:P1647 ?b
            #     } UNION {
            #       ?prop wdt:P1629 ?b
            #     }
                        
                {
                ?crewProp wdt:P1629 wd:Q17291399
                } UNION {
                ?crewProp wdt:P1629 wd:Q4220920
                } UNION {
                ?crewProp wdt:P1647 wd:P767
                } UNION {
                ?crewProp wdt:P1647 wd:P3092      
                }
            
                ?crewProp rdfs:label ?crewPropLabel .
                FILTER(LANG(?crewPropLabel) = "en")
            }
        }
    }
    """
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
            OPTIONAL { ?item wdt:P5885 ?microsoftStoreId . }
        }
    }
    """
GROUPED_VARS = [
    ('country', 'countryLabel', 'countryArticle', 'countryArticleName'),
    ('originalLanguage', 'originalLanguageLabel', 'originalLanguageArticle', 'originalLanguageArticleName'),
    # ('director', 'directorLabel', 'directorArticle', 'directorArticleName', 'directorImage'),
    # ('screenwriter', 'screenwriterLabel', 'screenwriterArticle', 'screenwriterArticleName', 'screenwriterImage'),
    # ('producer', 'producerLabel', 'producerArticle', 'producerArticleName', 'producerImage'),
    ('cast', 'castLabel', 'castArticle', 'castArticleName', 'castCharacterLabel', 'castCharacterName', 'castImage'),
    ('productionCompany', 'productionCompanyLabel', 'productionCompanyArticle', 'productionCompanyArticleName'),
    ('distributor', 'distributorLabel', 'distributorArticle', 'distributorArticleName'),
    # ('cinematographer', 'cinematographerLabel', 'cinematographerArticle', 'cinematographerArticleName', 'cinematographerImage'),
    # ('editor', 'editorLabel', 'editorArticle', 'editorArticleName', 'editorImage'),
    # ('composer', 'composerLabel', 'composerArticle', 'composerArticleName'),
    ('starCast', 'starCastName', 'starCastCast'),
    ('crew', 'crewLabel', 'crewArticle', 'crewArticleName', 'crewImage', 'crewLabel', 'crewProp', 'crewPropLabel'),
]
GROUPED_VARS_FLAT = [var for group in GROUPED_VARS for var in group]

CREW_PROP_MAPPING = {
    "Producer": ["P162", "P1431"],
    "Screenwriter": ["P58"],
    "Director": ["P57"],
    "Cinematographer": ["P344"],
    "Editor": ["P1040"],
    "Composer": ["P86"],
}