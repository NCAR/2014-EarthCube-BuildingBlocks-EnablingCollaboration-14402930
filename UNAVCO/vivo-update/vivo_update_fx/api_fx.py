import requests
import random
import logging
import json
from rdflib import Literal, Graph
from rdflib.namespace import Namespace, RDF, RDFS, XSD
import namespace as ns
from namespace import VIVO, VCARD, OBO, BIBO, FOAF, SKOS, D, CITO
from SPARQLWrapper import SPARQLWrapper
from fuzzywuzzy import fuzz, process, utils
from operator import itemgetter
from tabulate import tabulate

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
def vivo_api_construct(query, g=None):
    if not g:
        g = Graph(namespace_manager=ns.ns_manager)
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


# Return the crossref metadata, given a doi
def crossref_lookup(doi):
    tries = 0
    while True:
        r = requests.get('http://api.crossref.org/works/{}'.format(doi))
        tries += 1
        if r.status_code == 404:
            logging.debug('{} not found on cross ref'.format(doi))
            # Not a crossref DOI.
            return None
        if r.status_code == 500:
            logging.debug('{} has a redirect, cant parse...'.format(doi))
            return None
        if r:
            return r.json()["message"]
        if r.status_code == 502 and tries < 6:
            logging.info('Server error, waiting 10 seconds before retry...')
            sleep(10)
        else:
            raise Exception('Request to fetch DOI {} returned {}'
                            .format(doi, r.status_code))


def grab_corpus(doi):
    API_URL = 'http://opencitations.net/sparql'
    payload = {'query': 'PREFIX datacite: <http://purl.org/spar/datacite/> '
               'PREFIX literal: '
               '<http://www.essepuntato.it/2010/06/literalreification/> '
               'PREFIX cito: <http://purl.org/spar/cito/> '
               'SELECT ?pub ?doi WHERE { ?pub_in datacite:hasIdentifier ?doi_in . '
               '?doi_in literal:hasLiteralValue "' + doi.lower() + '" . '
               '?pub_in cito:cites ?pub . '
               '?pub datacite:hasIdentifier ?doi_obj . '
               '?doi_obj literal:hasLiteralValue ?doi . '
               '?doi_obj datacite:usesIdentifierScheme	datacite:doi . } ',
               'format': 'json'}
    r = requests.get(API_URL, params=payload)
    try:
        r = r.json()
    except ValueError:
        logging.info('No response from Open Citations... ')
    bindings = r["results"]["bindings"]
    dois = []
    for bindings in bindings:
        if 'doi' in bindings:
            dois.append(bindings['doi']['value'])
    return dois


# This convenience method returns the first result from a generator
def peek(generator):
    try:
        first = next(generator)
    except StopIteration:
        return None
    return first


# Generate a list of vcard:individuals and foaf:persons with a given last name
def name_lookup(name):
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
    payload = {'email': EMAIL, 'password': PASSWORD, 'query':
               'PREFIX  vcard: <http://www.w3.org/2006/vcard/ns#> '
               'PREFIX vivo: <http://vivoweb.org/ontology/core#> '
               'SELECT ?gname ?mname ?fname ?vcardname ?vcard ?foaf '
               'WHERE { GRAPH '
               '<http://vitro.mannlib.cornell.edu/default/vitro-kb-2> {'
               '?vcard vcard:hasName ?vcardname . '
               '?vcardname vcard:givenName ?gname. '
               '?vcardname vcard:familyName ?fname . '
               'FILTER (STR(?fname)="' + name + '")'
               'OPTIONAL{'
               '?foaf <http://purl.obolibrary.org/obo/ARG_2000028> ?vcard . } '
               'OPTIONAL{?vcardname vivo:middleName ?mname .}}}'}
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(API_URL, params=payload, headers=headers)
    matched_names = r.json()

    bindings = matched_names["results"]["bindings"]
    roll = []
    for bindings in bindings:
        givenname = bindings["gname"]["value"] if "gname" in bindings else ''
        midname = bindings["mname"]["value"] if "mname" in bindings else ''
        familyname = bindings["fname"]["value"] if "fname" in bindings else ''
        familyname = bindings["fname"]["value"] if "fname" in bindings else ''
        vcard_uri = bindings["vcard"]["value"] if "vcard" in bindings else ''
        foaf_uri = bindings["foaf"]["value"] if "foaf" in bindings else ''
        preroll = []
        preroll.append(givenname)
        preroll.append(midname)
        preroll.append(familyname)
        preroll.append(vcard_uri)
        preroll.append(foaf_uri)
        roll.append(preroll)
    return roll

