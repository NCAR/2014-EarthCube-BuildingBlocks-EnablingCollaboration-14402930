import requests
import lxml
from lxml import html
import logging
from logging import handlers
from datetime import datetime
from rdflib import Literal, Graph, XSD, URIRef
from rdflib.namespace import Namespace
import namespace as ns
import argparse
from namespace import VIVO, VCARD, OBO, BIBO, FOAF, SKOS, D, RDFS, RDF, VLOCAL
from api_fx import (vivo_api_query, vivo_api_construct, uri_gen, new_vcard,
                    sparql_update)
import nicklookup.python_parser as nicklookup


DEFAULT_ORG_URI = D.org253530
DEPT_URIS = {'GI': 'org425399', 'ECE': 'org473959', 'GDS': 'org904367', 'BA':
             'org575275', 'ExO': 'org321045', 'HQ': 'org321045'}
LOCATION_URIS = {'CA': 'n546546', 'CO': 'n3573', 'AK': 'n622145'}


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
                        "n3, turtle", "nt", "pretty-xml", "trix"], help="The "
                        "RDF format for serializing. Default is turtle.")
    parser.add_argument("--debug", action="store_true", help="Set logging "
                        "level to DEBUG.")

    # Parse
    args = parser.parse_args()

# Set up logging to file and console

LOG_FILENAME = 'logs/staff-update.log'
LOG_FORMAT = '%(asctime)s - [%(levelname)s] - %(message)s'
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
if args.debug:
    LOGGING_LEVEL = logging.DEBUG
    logging.getLogger("requests").setLevel(logging.DEBUG)
    logging.getLogger("SPARQLWrapper").setLevel(logging.DEBUG)
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
gemp = Graph(namespace_manager=ns.ns_manager)
gout = Graph(namespace_manager=ns.ns_manager)

current_employees = []  # Add scraped employees to a list to compare

time = datetime.now()
timestamp = str(time)[:-7]
date = time.strftime('%Y-%m-%dT%H:%M:%S')


def get_employees(gemp):
    query = ("PREFIX rdf: <"+RDF+"> "
             "PREFIX vcard: <"+VCARD+"> "
             "PREFIX rdfs: <"+RDFS+"> "
             "PREFIX vivo: <"+VIVO+"> "
             "PREFIX obo: <"+OBO+"> "
             "PREFIX vlocal: <"+VLOCAL+"> "

             "CONSTRUCT { ?person a vlocal:UNAVCOEmployee . "
             "?person rdfs:label ?label . "
             "?person obo:ARG_2000028 ?vcard . "
             "?vcard vcard:hasName ?name . "
             "?name vcard:givenName ?gname . "
             "?name vivo:middleName ?midName . "
             "?person obo:RO_0001025 ?location . "
             "?name vcard:familyName ?famName . } "
             "WHERE { "
             "?person a vlocal:UNAVCOEmployee . "
             "?person rdfs:label ?label . "
             "?person obo:ARG_2000028 ?vcard . "
             "?vcard vcard:hasName ?name . "
             "?name vcard:givenName ?gname . "
             "OPTIONAL{?name vivo:middleName ?midName . }"
             "?name vcard:familyName ?famName . "
             "OPTIONAL{?person obo:RO_0001025 ?location . }"
             "} ")

    gemp = vivo_api_construct(query, gemp)
    return(gemp)


