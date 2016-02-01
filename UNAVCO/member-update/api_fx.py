import requests
import random
import logging
import json
from time import sleep
from rdflib import Literal, Graph
from rdflib.namespace import Namespace, RDF, RDFS, XSD
import namespace as ns
from operator import itemgetter
from tabulate import tabulate
from fuzzywuzzy import fuzz, process, utils
from namespace import VIVO, VCARD, OBO, BIBO, FOAF, SKOS, D, CITO
from SPARQLWrapper import SPARQLWrapper

log = logging.getLogger(__name__)

def load_settings():
    try:
        with open('api_settings.json') as f:    
            try:
                data = json.load(f)
                return data 
            except Exception:
                logging.exception("Could not load API credentials. "
                                     "The api_settings.json file is likely "
                                     "not formatted correctly. See "
                                     "api_settings.json.example.")
                raise
    except Exception:
        logging.exception("Could not load API credentials. "
                            "Ensure your credentials and API stored "
                            "correctly in api_settings.json. See "
                            "api_settings.json.example.")
        raise


# Generic query
def vivo_api_query(query):
    data = load_settings()
    try:
        EMAIL = data["api_user"]
        PASSWORD = data["api_password"]
        API_URL = data["query_api_url"]
    except KeyError:
        logging.exception("Could not load API credentials. "
                            "Ensure your credentials and API stored "
                            "correctly in api_settings.json. See "
                            "api_settings.json.example.")
        raise RuntimeError('Update failed. See log for details.')
        
    while True:
        payload = {'email': EMAIL, 'password': PASSWORD, 'query':''+query}
        headers = {'Accept': 'application/sparql-results+json'}
        r = requests.post(API_URL,params=payload, headers=headers)
        try:
            json=r.json()
            bindings = json["results"]["bindings"]
        except ValueError:
            logging.exception("Nothing returned from query API. "
                                "Ensure your credentials and API url are set "
                                "correctly in api_fx.py.")
            bindings = None
        return bindings
        

def sparql_update(graph,operation):
    data = load_settings()
    try:
        EMAIL = data["api_user"]
        PASSWORD = data["api_password"]
        UPDATE_API_URL = data["update_api_url"]
        GRAPH = data["default_graph"]
    except KeyError:
        logging.exception("Could not load API credentials. "
                            "Ensure your credentials and API stored "
                            "correctly in api_settings.json. See "
                            "api_settings.json.example.")
        raise RuntimeError('Update failed. See log for details.')
        
    # Need to construct query
    ns_lines = []
    triple_lines = []
    for line in graph.serialize(format="turtle").splitlines():
        if line.startswith("@prefix"):
            # Change from @prefix to PREFIX
            ns_lines.append("PREFIX" + line[7:-2])
        else:
            triple_lines.append(line)
    query = "\n".join(ns_lines)
    query += "\n"+operation+" DATA { GRAPH <"+GRAPH+"> {\n"
    query += "\n".join(triple_lines)
    query += "\n}}"
    logging.debug(query)
    execute_sparql_update(query, UPDATE_API_URL, EMAIL, PASSWORD, operation)

def execute_sparql_update(query, endpoint, username, password, operation):
    """
    Perform a SPARQL Update query.
    :param query: the query to perform
    :param endpoint: the URL for SPARQL Update on the SPARQL server
    :param username: username for SPARQL Update
    :param password: password for SPARQL Update
    """
    sparql = SPARQLWrapper(endpoint)
    sparql.addParameter("email", username)
    sparql.addParameter("password", password)
    sparql.setQuery(query)
    sparql.setMethod("POST")
    sparql.query()
    logging.info('SPARQL '+operation+' successful.')

# Create unique URIs
def uri_gen(prefix):
    data = load_settings()
    try:
        EMAIL = data["api_user"]
        PASSWORD = data["api_password"]
        API_URL = data["query_api_url"]
        GRAPH = data["default_graph"]
    except KeyError:
        logging.exception("Could not load API credentials. "
                            "Ensure your credentials and API stored "
                            "correctly in api_settings.json. See "
                            "api_settings.json.example.")
        raise RuntimeError('URI generation failed. See log for details.')
        
    while True:
        vivouri = prefix + str(random.randint(100000,999999))
        payload = {'email': EMAIL, 'password': PASSWORD, 'query': 'ASK WHERE {GRAPH <'+GRAPH+'> { <'+D+vivouri+'> ?p ?o . }  }' }
        r = requests.post(API_URL,params=payload)
        exists=r.text
        
        if exists=='false':
            logging.debug('Determined that new uri '+vivouri+
                        ' does not exist in database.')
            return vivouri
            break
            
        if exists=='true':
            logging.debug('Determined that new uri '+vivouri+
                        ' already exists in database, trying again.')
                        
        else:
            logging.error('Unexpected response from VIVO Query API. Check your '
                        'credentials and API url in api_fx.py.')
            raise RuntimeError('URI generation failed. See log for details.')


def new_vcard(first_name,last_name,full_name,g):
    (author_uri,name_uri) = uri_gen('n'),uri_gen('n')
    g.add((D[author_uri], RDF.type, VCARD.Individual))
    g.add((D[author_uri], VCARD.hasName, D[name_uri]))
    g.add((D[name_uri], RDF.type, VCARD.Name))
    g.add((D[name_uri], VCARD.familyName, Literal(last_name)))
    if first_name:
        g.add((D[name_uri], VCARD.givenName, Literal(first_name)))
        #g.add((D[author_uri], RDFS.label, Literal(last_name+', '+first_name)))
    #else: g.add((D[author_uri], RDFS.label, Literal(last_name))))
    return author_uri
