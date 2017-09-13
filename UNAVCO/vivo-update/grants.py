# The goal here is to query the NSF grants API. Automate this with cron jobs
# to keep our Connect UNAVCO database current.

from lxml import html
import logging
from logging import handlers
from datetime import datetime
from rdflib import Literal, Graph, XSD, URIRef
from rdflib.namespace import Namespace
import namespace as ns
import argparse
from namespace import VIVO, VCARD, OBO, BIBO, FOAF, SKOS, D, RDFS, RDF, VLOCAL
from api_fx import (vivo_api_query, uri_gen, new_vcard, sparql_update,
                    call_nsf_api)


NSF_ID = 'org491200'
NASA_ID = 'org631200'
PER_PAGE = 25  # Number of grants to return at a time from the NSF API. Max 25.
SEARCH_KEYWORD = 'unavco'  # Term to use in NSF API search.
START_DATE = '09/01/2015'  # Date to start the search from.

ORG_SYNONYMS = {'University of California-San Diego Scripps Inst of '
                'Oceanography': 'Scripps Institution of Oceanography',
                'University Corporation For Atmospheric Res':
                'University Corporation For Atmospheric Research',
                'University of Colorado at Boulder':
                'University of Colorado Boulder',
                'Ohio State University Research Foundation -DO NOT USE':
                'Ohio State University',
                'OHIO STATE UNIVERSITY, THE': 'Ohio State University',
                'University of Hawaii':
                u'University of Hawai\\\'i at M\u0101noa',
                'University of Miami Rosenstiel School of Marine&'
                'Atmospheric Sci': 'University of Miami',
                'University of Alaska Fairbanks Campus':
                'University of Alaska, Fairbanks',
                'Louisiana State University & Agricultural '
                'and Mechanical College':
                'Louisiana State University',
                'Board of Regents, NSHE, obo University of Nevada, Reno':
                'University of Nevada, Reno'}

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

    parser.add_argument("--debug", action="store_true", help="Set logging "
                        "level to DEBUG.")

    # Parse
    args = parser.parse_args()

# Set up logging to file and console
LOG_FILENAME = 'logs/grants-update.log'
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


def get_grants():
    ''' Get existing grants info using the VIVO query API

    The get_member function calls the VIVO query API.
    The query looks for info based on the organization name,
    a URI supplied by the KNOWN_ORGS list or by user input.

    Args:
        None

    Returns:
        Dictionary of grant info if successful, None otherwise.

    '''

    q_info = {}  # Create an empty dictionary

    query = ("PREFIX rdf: <"+RDF+"> "
             "PREFIX rdfs: <"+RDFS+"> "
             "PREFIX vivo: <"+VIVO+"> "
             "SELECT ?award ?label ?id "
             "WHERE { "
             "?award a vivo:Grant . "
             "?award rdfs:label ?label . "
             "?award vivo:sponsorAwardId ?id . "
             "} ")

    bindings = vivo_api_query(query)

    if bindings:
        for record in bindings:

            if "id" in record:
                award_id = record["id"]["value"].replace(D, '')
                # Strip division codes
                if award_id[:4] in ('EAR-', 'AGS-', 'DUE-', 'GEO-', 'IIA-',
                                    'PLR-'):
                    award_id = award_id[4:]
                if award_id[:5] in ('ICER-', 'CMMI-'):
                    award_id = award_id[5:]
                q_info[award_id] = {}
            else:
                # This is bad news
                award_id = None
            if award_id:
                if "label" in record:
                    q_info[award_id]['label'] = record["label"]["value"]
                else:
                    q_info[award_id]['label'] = None
                if "award" in record:
                    q_info[award_id]['award'] = record["award"]["value"]
                else:
                    q_info[award_id]['award'] = None

            log.debug('VIVO database returned '+str(q_info))
        return q_info
    else:
        return None