def get_person(name, g=None):

    # The first pass ignores the middle name in case NSF has none but VIVO does
    query1 = ("PREFIX rdf: <"+RDF+"> "
              "PREFIX rdfs: <"+RDFS+"> "
              "PREFIX foaf: <"+FOAF+"> "
              "PREFIX vcard: <"+VCARD+"> "
              "PREFIX vivo: <"+VIVO+"> "
              "PREFIX obo: <"+OBO+"> "
              "SELECT ?per "
              "WHERE { "
              "?per obo:ARG_2000028 ?vcard . "
              "?vcard vcard:hasName ?nameobj . "
              "?nameobj vcard:familyName ?famname . "
              "?nameobj vcard:givenName ?givname . "
              "BIND(CONCAT(?givname, ?famname) AS ?fullname) "
              "BIND(replace(replace(lcase(STR(?fullname)), '\\\.', ''),' ','')"
              " as ?fixname) "
              "FILTER (?fixname = '" + name.lower().replace(
                                                            ' ', '').replace(
                                                            '.', '') + "')"
              "} ")

    query2 = ("PREFIX rdf: <"+RDF+"> "
              "PREFIX rdfs: <"+RDFS+"> "
              "PREFIX foaf: <"+FOAF+"> "
              "PREFIX vcard: <"+VCARD+"> "
              "PREFIX vivo: <"+VIVO+"> "
              "PREFIX obo: <"+OBO+"> "
              "SELECT ?per "
              "WHERE { "
              "?per obo:ARG_2000028 ?vcard . "
              "?vcard vcard:hasName ?nameobj . "
              "?nameobj vcard:familyName ?famname . "
              "?nameobj vcard:givenName ?givname . "
              "OPTIONAL {?nameobj vivo:middleName ?midname . } "
              "BIND(COALESCE(?midname, '') As ?midname1) "
              "BIND(CONCAT(?givname, ?midname1, ?famname) AS ?fullname) "
              "BIND(replace(replace(lcase(STR(?fullname)), '\\\.', ''),' ','')"
              " as ?fixname) "
              "FILTER (?fixname = '" + name.lower().replace(' ', '').replace(
                                                            '.', '') + "')"
              "} ")

    # Somebody might go by their middle name.
    query3 = ("PREFIX rdf: <"+RDF+"> "
              "PREFIX rdfs: <"+RDFS+"> "
              "PREFIX foaf: <"+FOAF+"> "
              "PREFIX vcard: <"+VCARD+"> "
              "PREFIX vivo: <"+VIVO+"> "
              "PREFIX obo: <"+OBO+"> "
              "SELECT ?per "
              "WHERE { "
              "?per obo:ARG_2000028 ?vcard . "
              "?vcard vcard:hasName ?nameobj . "
              "?nameobj vivo:middleName ?midname . "
              "?nameobj vcard:familyName ?famname . "
              "BIND(CONCAT(?midname, ?famname) AS ?fullname) "
              "BIND(replace(replace(lcase(STR(?fullname)), '\\\.', ''),' ','')"
              " as ?fixname) "
              "FILTER (?fixname = '" + name.lower().replace(' ', '').replace(
                                                            '.', '') + "')"
              "} ")

    if g:  # Execute the query on the local employee graph first
        qres = g.query(query1)
        if not qres:
            qres = g.query(query2)
        if not qres:
            qres = g.query(query3)
        for row in qres:
            person = {'id': (row[0].replace(D, ''))}
            return person

    bindings = vivo_api_query(query1)  # Not found in local graph, try api
    if not bindings:
        bindings = vivo_api_query(query2)
    if not bindings:
        bindings = vivo_api_query(query3)
    if bindings and 'per' in bindings[0]:
        person = {'id': bindings[0]['per']['value'].replace(D, '')}

    else:
        person = {'id': None}

    return person


def get_person_info(per_uri):
    query = ("PREFIX rdf: <"+RDF+"> "
             "PREFIX rdfs: <"+RDFS+"> "
             "PREFIX foaf: <"+FOAF+"> "
             "PREFIX vcard: <"+VCARD+"> "
             "PREFIX vivo: <"+VIVO+"> "
             "PREFIX obo: <"+OBO+"> "
             "PREFIX d: <"+D+"> "
             "PREFIX vlocal: <"+VLOCAL+"> "

             "SELECT * "
             "WHERE { "
             "d:"+per_uri+" obo:ARG_2000028 ?vcard . "
             "OPTIONAL{d:"+per_uri+" rdf:type ?objectType . "
             "FILTER ((?objectType)=vlocal:UNAVCOEmployee) } "
             "OPTIONAL{?vcard vcard:hasEmail ?email . "
             "?email vcard:email ?emailAddress .} "
             "OPTIONAL{?vcard vcard:hasTelephone ?tel . "
             "?tel vcard:telephone ?phonenum . "
             "FILTER NOT EXISTS{?tel a vcard:Fax .}} "
             "OPTIONAL{d:"+per_uri+" obo:RO_0001025 ?location . "
             "?location a vivo:Building . "
             "?location rdfs:label ?locationLabel .} "
             "OPTIONAL{?position vivo:relates d:"+per_uri+" . "
             "?position a vivo:Position . "
             "?position rdfs:label ?positionLabel . "
             "?position vivo:dateTimeInterval ?dtint . "
             "OPTIONAL{ ?dtint vivo:start ?dtstart . "
             "?dtstart vivo:dateTime ?dtstartval . "
             "} FILTER NOT EXISTS{?dtint vivo:end ?dtendval .} } "
             "} ")

    bindings = vivo_api_query(query)
    if bindings:
        per_info = bindings[0]

    else:
        # Ruh roh!
        per_info = {}
        log.warn('Could not retrieve info for {} even though the URI was '
                 'detected. Something is probably wrong.'.format(per_uri))
        log.warn('The unsuccessful query was {}'.format(query))
    return per_info


