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
import urllib2
import json
import sys
import logging
from SPARQLWrapper import SPARQLWrapper

log = logging.getLogger(__name__)


# API info
email = 'email'
password = 'password'
api_url = 'api_url'
aboxgraph = 'http://vitro.mannlib.cornell.edu/default/vitro-kb-2'
namespace = 'http://connect.unavco.org/individual/'


def load_settings():
    try:
        with open('../api_settings.json') as f:
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
def uri_gen(prefix):
    while True:
        vivouri = prefix + str(random.randint(100000, 999999))
        payload = {'email': email, 'password': password, 'query':
                   'ASK WHERE {GRAPH <' + aboxgraph + '> { <' + D + vivouri +
                   '> ?p ?o . }  }'}
        r = requests.post(api_url, params=payload)
        exists = r.text
        if exists == 'false':
            return vivouri
            break

        if exists not in ('true', 'false'):
            sys.exit("VIVO API error! Script is aborting.\nVerify your API "
                     "info in vivo_uri.py file.")


# URI check
def uri_check(uri):
    while True:
        payload = {'email': email, 'password': password, 'query': 'ASK WHERE '
                   '{GRAPH <'+aboxgraph+'> { <'+D+uri+'> ?p ?o . }  }'}
        r = requests.post(api_url, params=payload)
        exists = r.text
        if exists not in ('true', 'false'):
            sys.exit("VIVO API error! Script is aborting.\nVerify your API "
                     "info in vivo_uri.py file.")
        return exists


# List of all vCards and foaf objects
def person_check():
    while True:
        payload = {'email': email, 'password': password, 'query': 'PREFIX '
                   'foaf: <' + FOAF + '> PREFIX vcard: <' + VCARD +
                   '> SELECT ?s WHERE {{ GRAPH <' + aboxgraph + '> {  ?s a '
                   'foaf:Person . } . } UNION {?s a vcard:Individual .}}'}
        headers = {'Accept': 'application/sparql-results+json'}
        r = requests.post(api_url, params=payload, headers=headers)
        data = r.json()
        bindings = data["results"]["bindings"]

        if bindings:
            uri_list = []
            for per_record in bindings:
                uri = per_record['s']['value'] if "s" in per_record else None
                if uri:
                    uri_list.append(uri.replace(D, ''))
            return uri_list
        else:
            return None


# URI type check
def type_check(uri):
    while True:
        payload = {'email': email, 'password': password, 'query': 'SELECT ?o'
                   ' WHERE {GRAPH <' + aboxgraph + '> { <' + D + uri + '>'
                   ' <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?o .}}'}
        headers = {'Accept': 'application/sparql-results+json'}
        r = requests.post(api_url, params=payload, headers=headers)
        data = r.json()
        bindings = data["results"]["bindings"]
        if bindings:
            if "o" in bindings[0]:
                uri_type = bindings[0]["o"]["value"]
            else:
                uri_type = None
            return uri_type
        else:
            return None


def uri_lookup_doi(doi):
    """Determine if a doi exists in the VIVO database

    Args:
        doi: the doi to look up in VIVO.
    Returns:
        the uri corresponding to the doi.

    """
    payload = {'email': email, 'password': password,
               'query': 'SELECT ?uri WHERE {GRAPH <' + aboxgraph +
               '> { ?uri <http://purl.org/ontology/bibo/doi> ?doi.'
               'FILTER(lcase(str(?doi)) = "' + doi + '") . }  }'}
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url, params=payload, headers=headers)

    uri_found = r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        rel_uri = bindings[0]["uri"]["value"] if "uri" in bindings[0] else None
        return rel_uri


# Return a list of all the datasets in vivo
# TODO include the uris in the list to save time
def get_datasets_in_vivo():
    payload = {'email': email, 'password': password,
               'query': 'SELECT ?dataset ?doi WHERE {  ?dataset a '
               '<http://vivoweb.org/ontology/core#Dataset> . ?dataset '
               '<http://purl.org/ontology/bibo/doi> ?doi.}'}
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url, params=payload, headers=headers)
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


