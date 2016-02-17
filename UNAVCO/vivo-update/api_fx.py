import requests
import random
import logging
import json
from rdflib import Literal, Graph
from rdflib.namespace import Namespace, RDF, RDFS, XSD
import namespace as ns
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
        payload = {'email': EMAIL, 'password': PASSWORD, 'query': ''+query}
        headers = {'Accept': 'application/sparql-results+json'}
        r = requests.post(API_URL, params=payload, headers=headers)
        try:
            json = r.json()
            bindings = json["results"]["bindings"]
        except ValueError:
            logging.exception(query)
            logging.exception("Nothing returned from query API. "
                              "Ensure your credentials and API url are set "
                              "correctly in api_fx.py.")
            bindings = None
        return bindings


# Generic CONSTRUCT query
def vivo_api_construct(query, g):
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
        payload = {'email': EMAIL, 'password': PASSWORD, 'query': ''+query}
        headers = {'Accept': 'text/turtle'}
        r = requests.post(API_URL, params=payload, headers=headers)
        try:
            g.parse(data=r.text, format='turtle')
        except ValueError:
            logging.exception(query)
            logging.exception("CONSTRUCT query to VIVO api failed.  "
                              "Ensure your credentials and API url are set "
                              "correctly in api_fx.py.")
        return g


def sparql_update(graph, operation):
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

    query = " ".join(ns_lines)
    query += " "+operation+" DATA { GRAPH <"+GRAPH+"> { "
    query += " ".join(x.decode('utf-8') for x in triple_lines)
    query += " }}"
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
    logging.info('Starting SPARQL '+operation+'. Attempting to post to Update '
                 'API at '+endpoint)
    sparql = SPARQLWrapper(endpoint)
    sparql.addParameter("email", username)
    sparql.addParameter("password", password)
    sparql.setQuery(query)
    sparql.setMethod("POST")
    sparql.query()
    logging.info('SPARQL '+operation+' successful.')


# Create unique URIs
def uri_gen(prefix, graph=None):
    data = load_settings()
    try:
        EMAIL = data["api_user"]
        PASSWORD = data["api_password"]
        API_URL = data["query_api_url"]
        DEFAULT_GRAPH = data["default_graph"]
    except KeyError:
        logging.exception("Could not load API credentials. "
                          "Ensure your credentials and API stored "
                          "correctly in api_settings.json. See "
                          "api_settings.json.example.")
        raise RuntimeError('URI generation failed. See log for details.')

    while True:
        vivouri = prefix + str(random.randint(100000, 999999))
        payload = {'email': EMAIL, 'password': PASSWORD, 'query': 'ASK WHERE '
                   '{GRAPH <'+DEFAULT_GRAPH+'> { <'+D+vivouri+'> ?p ?o . }  }'}
        r = requests.post(API_URL, params=payload)
        exists = r.text

        if graph:
            for s, p, o in graph:
                if (D[vivouri], p, o) in graph:
                    exists = 'true'
                    logging.info('Determined that new uri ' + vivouri +
                                 'already exists in local database, trying '
                                 'again.')

        if exists == 'false':
            logging.debug('Determined that new uri ' + vivouri +
                          ' does not exist in database.')
            return vivouri
            break

        if exists == 'true':
            logging.debug('Determined that new uri ' + vivouri +
                          ' already exists in database, trying again.')

        else:
            logging.error('Unexpected response from VIVO Query API. Check '
                          'your credentials and API url in api_fx.py.')
            raise RuntimeError('URI generation failed. See log for details.')


def new_vcard(first_name, last_name, full_name, g):
    (author_uri, name_uri) = uri_gen('n'), uri_gen('n')
    g.add((D[author_uri], RDF.type, VCARD.Individual))
    g.add((D[author_uri], VCARD.hasName, D[name_uri]))
    g.add((D[name_uri], RDF.type, VCARD.Name))
    g.add((D[name_uri], VCARD.familyName, Literal(last_name)))
    if first_name:
        g.add((D[name_uri], VCARD.givenName, Literal(first_name)))
    return author_uri


def call_nsf_api(keyword, datestart, offset=0, rpp=25):
    while True:
        API_URL = 'http://api.nsf.gov/services/v1/awards.json'
        payload = {'rpp': rpp, 'keyword': keyword, 'printFields': 'rpp,offset,'
                   'id,agency,awardeeCity,awardeeCountryCode,awardeeCounty,'
                   'awardeeDistrictCode,awardeeName,awardeeStateCode,'
                   'awardeeZipCode,cfdaNumber,coPDPI,date,startDate,expDate,'
                   'estimatedTotalAmt,fundsObligatedAmt,dunsNumber,'
                   'fundProgramName,parentDunsNumber,pdPIName,perfCity,'
                   'perfCountryCode,perfCounty,perfDistrictCode,perfLocation,'
                   'perfStateCode,perfZipCode,poName,primaryProgram,transType,'
                   'title,awardee,poPhone,poEmail,awardeeAddress,perfAddress,'
                   'publicationResearch,publicationConference,fundAgencyCode,'
                   'awardAgencyCode,projectOutComesReport,abstractText,'
                   'piFirstName,piMiddeInitial,piLastName,piPhone,piEmail',
                   'dateStart': datestart, 'offset': offset}

        r = requests.post(API_URL, params=payload)
        try:
            json = r.json()
            bindings = json["response"]["award"]

        except ValueError:
            logging.exception(payload)
            logging.exception("Nothing returned from query API. "
                              "Ensure your credentials and API url are set "
                              "correctly in api_fx.py.")

            bindings = None
        return bindings
