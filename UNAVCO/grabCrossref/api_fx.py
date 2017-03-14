import requests
import random
from time import sleep
from rdflib import Literal, Graph
from rdflib.namespace import Namespace, RDF, RDFS, XSD
import namespace
from operator import itemgetter
from tabulate import tabulate
from fuzzywuzzy import fuzz, process, utils
from namespace import VIVO, VCARD, OBO, BIBO, FOAF, SKOS, D, CITO
import json
import logging
from urllib import quote_plus

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


# Create unique URIs
def uri_gen(prefix, graph=None):
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
        raise RuntimeError('Update failed. See log for details.')
    while True:
        vivouri = prefix + str(random.randint(100000, 999999))
        payload = {'email': EMAIL, 'password': PASSWORD, 'query':
                   'ASK WHERE {GRAPH <'+GRAPH+'> { <' + D + vivouri +
                   '> ?p ?o . }  }'}
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


# Determine if a doi exists in the VIVO database
def uri_lookup_doi(doi):
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
        raise RuntimeError('Update failed. See log for details.')
    bib = BIBO
    payload = {'email': EMAIL, 'password': PASSWORD, 'query': 'SELECT ?uri '
               'WHERE {GRAPH <'+GRAPH+'> { ?uri <' + bib + 'doi' +
               '> ?doi. '
               'FILTER(lcase(str(?doi)) = "'+doi+'") . }  }'}
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(API_URL, params=payload, headers=headers)

    uri_found = r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        rel_uri = bindings[0]["uri"]["value"] if "uri" in bindings[0] else None
        return rel_uri


# Generate a list of vcard:individuals and foaf:persons with a given last name
def name_lookup(name):
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
        raise RuntimeError('Update failed. See log for details.')
    payload = {'email': EMAIL, 'password': PASSWORD, 'query': 'SELECT ?gname '
               '?mname ?fname ?vcardname ?vcard ?foaf WHERE { GRAPH <' +
               GRAPH + '> {?vcard <http://www.w3.org/2006/vcard/ns#hasName> '
               '?vcardname .  ?vcardname '
               '<http://www.w3.org/2006/vcard/ns#givenName> ?gname.  '
               '?vcardname <http://www.w3.org/2006/vcard/ns#familyName> '
               '?fname . FILTER (STR(?fname)="'+name+'") '
               'OPTIONAL{?foaf <http://purl.obolibrary.org/obo/ARG_2000028> '
               '?vcard . }OPTIONAL{?vcardname '
               '<http://vivoweb.org/ontology/core#middleName> ?mname .}}}'}
    headers = {'Accept': 'application/sparql-results+json'}
    # print payload
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


# Return the crossref metadata, given a doi
def crossref_lookup(doi):
    tries = 0
    while True:
        r = requests.get('http://api.crossref.org/works/{}'.format(doi))
        tries += 1
        if r.status_code == 404:
            print 'doi not found on cross ref'
            # Not a crossref DOI.
            return None
        if r:
            return r.json()["message"]
        if r.status_code == 502 and tries < 6:
            print 'Server error, waiting 10 seconds before retry...'
            sleep(10)
        else:
            raise Exception('Request to fetch DOI {} returned {}'
                            .format(doi, r.status_code))


# This crazy function will match an author with a vcard or person if its
# an exact match, otherwise it will ask for help
def name_selecter(roll, full_name, g, first_name, surname, pub_uri, matchlist,
                  rank=None):
    if len(roll) > 0: # The api found matching last names
        exit = False
        scoredlist = []
        for idx, val in enumerate(roll):
            if roll[int(idx)][4]:
                (author_uri, uritype) = roll[int(idx)][4], 'foaf'
            else:
                (author_uri, uritype) = roll[int(idx)][3], 'vcard'