def get_person(name):
    name = name.replace("'", "\\'")
    if '~' in name:  # The NSF API adds a tilde on co-PI names
        name = name.split('~', 1)[0]
    name_l = name.rsplit(' ', 1)
    given_name = name_l[0]
    family_name = name_l[1]
    # name = family_name+', '+given_name

    # The first pass ignores the middle name in case NSF has none but VIVO does
    query1 = ("PREFIX rdf: <"+RDF+"> "
              "PREFIX rdfs: <"+RDFS+"> "
              "PREFIX foaf: <"+FOAF+"> "
              "PREFIX vcard: <"+VCARD+"> "
              "PREFIX vivo: <"+VIVO+"> "
              "PREFIX obo: <"+OBO+"> "
              "SELECT ?per "
              "WHERE { "
	          "?per a foaf:Person . "
              "?per obo:ARG_2000028 ?vcard . "
              "?vcard vcard:hasName ?nameobj . "
              "?nameobj vcard:familyName ?famname . "
              "?nameobj vcard:givenName ?givname . "
              "BIND(CONCAT(?givname, ?famname) AS ?fullname) "
              "BIND(replace(replace(lcase(STR(?fullname)), '\\\.', ''),' ','')"
              " as ?fixname) "
              "FILTER (?fixname = '" + name.lower().replace(' ', '').
              replace('.', '')+"')"
              "} ")

    query2 = ("PREFIX rdf: <"+RDF+"> "
              "PREFIX rdfs: <"+RDFS+"> "
              "PREFIX foaf: <"+FOAF+"> "
              "PREFIX vcard: <"+VCARD+"> "
              "PREFIX vivo: <"+VIVO+"> "
              "PREFIX obo: <"+OBO+"> "
              "SELECT ?per "
              "WHERE { "
              "?per a foaf:Person . "
              "?per obo:ARG_2000028 ?vcard . "
              "?vcard vcard:hasName ?nameobj . "
              "?nameobj vcard:familyName ?famname . "
              "?nameobj vcard:givenName ?givname . "
              "OPTIONAL {?nameobj vivo:middleName ?midname . } "
              "BIND(COALESCE(?midname, '') As ?midname1) "
              "BIND(CONCAT(?givname, ?midname1, ?famname) AS ?fullname) "
              "BIND(replace(replace(lcase(STR(?fullname)), '\\\.', ''),' ','')"
              " as ?fixname) "
              "FILTER (?fixname = '" + name.lower().replace(' ', '').
              replace('.', '')+"')"
              "} ")

    bindings = vivo_api_query(query1)
    if not bindings:
        bindings = vivo_api_query(query2)
    if bindings and 'per' in bindings[0]:
        person = {'id': bindings[0]['per']['value'].replace(D, '')}

    else:
        person = {'id': None,
                  'given_name': given_name, 'family_name': family_name}

    return person


def get_org(org_name):
    if org_name in ORG_SYNONYMS:
        org_name = ORG_SYNONYMS[org_name]

    query = ("PREFIX rdf: <"+RDF+"> "
             "PREFIX rdfs: <"+RDFS+"> "
             "PREFIX foaf: <"+FOAF+"> "

             "SELECT ?org "
             "WHERE { "
             "?org a foaf:Organization . "
             "?org rdfs:label ?orgname . "
             "BIND(replace(replace(replace(replace(replace(lcase(STR(?orgname"
             ")), '\\\.', ''),' ',''),'-',''),',',''),'inc','') as ?fixname) "
             "FILTER (?fixname = '" + org_name.lower().replace('inc', '')
             .replace(' ', '').replace('.', '').replace('-', '')
             .replace(',', '') + "')"
             "} ")

    qres = g.query(query)  # Query the local graph first
    if qres:
        for row in qres:
            return row[0].replace(D, '')

    bindings = vivo_api_query(query)
    if bindings and 'org' in bindings[0]:
        org_id = bindings[0]['org']['value'].replace(D, '')

    else:
        org_id = None

    return org_id

# Load existing grants from Connect UNAVCO
q_info = get_grants()