def name_selecter(roll, full_name, g, first_name, surname, pub_uri, matchlist,
                  rank=None):
    # if none of the possibilities are foaf, just make a new vcard
        # code
    if len(roll) > 0:  # the api found matching last names
        exit = False
        foaf = False
        scoredlist = []
        for idx, val in enumerate(roll):
            if roll[int(idx)][4]:
                (author_uri, uritype) = roll[int(idx)][4], 'foaf'
                foaf = True
            else:
                (author_uri, uritype) = roll[int(idx)][3], 'vcard'
            '''
            # Map to foaf object if it exists, otherwise vcard individual
            if roll[int(idx)][4]:
                (author_uri,uritype) = roll[int(idx)][4],'foaf'
            else:
                (author_uri,uritype) = roll[int(idx)][3],'vcard'
            '''

            author_uri = author_uri.replace(D, '')
            rollname = (roll[idx][0] + ' ' + roll[idx][1] + ' ' + roll[idx][2]
                        if roll[idx][1] else roll[idx][0] + ' ' + roll[idx][2])
            try:  # Weird character encoding things going on hur
                full_name.decode('ascii')
                fuzzy_name = None
            except UnicodeEncodeError:
                fuzzy_name = utils.full_process(full_name, force_ascii=True)
            if len(roll[idx][0]) > 2:  # Don't bother scoring against initials
                fuzznum = (fuzz.ratio(rollname, fuzzy_name) if fuzzy_name else
                           fuzz.ratio(rollname, full_name))
            #    raw_input(rollname+' vs. '+full_name+str(fuzznum))
                if fuzznum == 100:
                    matchlist = assign_authorship(author_uri, g, pub_uri,
                                                  full_name, matchlist, rank)
                    return matchlist
                scoredlist.append([roll[idx][0], roll[idx][1], roll[idx][2],
                                  author_uri, uritype, fuzznum])
            else:
                scoredlist.append([roll[idx][0], roll[idx][1], roll[idx][2],
                                  author_uri, uritype, None])
        if foaf is True:
            scoredlist = sorted(scoredlist, key=itemgetter(5), reverse=True)
            for idx, val in enumerate(scoredlist):
                # Add a handy index number for display
                scoredlist[idx].insert(0, idx)
                if scoredlist[idx][6] is None:
                    scoredlist[idx][6] = '-'  # Add a hash for prettiness
            print(tabulate(scoredlist, headers=['num', 'first', 'middle',
                                                'last', 'uri', 'type',
                                                'score']))
            if fuzzy_name:
                pick = raw_input("\nAuthor " + fuzzy_name + " may already "
                                 "exist in the database. Please choose a "
                                 "number or press Enter for none ")
            else:
                pick = raw_input("\nAuthor " + full_name+" may already exist "
                                 "in the database. Please choose a number or "
                                 "press Enter for none ")

            while True:
                if pick == '':  # None of the above
                    # Create a new vcard individual
                    author_uri = new_vcard(first_name, surname, full_name, g)
                    matchlist = assign_authorship(author_uri, g, pub_uri,
                                                  full_name, matchlist, rank)
                    break
                elif pick == 'RDF':
                    print(g.serialize(format='turtle'))
                    raw_input('\nYou found the RDF easter egg, look at you! '
                              'Press Enter to continue\n')
                    # Temporary testing shortcut
                    print(tabulate(scoredlist, headers=['num', 'first',
                                                        'middle', 'last',
                                                        'uri', 'score']))
                    pick = raw_input("\nAuthor " + full_name + " may already "
                                     "exist in the database. Please choose a "
                                     "number or press Enter for none ")
                elif pick.isdigit():
                    if int(pick) < len(roll):  # Make sure the number is valid
                        author_uri = scoredlist[int(pick)][4]
                        matchlist = assign_authorship(author_uri, g, pub_uri,
                                                      full_name, matchlist,
                                                      rank)
                        break
                    else:  # Number out of range
                        pick = raw_input('invalid input, try again ')

                else:  # Either not a number or not empty
                    pick = raw_input('invalid input, try again ')
            return matchlist
        else:
            # No matches, make new uri
            author_uri = new_vcard(first_name, surname, full_name, g)
            matchlist = assign_authorship(author_uri, g, pub_uri, full_name,
                                          matchlist, rank)
            return matchlist

    else:
        # No matches, make new uri
        author_uri = new_vcard(first_name, surname, full_name, g)
        matchlist = assign_authorship(author_uri, g, pub_uri, full_name,
                                      matchlist, rank)
        return matchlist


def assign_authorship(author_id, g, pub_uri, full_name, matchlist, rank=None):
    authorship_uri = uri_gen('n')
    g.add((D[author_id], VIVO.relatedBy, D[authorship_uri]))
    g.add((D[pub_uri], VIVO.relatedBy, D[authorship_uri]))
    g.add((D[authorship_uri], RDF.type, VIVO.Authorship))
    g.add((D[authorship_uri], VIVO.relates, D[author_id]))
    g.add((D[authorship_uri], VIVO.relates, D[pub_uri]))
    if rank:
        g.add((D[authorship_uri], VIVO.rank,
              Literal('%d' % rank, datatype=XSD.int)))
    matchlist[0].append(full_name)
    matchlist[1].append(author_id)
    return matchlist


# Return a list of all the datasets in vivo
# TODO include the uris in the list to save time
def get_datasets_in_vivo():
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
    payload = {'email': EMAIL, 'password': PASSWORD,
               'query': 'SELECT ?dataset ?doi WHERE {  ?dataset a '
               '<http://vivoweb.org/ontology/core#Dataset> . ?dataset '
               '<http://purl.org/ontology/bibo/doi> ?doi.}'}
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(API_URL, params=payload, headers=headers)
    data = r.json()
    bindings = data["results"]["bindings"]
    if bindings:
        datasets = [[], []]
        for dataset in bindings:
            doi = dataset["dataset"]["value"].replace(D, '')
            uri = dataset["doi"]["value"]
            datasets[0].append(uri)
            datasets[1].append(doi)
        return datasets