# Generate a list of vcard:individuals and foaf:persons with a given last name
def name_lookup(name):
    payload = {'email': email, 'password': password, 'query':
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
    r = requests.post(api_url, params=payload, headers=headers)
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


def datacite_lookup(doi):
    tries = 0
    payload = {'wt': 'json', 'indent': 'true', 'q': doi}
    api_url = 'http://search.datacite.org/api'

    while True:
        r = requests.post(api_url, params=payload)

        tries += 1
        if r.status_code == 404:
            print('doi not found on cross ref')
            # Not a crossref DOI.
            return None
        if r:
            return r.json()["response"]["docs"][0]
        if r.status_code == 502 and tries < 6:
            print('Server error, waiting 10 seconds before retry...')
            sleep(10)
        else:
            raise Exception("Request to fetch DOI %s returned %s" % (doi,
                            r.status_code))


# Return the crossref metadata, given a doi
def crossref_lookup(doi):
    tries = 0
    while True:
        r = requests.get('http://api.crossref.org/works/%s' % doi)
        tries += 1
        if r.status_code == 404:
            print('doi not found on cross ref')
            # Not a crossref DOI.
            return None
        if r:
            return r.json()["message"]
        if r.status_code == 502 and tries < 6:
            print('Server error, waiting 10 seconds before retry...')
            sleep(10)
        else:
            raise Exception("Request to fetch DOI %s returned %s" % (doi,
                            r.status_code))


'''
# Return the metadata, given a doi -- updated 2015-11-12 to use content
# negotiation TODO make this work or forget it
def crossref_lookup(doi):
    tries=0
    api_uri = 'http://dx.doi.org/%s' % doi

    while True:
        opener = urllib2.build_opener()
        opener.addheaders = [('Accept',
                              'application/vnd.citationstyles.csl+json')]
        r = opener.open(api_uri)
        status_code = r.getcode()


        tries+=1
        if status_code == 404:
            print 'doi not found on cross ref'
            #Not a crossref DOI.
            return None
        if r:
            r = json.loads(r.read())
            return r
        if status_code==502 and tries<6:
            print 'Server error, waiting 10 seconds before retry...'
            sleep(10)
        else:
            raise Exception("Request to fetch DOI %s returned %s" % (doi,
                            status_code))
'''


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


# This crazy function will match an author with a vcard or person if its an
# exact match, otherwise it will ask for help
def name_selecter_old(roll, full_name, g, first_name, surname, pub_uri,
                      matchlist, rank=None):
    if len(roll) > 0:  # The api found matching last names
        exit = False
        scoredlist = []
        for idx, val in enumerate(roll):
            if roll[int(idx)][4]:
                (author_uri, uritype) = roll[int(idx)][4], 'foaf'
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
            if roll[idx][1]:
                rollname = (roll[idx][0] + ' ' + roll[idx][1] + ' ' +
                            roll[idx][2])
            else:
                rollname = roll[idx][0] + ' ' + roll[idx][2]
            try:  # Weird character encoding things going on hur
                full_name.decode('ascii')
                fuzzy_name = None
            except UnicodeEncodeError:
                fuzzy_name = utils.full_process(full_name, force_ascii=True)
            if len(roll[idx][0]) > 2:  # Don't bother scoring against initials
                if fuzzy_name:
                    fuzznum = fuzz.ratio(rollname, fuzzy_name)
                else:
                    fuzznum = fuzz.ratio(rollname, full_name)
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
        scoredlist = sorted(scoredlist, key=itemgetter(5), reverse=True)

        # Only display the list if one of the options is a foaf:person
        # otherwise just make another vcard
        for sublist in scoredlist:
            pick = ''
            if 'foaf' in sublist:
                for idx, val in enumerate(scoredlist):
                    # Add a handy index number for display
                    scoredlist[idx].insert(0, idx)
                    # Add a hash for prettiness
                    if scoredlist[idx][6] is None:
                        scoredlist[idx][6] = '-'
                print(tabulate(scoredlist, headers=['num', 'first', 'middle',
                                                    'last', 'uri', 'type',
                                                    'score']))
                if fuzzy_name:
                    pick = raw_input("\nAuthor " + fuzzy_name + " may already "
                                     " exist in the database. Please choose a "
                                     "number or press Enter for none ")
                else:
                    pick = raw_input("\nAuthor " + full_name + " may already "
                                     "exist in the database. Please choose a "
                                     "number or press Enter for none ")
                break

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
                print(tabulate(scoredlist, headers=['num', 'first', 'middle',
                               'last', 'uri', 'score']))
                pick = raw_input("\nAuthor " + full_name + " may already exist"
                                 " in the database. Please choose a number or "
                                 "press Enter for none ")
            elif pick.isdigit():
                if int(pick) < len(roll):  # Make sure the number is valid
                    author_uri = scoredlist[int(pick)][4]
                    matchlist = assign_authorship(author_uri, g, pub_uri,
                                                  full_name, matchlist, rank)
                    break
                else:
                    # Number out of range
                    pick = raw_input('invalid input, try again ')

            else:
                # Either not a number or not empty
                pick = raw_input('invalid input, try again ')
        return matchlist

    else:
        # No matches, make new uri
        author_uri = new_vcard(first_name, surname, full_name, g)
        matchlist = assign_authorship(author_uri, g, pub_uri, full_name,
                                      matchlist, rank)
        return matchlist


def new_vcard(first_name, last_name, full_name, g):
    (author_uri, name_uri) = uri_gen('per'), uri_gen('n')
    g.add((D[author_uri], RDF.type, VCARD.Individual))
    g.add((D[author_uri], VCARD.hasName, D[name_uri]))
    g.add((D[name_uri], RDF.type, VCARD.Name))
    g.add((D[name_uri], VCARD.familyName, Literal(last_name)))
    if first_name:
        g.add((D[name_uri], VCARD.givenName, Literal(first_name)))
        # g.add(D[author_uri], RDFS.label, Literal(last_name+', '+first_name))
    # VIVO doesn't like labels on vcards anymore
    # else: g.add((D[author_uri], RDFS.label, Literal(last_name)))
    return author_uri


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


# TEMPORARY!!!!!!
def temp_delrb(rel_uri, g):
    payload = {'email': email, 'password': password, 'query': 'SELECT ?rbper '
               '?something WHERE {  <'+rel_uri+'> '
               '<http://vivoweb.org/ontology/core#relatedBy> ?auth . ?auth '
               '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
               '<http://vivoweb.org/ontology/core#Authorship> . ?auth '
               '<http://vivoweb.org/ontology/core#relates> ?rbper . ?rbper '
               '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>  '
               '<http://www.w3.org/2006/vcard/ns#Individual> . ?rbper '
               '<http://vivoweb.org/ontology/core#relates> ?something . } '}
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url, params=payload, headers=headers)
    uri_found = r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        for bindings in bindings:
            if "something" in bindings:
                rel_uri = bindings["something"]["value"]
            else:
                rel_uri = None
            if "rbper" in bindings:
                rel_rb = bindings["rbper"]["value"]
            else:
                rel_rb = None
            if rel_uri and rel_rb:
                print('<'+rel_rb + '> '
                      '<http://vivoweb.org/ontology/core#relates> <' +
                      rel_uri + '> .')