def position_start_triples(per_uri, dept, DEPT_URIS, DEFAULT_ORG_URI, g):
    new_pos_uri = uri_gen('n', g)
    new_dtint_uri, new_dtstart_uri = uri_gen('n', g), uri_gen('n', g)
    g.add((D[new_pos_uri], RDF.type, VIVO.NonAcademicPosition))
    g.add((D[new_pos_uri], RDFS.label, Literal(title)))
    g.add((D[new_pos_uri], VIVO.relates, D[per_uri['id']]))
    g.add((D[per_uri['id']], VIVO.relatedBy, D[new_pos_uri]))
    g.add((D[new_pos_uri], VIVO.dateTimeInterval, D[new_dtint_uri]))
    g.add((D[new_dtint_uri], RDF.type, VIVO.DateTimeInterval))
    g.add((D[new_dtint_uri], VIVO.start, D[new_dtstart_uri]))
    g.add((D[new_dtstart_uri], RDF.type, VIVO.DateTimeValue))
    g.add((D[new_dtstart_uri], VIVO.dateTime, Literal(date,
                                                      datatype=XSD.dateTime)))

    if dept:
        dept = dept.split(' ')[0].split('-')[0]
        if dept in DEPT_URIS:
            g.add((D[new_pos_uri], VIVO.relates, D[DEPT_URIS[dept]]))
        else:
            g.add((D[new_pos_uri], VIVO.relates, URIRef(DEFAULT_ORG_URI)))
            log.warn('{} department/organization is unknown.'.format(dept))
    else:
        g.add((D[new_pos_uri], VIVO.relates, URIRef(DEFAULT_ORG_URI)))
        log.warn('{} does not appear to belong to a department'.format(name))

    return new_pos_uri


def position_end_triples(per_info, g):
    if 'dtint' not in per_info:
        dtint_uri = uri_gen('n', g)
        g.add((D[dtint_uri], RDF.type, VIVO.DateTimeInterval))
        g.add((URIRef(per_info['position']['value']), VIVO.dateTimeInterval,
               D[dtint_uri]))
    else:
        dtint_uri = per_info['dtint']['value']
    dtend_uri = uri_gen('n', g)
    g.add((URIRef(dtint_uri), VIVO.end, D[dtend_uri]))
    g.add((D[dtend_uri], RDF.type, VIVO.DateTimeValue))
    g.add((D[dtend_uri], VIVO.dateTime, Literal(date,
                                                datatype=XSD.dateTime)))


def new_telephone_triples(vcard_uri, phone, g):
    new_tele_uri = uri_gen('n', g)
    g.add((D[vcard_uri], VCARD.hasTelephone, D[new_tele_uri]))
    g.add((D[new_tele_uri], RDF.type, VCARD.Telephone))
    g.add((D[new_tele_uri], VCARD.telephone, Literal(phone)))


def new_email_triples(vcard_uri, email, g):
    new_email_uri = uri_gen('n', g)
    g.add((D[vcard_uri], VCARD.hasEmail, D[new_email_uri]))
    g.add((D[new_email_uri], RDF.type, VCARD.Email))
    g.add((D[new_email_uri], RDF.type, VCARD.Work))
    g.add((D[new_email_uri], VCARD.email, Literal(email)))