# Loop through until there aren't any more grants returned. Max per call is 25.
offset = 0
while True:
    grants = call_nsf_api(SEARCH_KEYWORD, START_DATE, offset)
    if grants:
        log.info('NSF API returned {} grants.'.format(len(grants)))
        for grant in grants:
            if 'fundProgramName' in grant:
                if grant['fundProgramName'] == 'POSTDOCTORAL FELLOWSHIPS':
                    break

            nsf_id = grant['id']
            log.debug('Found grant #' + nsf_id + ' titled ' + grant['title'])

            if nsf_id not in q_info:
                log.info('Grant #' + nsf_id + ' not found in Connect UNAVCO '
                         'database. Adding triples.')
                award_uri, time_int_uri = uri_gen('awd'), uri_gen('n')
                start_uri, end_uri = uri_gen('n'), uri_gen('n')
                g.add((D[award_uri], RDF.type, VIVO.Grant))
                g.add((D[award_uri], RDFS.label, Literal(grant['title'],
                       datatype=XSD.string)))
                g.add((D[award_uri], BIBO.abstract,
                       Literal(grant['abstractText'])))
                g.add((D[award_uri], VIVO.sponsorAwardId,
                       Literal(grant['id'])))
                g.add((D[award_uri], VIVO.totalAwardAmount, Literal("${:,.2f}"
                       .format(float(grant['fundsObligatedAmt'])))))
                if 'agency' in grant:
                    if grant['agency'] == 'NSF':
                        g.add((D[award_uri], VIVO.assignedBy, D[NSF_ID]))
                    elif grant['agency'] == 'NASA':
                        g.add((D[award_uri], VIVO.assignedBy, D[NASA_ID]))
                    else:
                        log.warn('Funding agency '+grant['agency'] +
                                 ' not found.')
                else:
                    log.warn('Funding agency not specified by NSF API.')

                g.add((D[award_uri], VIVO.dateTimeInterval, D[time_int_uri]))
                g.add((D[time_int_uri], RDF.type, VIVO.DateTimeInterval))
                g.add((D[time_int_uri], VIVO.start, D[start_uri]))
                g.add((D[start_uri], RDF.type, VIVO.DateTimeValue))
                g.add((D[start_uri], VIVO.dateTimePrecision,
                       VIVO.yearMonthDayPrecision))

                grant['startDate'] = datetime.strptime(grant['startDate'],
                                                       '%m/%d/%Y')
                grant['startDate'] = grant['startDate'].strftime('%Y-%m-%dT%H:'
                                                                 '%M:%S')
                g.add((D[start_uri], VIVO.dateTime, Literal(grant['startDate'],
                       datatype=XSD.dateTime)))
                if 'expDate' in grant:
                    g.add((D[time_int_uri], VIVO.end, D[end_uri]))
                    g.add((D[end_uri], RDF.type, VIVO.DateTimeValue))
                    g.add((D[end_uri], VIVO.dateTimePrecision,
                           VIVO.yearMonthDayPrecision))
                    grant['expDate'] = datetime.strptime(grant['expDate'],
                                                         '%m/%d/%Y')
                    grant['expDate'] = grant['expDate'].strftime('%Y-%m-%dT%H:'
                                                                 '%M:%S')
                    g.add((D[end_uri], VIVO.dateTime, Literal(grant['expDate'],
                           datatype=XSD.dateTime)))

                if 'awardeeName' in grant:
                    admin_org = grant['awardeeName']
                else:
                    admin_org = grant['awardee']

                admin_uri = get_org(admin_org)

                if not admin_uri:
                    log.info('Awardee ' + admin_org + ' not found in Connect '
                             'UNAVCO database. Adding triples.')
                    admin_uri = uri_gen('org')
                    g.add((D[admin_uri], RDF.type, FOAF.Organization))
                    g.add((D[admin_uri], RDFS.label, Literal(admin_org)))

                admin_role_uri = uri_gen('n')
                g.add((D[admin_role_uri], RDF.type, VIVO.AdministratorRole))
                g.add((D[award_uri], VIVO.relates, D[admin_role_uri]))
                g.add((D[admin_role_uri], OBO.RO_0000052, D[admin_uri]))
                g.add((D[admin_uri], OBO.RO_0000053, D[admin_role_uri]))
                g.add((D[admin_role_uri], VIVO.relatedBy, D[award_uri]))
                g.add((D[admin_uri], VIVO.relatedBy, D[award_uri]))

                # TODO Make name matching better.?
                pi_dict = get_person(grant['pdPIName'])
                if not pi_dict['id']:
                    log.info('PI name '+grant['pdPIName'] +
                             ' not found in Connect UNAVCO '
                             'database. Adding triples.')
                    pi_dict['id'] = new_vcard(pi_dict['given_name'],
                                              pi_dict['family_name'], None, g)

                pi_role_uri = uri_gen('n')
                g.add((D[award_uri], VIVO.relates, D[pi_role_uri]))
                g.add((D[pi_role_uri], VIVO.relatedBy, D[award_uri]))
                g.add((D[pi_role_uri], RDF.type,
                       VIVO.PrincipalInvestigatorRole))
                g.add((D[pi_role_uri], OBO.RO_0000052, D[pi_dict['id']]))
                g.add((D[pi_dict['id']], OBO.RO_0000053, D[pi_role_uri]))

                if 'coPDPI' in grant:
                    for person in grant['coPDPI']:
                        co_pi_dict = get_person(person)
                        if not co_pi_dict['id']:
                            given_name = co_pi_dict['given_name']
                            family_name = co_pi_dict['family_name']
                            log.info('Co-PI ' + given_name+' ' + family_name +
                                     ' not found in Connect UNAVCO database. '
                                     'Adding triples.')
                            # Create vCard object
                            co_pi_dict['id'] = new_vcard(given_name,
                                                         family_name, None, g)

                        co_pi_role_uri = uri_gen('n')
                        g.add((D[award_uri], VIVO.relates, D[co_pi_role_uri]))
                        g.add((D[co_pi_role_uri], VIVO.relatedBy,
                               D[award_uri]))
                        g.add((D[co_pi_role_uri], RDF.type,
                               VIVO.CoPrincipalInvestigatorRole))
                        g.add((D[co_pi_role_uri], OBO.RO_0000052,
                               D[co_pi_dict['id']]))
                        g.add((D[co_pi_dict['id']], OBO.RO_0000053,
                               D[co_pi_role_uri]))

        offset += PER_PAGE
    else:
        break

