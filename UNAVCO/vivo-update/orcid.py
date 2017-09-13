# This script queries the VIVO database for ORCIDs, then queries ORCID's
# public API for employment and education information.
# Automate this with cron jobs using the --api and --auto flags
# to keep the Connect UNAVCO database current.

import requests
import logging
from logging import handlers
from datetime import datetime
from rdflib import Literal, Graph, XSD, URIRef
from rdflib.namespace import Namespace
import namespace as ns
import argparse
import csv
import re
import time
import json
import sys
from namespace import (VIVO, VCARD, OBO, BIBO, FOAF, SKOS, D, RDFS, RDF,
                       VLOCAL, WGS84, EC)
from api_fx import (vivo_api_query, uri_gen, load_settings, sparql_update,
                    vivo_api_construct)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default=False, dest="use_api",
                        action="store_true", help="Send the newly created "
                        "triples to VIVO using the update API. Note, there "
                        "is no undo button! You have been warned!")
    parser.add_argument("-a", "--auto", default=False, dest="auto_mode",
                        action="store_true", help="Run in auto mode. "
                        "Unknown organizations and people will automatically "
                        "be created instead of asking the user for input.")
    parser.add_argument("-f", "--format", default="turtle", choices=["xml",
                        "n3", "turtle", "nt", "pretty-xml", "trix"], help="The"
                        " RDF format for serializing. Default is turtle.")
    parser.add_argument("--orcid", dest="orcid", help="Create triples for a "
                        "single ORCID rather than entire VIVO database.")
    parser.add_argument("--uri", dest="uri", help="VIVO URI matching the "
                        "ORCID given in the --orcid argument.")
    parser.add_argument("--debug", action="store_true", help="Set logging "
                        "level to DEBUG.")

    # Parse
    args = parser.parse_args()

    if (args.orcid or args.uri) and (args.uri is None or args.orcid is None):
        parser.error("Both --orcid and --uri required to retrieve single "
                     "ORCID profile .")

# Set up logging to file and console
LOG_FILENAME = 'logs/orcid-update.log'
LOG_FORMAT = '%(asctime)s - [%(levelname)s] - %(message)s'
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
if args.debug:
    LOGGING_LEVEL = logging.DEBUG
    logging.getLogger("requests").setLevel(logging.DEBUG)
else:
    LOGGING_LEVEL = logging.INFO
    logging.getLogger("requests").setLevel(logging.WARNING)

# Create console handler and set level
handler = logging.StreamHandler()
handler.setLevel(LOGGING_LEVEL)
formatter = logging.Formatter(LOG_FORMAT)
handler.setFormatter(formatter)
logger.addHandler(handler)

# Create error file handler and set level
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=5000000,
                                               backupCount=5, encoding=None,
                                               delay=0)
handler.setLevel(LOGGING_LEVEL)
formatter = logging.Formatter(LOG_FORMAT)
handler.setFormatter(formatter)
logger.addHandler(handler)

log = logging.getLogger(__name__)

# Instantiate a graph and namespace
g = Graph(namespace_manager=ns.ns_manager)
gout = Graph(namespace_manager=ns.ns_manager)
g_degrees = None  # Only populate degree list if needed


def get_orcids_from_vivo():
    ''' Get existing ORCID list from the vivo server set in api_settings.json

    Args:
        None

    Returns:
        List of ORCIDs

    '''

    query = ("PREFIX rdf: <" + RDF + "> "
             "PREFIX vivo: <" + VIVO + "> "
             "PREFIX foaf: <" + FOAF + "> "

             "SELECT * WHERE { "
             "GRAPH <http://vitro.mannlib.cornell.edu/default/vitro-kb-2> { "
             "?person rdf:type foaf:Person . "
             "?person vivo:orcidId ?orcid . "
             "}} ")

    r = vivo_api_query(query=query)
    log.debug(r)
    return r


def fetch_orcid_token():
    ''' Get token for ORCID public API

    Args:
        None

    Returns:
        ORCID oauth token

    '''

    data = load_settings()
    client_id = data['orcid_client_id']
    client_secret = data['orcid_client_secret']
    payload = {"client_id": client_id, "client_secret": client_secret,
               "grant_type": "client_credentials",
               "scope": "/read-public", 'grant_type': 'client_credentials'}
    r = requests.post('https://orcid.org/oauth/token',
                      headers={"Accept": "application/json"}, data=payload)

    if r:
        r = r.json()
        log.debug(r)
        return r
    else:
        raise Exception("Request to fetch ORCID token returned %s"
                        % r.status_code)