def data_cite():
    r = requests.post('http://search.datacite.org/api?q=UNAVCO&fl=doi,creator'
                      ',title,publisher,publicationYear,datacentre&fq=is_acti'
                      've:true&fq=has_metadata:true&rows=500&wt=json&indent='
                      'true')
    r = r.json()
    docs = r['response']['docs']
    dois = []
    if docs:
        for docs in docs:
            doi = docs["doi"]
            if uri_lookup_doi(doi) is None:
                print(doi)
            dois.append(doi)
        return dois


def temp_subject(concept, g):
    payload = {'email': email, 'password': password, 'query': 'SELECT ?suburi'
               ' WHERE { ?suburi '
               '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
               '<http://www.w3.org/2004/02/skos/core#Concept> . ?suburi '
               '<http://www.w3.org/2000/01/rdf-schema#label> "' + concept +
               '" .} '}
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url, params=payload, headers=headers)
    uri_found = r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        for bindings in bindings:
            if "suburi" in bindings:
                sub_uri = bindings["suburi"]["value"]
            else:
                sub_uri = None
            sub_uri = sub_uri.replace('http://connect.unavco.org/individual/',
                                      '')
            return sub_uri


def temp_journal(concept, g):
    payload = {'email': email, 'password': password, 'query': 'SELECT ?suburi'
               ' WHERE { ?suburi '
               '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
               '<http://purl.org/ontology/bibo/Journal> . ?suburi '
               '<http://www.w3.org/2000/01/rdf-schema#label> "' + concept +
               '" .} '}
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url, params=payload, headers=headers)
    uri_found = r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        for bindings in bindings:
            if "suburi" in bindings:
                sub_uri = bindings["suburi"]["value"]
            else:
                sub_uri = None
            sub_uri = sub_uri.replace('http://connect.unavco.org/individual/',
                                      '')
            return sub_uri


def temp_smush(rel_uri, g, doi_uri):
    payload = {'email': email, 'password': password, 'query': 'SELECT ?p ?o '
               'WHERE {  <http://connect.unavco.org/individual/' + rel_uri +
               '> ?p ?o . } '}
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url, params=payload, headers=headers)
    uri_found = r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        for bindings in bindings:
            p = bindings["p"]["value"] if "p" in bindings else None
            o = bindings["o"]["value"] if "o" in bindings else None
            o = o.replace("http://connect.unavco.org/individual/", "")
            p = p.replace("http://purl.org/spar/cito/", "")
            doi_uri = doi_uri.replace("http://connect.unavco.org/individual/",
                                      "")
            g.add((D[doi_uri], CITO[p], D[o]))

    payload = {'email': email, 'password': password, 'query': 'SELECT ?s ?p2 '
               'WHERE {  ?s ?p2 <http://connect.unavco.org/individual/' +
               rel_uri + '> . } '}
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url, params=payload, headers=headers)
    uri_found = r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        for bindings in bindings:
            s = bindings["s"]["value"] if "s" in bindings else None
            p2 = bindings["p2"]["value"] if "p2" in bindings else None
            s = s.replace("http://connect.unavco.org/individual/", "")
            p2 = p2.replace("http://purl.org/spar/cito/", "")
            doi_uri = doi_uri.replace("http://connect.unavco.org/individual/",
                                      "")
            g.add((D[s], CITO[p2], D[doi_uri]))


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