timestamp = str(datetime.now())[:-7]

if len(g) > 0:
    try:
        with open("rdf/grant-update-"+timestamp+"-in.ttl", "w") as f:
            f.write(g.serialize(format=args.format))
            log.info('Wrote RDF to rdf/grant-update-' + timestamp +
                     '-in.ttl in ' + args.format + ' format.')
    except IOError:
        # Handle the error.
        log.exception("Failed to write RDF file. "
                      "Does a directory named 'rdf' exist?")
        log.exception("The following RDF was not saved: \n" +
                      g.serialize(format=args.format))
else:
    log.info('No triples to INSERT.')

if len(gout) > 0:
    try:
        with open("rdf/grant-update-" + timestamp + "-out.ttl", "w") as fout:
            fout.write(gout.serialize(format=args.format))
            log.info('Wrote RDF to rdf/grant-update-' + timestamp +
                     '-out.ttl in ' + args.format + ' format.')
    except IOError:
        # Handle the error.
        log.exception("Failed to write RDF file. "
                      "Does a directory named 'rdf' exist?")
        log.exception("The following RDF was not saved: \n" +
                      gout.serialize(format=args.format))
else:
    log.info('No triples to DELETE.')

# The database will be updated directly if the --api flag is set
if args.use_api:
    if len(g) > 0:
        sparql_update(g, 'INSERT')
    if len(gout) > 0:
        sparql_update(gout, 'DELETE')