def fetch_orcid_profile(orcid, token):
    ''' Get full profile from ORCID

    Args:
        orcid: ORCID id as full URI
        token: ORCID oauth token

    Returns:
        Full ORCID profile in json format

    '''

    headers = {"Content-Type": "application/json", "Authorization": "Bearer " +
               token}
    r = requests.get('https://pub.orcid.org/v1.2/%s/orcid-profile/' % orcid,
                     headers=headers)

    if r:
        # print json.dumps(r.json(), indent=4, sort_keys=True)
        r = r.json()
        log.debug(r)
        return r
    else:
        raise Exception("Request to fetch ORCID profile for %s returned %s"
                        % (orcid, r.status_code))


def fetch_vivo_profile(orcid):
    ''' Get full profile from VIVO server defined in api_settings.json

    Args:
        orcid: ORCID id

    Returns:
        Full VIVO profile in RDF format

    '''
    query = ("PREFIX vivo: <" + VIVO + "> "

             "DESCRIBE * "
             "WHERE { { "
             "?person vivo:orcidId <http://orcid.org/" + orcid + "> . } "
             "UNION {?person vivo:orcidId <http://orcid.org/" + orcid + "> . "
             "?person vivo:relatedBy ?position . "
             "?position a vivo:Position . "
             "OPTIONAL{ ?position vivo:dateTimeInterval ?dtint . "
             "?dtint vivo:start ?dtstart . "
             "OPTIONAL{ ?dtint vivo:end ?dtend .} "
             "} "
             "} "
             "} ")

    g_profile = Graph(namespace_manager=ns.ns_manager)
    g_profile = vivo_api_construct(query=query, g=g_profile)
    return g_profile


def fetch_orgs_from_vivo():
    ''' Get existing organization list from server defined in api_settings.json

    Args:
        None

    Returns:
        List of organization URIs, labels, labels stripped of spaces and
        non-alphanumeric characters, and their Ringgold ID if available
    '''

    query = ("PREFIX rdf: <" + RDF + "> "
             "PREFIX vlocal: <" + VLOCAL + "> "
             "PREFIX foaf: <" + FOAF + "> "
             "PREFIX rdfs: <" + RDFS + "> "

             "CONSTRUCT { ?org rdfs:label ?label . "
             "?org rdfs:label ?labelstrip . "
             "?org rdf:type foaf:Organization . "
             "?org vlocal:ringgoldID ?ringgoldID . }"
             "WHERE { "
             "?org rdf:type foaf:Organization . "
             "?org rdfs:label ?label . "
             "OPTIONAL{?org vlocal:ringgoldID ?ringgoldID . } "
             'BIND(LCASE(REPLACE(str(?label),"[^\\\w]","")) AS ?labelstrip) '
             "} ")

    g_orgs = Graph(namespace_manager=ns.ns_manager)
    g_orgs = vivo_api_construct(query=query, g=g_orgs)
    return g_orgs


def fetch_degrees_from_vivo():
    ''' Get existing degree type list from the server set in api_settings.json

    Args:
        None

    Returns:
        Degrees in the ontology with their URIs
    '''

    query = ("PREFIX vivo: <" + VIVO + "> "

             "DESCRIBE * "
             "WHERE { "
             "?degree_type_uri a vivo:AcademicDegree . "
             "} ")

    g_degrees = Graph(namespace_manager=ns.ns_manager)
    g_degrees = vivo_api_construct(query=query, g=g_orgs)
    return g_degrees


r_token = fetch_orcid_token()
if 'access_token' in r_token:
    token = r_token['access_token']
else:
    raise Exception("Couldn't get access token from ORCID, check credentials")

if args.orcid:
    orcids = ([{u'orcid': {u'type': u'uri', u'value': args.orcid},
                u'person': {u'type': u'uri', u'value': args.uri}}])
else:
    orcids = get_orcids_from_vivo()
g_orgs = fetch_orgs_from_vivo()