#            (author_uri,uritype) = roll[int(idx)][4],'foaf' if roll[int(idx)][4] else roll[int(idx)][3],'vcard' #map to foaf object if it exists, otherwise vcard individual
            author_uri = author_uri.replace(D, '')
            rollname = roll[idx][0]+' '+roll[idx][1]+' '+roll[idx][2] if roll[idx][1] else roll[idx][0]+' '+roll[idx][2]
            try: # Weird character encoding things going on hur
                full_name.decode('ascii')
                fuzzy_name = None
            except UnicodeEncodeError:
                fuzzy_name = utils.full_process(full_name, force_ascii=True)
            if len(roll[idx][0]) > 2: # Don't bother scoring against initials
                fuzznum = fuzz.ratio(rollname, fuzzy_name) if fuzzy_name else fuzz.ratio(rollname, full_name)
            #    raw_input(rollname+' vs. '+full_name+str(fuzznum))
                if fuzznum == 100:
                    matchlist = assign_authorship(author_uri, g, pub_uri, full_name, matchlist, rank)
                    return matchlist
                scoredlist.append([roll[idx][0], roll[idx][1], roll[idx][2], author_uri, uritype, fuzznum])
            else:
                scoredlist.append([roll[idx][0], roll[idx][1], roll[idx][2], author_uri, uritype, None])
        scoredlist = sorted(scoredlist, key=itemgetter(5), reverse=True)
        for idx, val in enumerate(scoredlist):
            # Add a handy index number for display
            scoredlist[idx].insert(0, idx)
            # Add a hash for prettiness
            if scoredlist[idx][6] == None: scoredlist[idx][6]='-'
        print tabulate(scoredlist, headers=['num', 'first', 'middle', 'last', 'uri', 'type', 'score'])
        pick = raw_input("\nAuthor "+fuzzy_name+" may already exist in the database. Please choose a number or press Enter for none ") if fuzzy_name else raw_input("\nAuthor "+full_name+" may already exist in the database. Please choose a number or press Enter for none ")

        while True:
            if pick == '': # None of the above
                # Create a new vcard individual
                author_uri = new_vcard(first_name, surname, full_name, g)
                matchlist = assign_authorship(author_uri, g, pub_uri, full_name, matchlist, rank)
                break
            elif pick == 'RDF':
                print g.serialize(format='turtle')
                raw_input('\nYou found the RDF easter egg, look at you! Press Enter to continue\n')
                print tabulate(scoredlist, headers=['num', 'first', 'middle', 'last', 'uri', 'score']) # Temporary testing shortcut
                pick = raw_input("\nAuthor "+full_name+" may already exist in the database. Please choose a number or press Enter for none ")
            elif pick.isdigit():
                if int(pick) < len(roll): # Make sure the number is valid
                    author_uri = scoredlist[int(pick)][4]
                    matchlist = assign_authorship(author_uri, g, pub_uri, full_name, matchlist, rank)
                    break
                else:
                    pick = raw_input('invalid input, try again ') # Number out of range

            else:
                pick = raw_input('invalid input, try again ') # Either not a number or not empty
        return matchlist

    else:
        # No matches, make new uri
        author_uri = new_vcard(first_name, surname, full_name, g)
        matchlist = assign_authorship(author_uri, g, pub_uri, full_name,
                                      matchlist, rank)
        return matchlist


def new_vcard(first_name, last_name, full_name, g):
    (author_uri, name_uri) = uri_gen('per', g), uri_gen('n', g)
    g.add((D[author_uri], RDF.type, VCARD.Individual))
    g.add((D[author_uri], VCARD.hasName, D[name_uri]))
    g.add((D[name_uri], RDF.type, VCARD.Name))
    g.add((D[name_uri], VCARD.familyName, Literal(last_name)))
    if first_name:
        g.add((D[name_uri], VCARD.givenName, Literal(first_name)))
    return author_uri


def assign_authorship(author_id, g, pub_uri, full_name, matchlist, rank=None):
    authorship_uri = uri_gen('n', g)
    g.add((D[author_id], VIVO.relatedBy, D[authorship_uri]))
    g.add((D[authorship_uri], RDF.type, VIVO.Authorship))
    g.add((D[authorship_uri], VIVO.relates, D[author_id]))
    g.add((D[authorship_uri], VIVO.relates, D[pub_uri]))
    g.add((D[pub_uri], VIVO.relatedBy, D[authorship_uri]))
    if rank:
        g.add((D[authorship_uri], VIVO.rank, Literal('%d' % rank,
              datatype=XSD.int)))
    matchlist[0].append(full_name)
    matchlist[1].append(author_id)
    return matchlist


# Lookup URI for a given subject
def get_subject(concept, g):
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
    payload = {'email': EMAIL, 'password': PASSWORD, 'query': 'SELECT '
               '?suburi WHERE { ?suburi '
               '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
               '<http://www.w3.org/2004/02/skos/core#Concept> . ?suburi '
               '<http://www.w3.org/2000/01/rdf-schema#label> "'+concept+'". }'}
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(API_URL, params=payload, headers=headers)
    uri_found = r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        for bindings in bindings:
            if "suburi" in bindings:
                sub_uri = bindings["suburi"]["value"]
            else:
                sub_uri = None
            return sub_uri


def get_publishers():
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

    payload = {'email': EMAIL, 'password': PASSWORD, 'query':
               'SELECT ?publisher ?publisherLabel WHERE { ?publisher '
               '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
               '<http://vivoweb.org/ontology/core#Publisher> . ?publisher '
               '<http://www.w3.org/2000/01/rdf-schema#label> ?publisherLabel '
               '. } '}
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(API_URL, params=payload, headers=headers)
    uri_found = r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        publishers = {}
        for bindings in bindings:
            if 'publisher' in bindings:
                publishers[bindings['publisherLabel']['value']] = \
                                    bindings['publisher']['value']
            else:
                publishers[bindings['publisherLabel']['value']] = None
        return publishers


def get_journals():
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
    payload = {'email': EMAIL, 'password': PASSWORD, 'query':
               'SELECT ?journal ?journalLabel WHERE { ?journal '
               '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
               '<http://purl.org/ontology/bibo/Journal> . ?journal '
               '<http://www.w3.org/2000/01/rdf-schema#label> ?journalLabel '
               '. } '}
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(API_URL, params=payload, headers=headers).json()
    bindings = r["results"]["bindings"]
    if bindings:
        journals = {}
        for bindings in bindings:
            if 'journal' in bindings:
                journals[bindings['journalLabel']['value']] = \
                                    bindings['journal']['value']
        return journals