# UNAVCO employees in an RDF graph for subsequent queries
gemp = get_employees(gemp)
print('Employee query returned {} triples.'.format(len(gemp)))

HEADERS = {
    'Origin': 'http://www.unavco.org',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.8',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 '
    'Safari/537.36', 'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
    'image/webp,*/*;q=0.8',
    'Cache-Control': 'max-age=0',
    'Referer': 'http://www.unavco.org/contact/staff-directory/staff-directory'
    '.html',
    'Connection': 'keep-alive',
}


DATA = 'showPhoto=0&showInsecureEmail=1'

page = requests.post('http://www.unavco.org/contact/staff-directory/staff-'
                     'directory.html', headers=HEADERS, data=DATA)
root = html.fromstring(page.content)
tree = lxml.etree.ElementTree(root)

rows = tree.xpath('/html/body/div/div[6]/div/table/tbody/tr')
log.info('Scraping '+str(len(rows))+' rows on staff list.')
for row in rows:
    if row.getchildren():
        row_data = [c.text for c in row.getchildren()]  # Top level (no links)
        for idx, c in enumerate(row.getchildren()):  # Email + phone are links
            if c.getchildren():
                row_data[idx] = c.getchildren()[0].text

    log.debug('Row info: {}'.format(row_data))
    first_name, last_name, dept, title, boz, loc, email, phone, cell = row_data

    if first_name and last_name:
        name = ' '.join([first_name, last_name])
        per_uri = get_person(name, gemp)  # Restrict query to employees first
        if per_uri['id']:
            log.debug('{} found in database with uri {}.'
                      .format(name, per_uri['id']))

        else:  # Try nicknames
            nicknames = nicklookup.NameDenormalizer('nicklookup/names.csv'). \
                        get(first_name)
            if nicknames:
                for nickname in nicknames:
                    nickname = ' '.join([nickname, last_name])
                    per_uri = get_person(nickname, gemp)
                    log.debug('Nickname: {0} Result: {1}'.
                              format(nickname, per_uri))
                    if per_uri['id']:
                        log.debug('{} found in database as "{}" with uri '
                                  '{}.'.format(name, nickname, per_uri['id']))
                        break

        if per_uri['id']:
            # Look up existing info
            per_info = get_person_info(per_uri['id'])
            if 'objectType' not in per_info:
                g.add((D[per_uri['id']], RDF.type, VLOCAL.UNAVCOEmployee))
                log.info("{} {} found in database as non-employee, adding "
                         "employee type .".format(first_name, last_name))

        else:
            per_info = {}
            log.info(u'{} could not be found in the database.'.format(name))
            per_uri['id'] = uri_gen('per', g)
            g.add((D[per_uri['id']], RDF.type, FOAF.Person))
            g.add((D[per_uri['id']], RDF.type, VLOCAL.UNAVCOEmployee))
            g.add((D[per_uri['id']], RDFS.label, Literal(', '.join(
                  [last_name, first_name]))))
            per_info = {'vcard': {'value': None}}
            per_info['vcard']['value'] = new_vcard(first_name,
                                                   last_name, None, g)
            g.add((D[per_uri['id']], OBO.ARG_2000028,
                   D[per_info['vcard']['value']]))

        vcard_uri = per_info['vcard']['value'].replace(D, '')
        current_employees.append(per_uri['id'])

        if title:
            title = title.strip()

            if 'position' in per_info:  # Old position
                if title == "Content Specialist/Data Tech II":  # Eugh!
                    pass
                elif title != per_info['positionLabel']['value']:  # Add end
                    log.info('{} position changed from {} to {}.'.format(
                             name, per_info['positionLabel']['value'], title))
                    position_end_triples(per_info, g)

                    # Add new triples fo new position
                    new_pos_uri = position_start_triples(per_uri, dept,
                                                         DEPT_URIS,
                                                         DEFAULT_ORG_URI, g)

            else:
                # Add new triples fo new position
                new_pos_uri = position_start_triples(per_uri, dept, DEPT_URIS,
                                                     DEFAULT_ORG_URI, g)

        # We only put people in buildings, not cities
        if loc:
            if loc in LOCATION_URIS:
                new_loc_uri = LOCATION_URIS[loc]
                if 'location' in per_info:
                    if (per_info['location']['value'].replace(D, '') !=
                            new_loc_uri):
                        gout.add((URIRef(per_info['location']['value']),
                                  OBO.RO_0001015, D[per_uri['id']]))
                        gout.add((D[per_uri['id']], OBO.RO_0001025, URIRef(
                                  per_info['location']['value'])))
                        g.add((D[per_uri['id']], OBO.RO_0001025,
                               D[new_loc_uri]))
                        log.info('{} location updated from {} to {}.'.format
                                 (name, per_info['locationLabel']['value'],
                                  loc))
                else:
                    g.add((D[per_uri['id']], OBO.RO_0001025, D[new_loc_uri]))

        if email:
            if 'emailAddress' in per_info:
                if per_info['emailAddress']['value'] != email:
                    gout.add((D[vcard_uri], VCARD.hasEmail,
                              URIRef(per_info['email']['value'])))
                    gout.add((URIRef(per_info['email']['value']), RDF.type,
                              VCARD.Email))
                    gout.add((URIRef(per_info['email']['value']), RDF.type,
                              VCARD.Work))
                    gout.add((URIRef(per_info['email']['value']), VCARD.email,
                              Literal(per_info['emailAddress']['value'])))

                    new_email_triples(vcard_uri, email, g)
                    log.info('{} email changed from {} to {}.'.format(name,
                             per_info['emailAddress']['value'], email))
            else:
                new_email_triples(vcard_uri, email, g)

        if phone:
            # Don't add incomplete phone numbers or known bad numbers
            # (e.g. Beth P.S. reported the number on the staff page was wrong)
            if phone != "303-381-7483" and len(phone) > 11:
                if 'phonenum' in per_info:
                    if per_info['phonenum']['value'] != phone:
                        gout.add((D[vcard_uri], VCARD.hasTelephone,
                                  URIRef(per_info['tel']['value'])))
                        gout.add((URIRef(per_info['tel']['value']), RDF.type,
                                  VCARD.Telephone))
                        gout.add((URIRef(per_info['tel']['value']),
                                  VCARD.telephone, Literal(per_info['phonenum']
                                                           ['value'])))

                        new_telephone_triples(vcard_uri, phone, g)
                        log.info('{} phone changed from {} to {}.'.format(name,
                                 per_info['phonenum']['value'], phone))
                else:
                    new_telephone_triples(vcard_uri, phone, g)
                    log.debug('{} phone set as {}, coo\'?'.format(name, phone))

    else:
        log.warn('This script will not work with incomplete names. '
                 'Scraped "{0}" as the first name and "{1}" as the '
                 'last name.'.format(first_name, last_name))

for person in gemp.subjects(RDF.type, VLOCAL.UNAVCOEmployee):
    if person.replace(D, '') not in current_employees:
        name = gemp.value(person, RDFS.label)
        log.info('{} not found on staff list, removing employee status'.
                 format(name))

        per_info = get_person_info(person.replace(D, ''))
        gout.add((person, RDF.type, VLOCAL.UNAVCOEmployee))
        for location in gemp.objects(person, OBO.RO_0001025):
                gout.add((person, OBO.RO_0001025, location))
                gout.add((location, OBO.RO_0001015, person))
        if 'position' in per_info:
            position_end_triples(per_info, g)


if len(g) > 0:
    try:
        with open("rdf/staff-update-"+timestamp+"-in.ttl", "w") as f:
            f.write(g.serialize(format=args.format))
            log.info('Wrote RDF to rdf/staff-update-' + timestamp + '-in.ttl '
                     'in ' + args.format+' format.')
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
        with open("rdf/staff-update-"+timestamp+"-out.ttl", "w") as fout:
            fout.write(gout.serialize(format=args.format))
            log.info('Wrote RDF to rdf/staff-update-' + timestamp + '-out.ttl '
                     'in ' + args.format + ' format.')
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