# Pull the info out of ORCID
log.info(u'Fetching ORCID profiles for {} records.'.format(len(orcids)))
for r in orcids:
    uri = r['person']['value']
    orcid = r['orcid']['value'].replace('http://orcid.org/', '')
    if len(orcid) != 19:
        log.warn('ORCID may be malformed, insta-death likely... ORCID should '
                 'be in the format "0000-0002-1825-0097", optionally '
                 'preceded by "http://orcid.org".')
    log.debug(u'Fetching ORCID for ' + orcid)

    orcid_profile = fetch_orcid_profile(orcid, token)
    g_profile = fetch_vivo_profile(orcid)

    for affiliation in (((orcid_profile["orcid-profile"]
                        .get("orcid-activities") or {})
                        .get("affiliations", {}) or {})
                        .get("affiliation", [])):

        if 'organization' in affiliation:
            organization = affiliation['organization']['name']

            # Skip UNAVCO positions since staff.py takes care of employees
            if 'UNAVCO' in organization.upper():
                log.debug(u'Skipping UNAVCO position')
                continue
            put_code = '-pc{}'.format(affiliation['put-code'])
            ringgold = ((affiliation["organization"]
                        .get("disambiguated-organization", {}) or {})
                        .get("disambiguated-organization-identifier"))
            log.debug(u'Affiliation: {}, ID: {}'.format(organization,
                                                        ringgold))

            title = affiliation["role-title"] or {}
            log.debug(u'Position title: {}'.format(title))

            start_year = (affiliation["start-date"] or
                          {}).get("year", {}).get("value")
            end_year = (affiliation["end-date"] or
                        {}).get("year", {}).get("value")
            log.debug(u'Date range: {} - {}'.format(start_year, end_year))

            if affiliation["type"] == "EDUCATION":
                relatedBy = g_profile.objects(URIRef(uri), OBO.RO_0000056)
            else:
                relatedBy = g_profile.objects(URIRef(uri), VIVO.relatedBy)

            position_exists = False
            for obj in relatedBy:
                log.debug(u'{} vs. {}'.format(put_code, obj))
                if put_code in obj:
                    log.debug(u'The position is already in VIVO, skipping.')
                    position_exists = True
                    break

            if not position_exists:
                # Look up URI based on Ringgold ID
                org_uri = (g_orgs.value(predicate=VLOCAL.ringgoldID,
                           object=Literal(ringgold)))
                if not org_uri:  # Try to match org based on label
                    org_strip = re.sub('[^\w]', '', organization).lower()
                    org_uri = g_orgs.value(predicate=RDFS.label,
                                           object=Literal(org_strip))
                    if not org_uri:  # Try to match org using string datatype
                        org_uri = (g_orgs.value(predicate=RDFS.label,
                                   object=Literal(org_strip,
                                                  datatype=XSD.string)))

                if not org_uri and not args.auto_mode:
                    log.info(u'{} not matched to database'
                             .format(organization))
                    while True:
                        org_uri = raw_input(u'{} not found in database, please'
                                            ' supply a URI or enter "new" to '
                                            'create a new object. '.
                                            format(organization).
                                            encode(sys.stdout.encoding))
                        if org_uri == '':
                            log.info(u'Invalid input, try again.')
                        elif org_uri == 'new':
                            org_uri = None
                            break
                        else:
                            org_uri = URIRef(org_uri)
                            if ringgold:
                                g.add((org_uri, VLOCAL.ringgoldID,
                                       Literal(ringgold)))
                                g_orgs.add((org_uri, VLOCAL.ringgoldID,
                                            Literal(ringgold)))
                            break

                # If we've made it this far just add a new organization to VIVO
                if not org_uri:
                    org_uri = D[uri_gen('org')]
                    log.info('Adding organization with URI {}'.format(org_uri))
                    if 'University' in organization:
                        g.add((org_uri, RDF.type, VIVO.University))
                    elif 'College' in organization:
                        g.add((org_uri, RDF.type, VIVO.College))
                    else:
                        g.add((org_uri, RDF.type, FOAF.Organization))
                    g.add((org_uri, RDFS.label, Literal(organization)))
                    g.add((org_uri, RDFS.label, Literal(organization)))
                    if ringgold:
                        g.add((org_uri, VLOCAL.ringgoldID, Literal(ringgold)))

                new_pos_uri = D[uri_gen('n', g) + put_code]
                if affiliation["type"] == "EMPLOYMENT":
                    g.add((new_pos_uri, RDF.type, VIVO.Position))
                    if title:
                        g.add((new_pos_uri, RDFS.label, Literal(title)))
                    g.add((new_pos_uri, VIVO.relates, URIRef(uri)))
                    g.add((URIRef(uri), VIVO.relatedBy, new_pos_uri))
                    g.add((new_pos_uri, VIVO.relates, org_uri))

                elif affiliation["type"] == "EDUCATION":
                    g.add((new_pos_uri, RDF.type, VIVO.EducationalProcess))
                    if affiliation.get("department-name"):
                        g.add((new_pos_uri,
                               VIVO.departmentOrSchool,
                               Literal(affiliation["department-name"])))
                    if title:
                        g.add((new_pos_uri, RDFS.label, Literal(title)))
                    g.add((new_pos_uri, OBO.RO_0000057, URIRef(uri)))
                    g.add((URIRef(uri), OBO.RO_0000056, new_pos_uri))
                    g.add((new_pos_uri, OBO.RO_0000057, org_uri))
                    if title:
                        if not g_degrees:
                            g_degrees = fetch_degrees_from_vivo()

                        degree_name = title

                        # Relates to degree
                        for s, p, o in g_degrees.triples((None,
                                                         VIVO.abbreviation,
                                                         None)):
                            log.debug(u'{} vs. {}'.format(o, degree_name))
                            if o.replace('.', '') in \
                                    degree_name.replace('.', ''):
                                log.debug(u'Matched name with degree URI {}'
                                          .format(s))
                                degree_type_uri = s
                                break
                            else:
                                degree_type_uri = None

                        if degree_type_uri:
                            degree_uri = D[uri_gen('n', g)]
                            g.add((degree_uri, RDF.type, VIVO.AwardedDegree))
                            g.add((degree_uri, VIVO.assignedBy, org_uri))
                            g.add((degree_uri, OBO.RO_0002353, new_pos_uri))
                            g.add((new_pos_uri, OBO.RO_0002234, degree_uri))
                            g.add((degree_uri, VIVO.relates, degree_type_uri))
                            g.add((degree_uri, VIVO.relates, URIRef(uri)))
                            g.add((degree_uri, RDFS.label,
                                   Literal(degree_name)))
                        else:
                            log.warn(u'Unable to find URI for degree of type'
                                     ' {}.'.format(degree_name))

                if start_year or end_year:
                    dtint_uri = D[uri_gen('n', g)]
                    g.add((dtint_uri, RDF.type, VIVO.DateTimeInterval))
                    g.add((new_pos_uri, VIVO.dateTimeInterval, dtint_uri))
                    if start_year:
                        start_uri = D[uri_gen('n', g)]
                        date = Literal("{}-01-01T00:00:00".format(start_year),
                                       datatype=XSD.dateTime)
                        g.add((dtint_uri, VIVO.start, start_uri))
                        g.add((start_uri, VIVO.dateTimePrecision,
                              VIVO.yearPrecision))
                        g.add((start_uri, VIVO.dateTime, Literal(date,
                              datatype=XSD.dateTime)))
                    if end_year:
                        end_uri = D[uri_gen('n', g)]
                        date = Literal("{}-01-01T00:00:00".format(end_year),
                                       datatype=XSD.dateTime)
                        g.add((dtint_uri, VIVO.end, end_uri))
                        g.add((end_uri, VIVO.dateTimePrecision,
                              VIVO.yearPrecision))
                        g.add((end_uri, VIVO.dateTime, Literal(date,
                              datatype=XSD.dateTime)))

                g_orgs = g_orgs + g


