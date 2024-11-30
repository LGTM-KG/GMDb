from django.shortcuts import render
from rdflib import Graph

local_g = Graph()
local_g.parse('Integrated_Movies_Triples.ttl')

# Create your views here.
def home_page(request):
    # Get Top 20 Highest Rating Movies Data
    top_20_rating_query = """
    PREFIX : <http://example.com/data/> 
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX v: <http://example.com/vocab#>

    SELECT ?movieName ?poster ?releasedYear ?rating ?numOfVotes where {
        ?s rdfs:label ?movieName ;
            v:releasedYear ?releasedYear ;
            v:poster ?poster .

        ?s v:imdbScore [
            v:rating ?rating ;
            v:numOfVotes ?numOfVotes 
        ] .
    } LIMIT 20
    """

    top_20_rating = local_g.query(top_20_rating_query)  # Execute the SPARQL query
    top_20_rating_list = []

    # Iterate over the results
    for row in top_20_rating:
        # Access variables by name from the row
        data = {
            "movieName": str(row.movieName),      
            "poster": str(row.poster),            
            "releasedYear": str(row.releasedYear)  
        }
        
        print(data)
        top_20_rating_list.append(data)

    context = {
        'top_20_rating': top_20_rating_list,
    }

    # Get Top 20 Highest Grossing Movies Data
    # Get 20 Romance Movies Data
    # Get 20 Comedy Movies Data
    # Get 20 Action Movies Data
    return render(request, "home.html", context)