timestamp = str(datetime.now())[:-7]

if len(g) > 0:
    try:
        with open("rdf/orcid-update-"+timestamp+"-in.ttl", "w") as f:
            f.write(g.serialize(format=args.format))
            log.info(u'Wrote RDF to rdf/orcid-update-' + timestamp +
                     '-in.ttl in ' + args.format + ' format.')
    except IOError:
        # Handle the error.
        log.exception("Failed to write RDF file. "
                      "Does a directory named 'rdf' exist?")
        log.exception("The following RDF was not saved: \n" +
                      g.serialize(format=args.format))
else:
    log.info(u'No triples to INSERT.')

if len(gout) > 0:
    try:
        with open("rdf/orcid-update-" + timestamp + "-out.ttl", "w") as fout:
            fout.write(gout.serialize(format=args.format))
            log.info(u'Wrote RDF to rdf/orcid-update-' + timestamp +
                     '-out.ttl in ' + args.format + ' format.')
    except IOError:
        # Handle the error.
        log.exception("Failed to write RDF file. "
                      "Does a directory named 'rdf' exist?")
        log.exception("The following RDF was not saved: \n" +
                      gout.serialize(format=args.format))
else:
    log.info(u'No triples to DELETE.')

# The database will be updated directly if the --api flag is set
if args.use_api:
    if len(g) > 0:
        sparql_update(g, 'INSERT')
    if len(gout) > 0:
        sparql_update(gout, 'DELETE')
