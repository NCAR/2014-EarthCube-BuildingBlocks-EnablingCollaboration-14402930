import requests
import argparse
import logging
from logging import handlers
import multiprocessing
from datetime import datetime
from rdflib import Literal, Graph, URIRef, XSD
from rdflib.namespace import Namespace
import namespace as ns
from namespace import VIVO, VCARD, OBO, BIBO, FOAF, SKOS, D, RDFS, RDF, VLOCAL
from api_fx import (crossref_lookup, uri_gen, grab_corpus, vivo_api_query,
                    sparql_update)
import itertools


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--manual', action="store_true",
                        help="Input DOIs manually.")
    parser.add_argument("--debug", action="store_true", help="Set logging "
                        "level to DEBUG.")
    parser.add_argument("--updateall", action="store_true", help="Update "
                        "citations for all DOIs in VIVO.")
    parser.add_argument("-o", "--opencitations", action="store_true",
                        help="Use the OpenCitations SPARQL endpoint.")
    parser.add_argument("-c", "--crossref", action="store_true", help="Use "
                        "CrossRef to find citation links and counts.")
    parser.add_argument("-f", "--format", default="turtle", choices=["xml",
                        "n3", "turtle", "nt", "pretty-xml", "trix"], help="The"
                        " RDF format for serializing. Default is turtle.")
    parser.add_argument("-t", "--threads", type=int, default=1, help="The "
                        "number of threads to run.")
    parser.add_argument("--api", default=False, dest="use_api",
                        action="store_true", help="Send the newly created "
                        "triples to VIVO using the update API. Note, there "
                        "is no undo button! You have been warned!")

    # Parse
    args = parser.parse_args()

# Set up logging to file and console
LOG_FILENAME = 'logs/citations.log'
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

timestamp = str(datetime.now())[:-7]


def setup():
    ''' Get existing DOIs using the VIVO query API

    The setup function calls the VIVO query API.
    The query looks for existing DOIs in the database and their URIs.

    Args:
        none

    Returns:
        Dictionary of DOIs and URIs if successful, None otherwise.

    '''
    query = ('PREFIX bibo: <http://purl.org/ontology/bibo/> '
             'PREFIX vivo: <http://vivoweb.org/ontology/core#> '
             'SELECT ?pub ?doi ?cited WHERE {{ ?pub bibo:doi ?doi . '
             '?pub a ?pubType . '
             'OPTIONAL{ ?pub <' + VLOCAL + 'timesCited> ?cited } } '
             'FILTER ( ( ( ( ( ( ( ?pubType = bibo:AcademicArticle ) || '
             '( ?pubType = vivo:Abstract ) ) || ( ?pubType = bibo:Article ) )'
             ' || ( ?pubType = bibo:Book ) ) || ( ?pubType = bibo:Chapter ) )'
             ' || ( ?pubType = bibo:Thesis ) ) || ( ?pubType = '
             'vivo:ConferencePaper ) ) } ')
    bindings = vivo_api_query(query)
    if bindings:
        dois = {}
        for bindings in bindings:
            if 'doi' in bindings:
                dois[bindings['doi']['value']] = {}
                dois[bindings['doi']['value']]['uri'] = \
                    bindings['pub']['value']

                if 'cited' in bindings:
                    dois[bindings['doi']['value']]['cited'] = \
                        bindings['cited']['value']

    log.debug(dois)
    return(dois)


def get_uri_4_doi(doi):
    ''' Get URI for DOI using the VIVO query API

    The setup function calls the VIVO query API.
    The query looks for an existing DOI in the database and its URI

    Args:
        none

    Returns:
        A single URI if successful, None otherwise.

    '''
    query = ('SELECT ?uri WHERE { ?uri <' + BIBO + 'doi' +
             '> ?doi. '
             'FILTER(lcase(str(?doi)) = "' + doi.lower() + '") . }')
    bindings = vivo_api_query(query)
    if bindings:
        rel_uri = bindings[0]["uri"]["value"] if "uri" in bindings[0] else None
        return rel_uri


def gen_triples(pub_uri, cited_pub_uri):
    g.add((URIRef(pub_uri), BIBO.cites, URIRef(cited_pub_uri)))
    g.add((URIRef(cited_pub_uri), BIBO.citedBy, URIRef(pub_uri)))


def gen_citation_count_triples(uri, count, old_cites, g, gout):
    log.debug('New count: {} Count in db: {}'.format(count, str(old_cites)))
    if str(old_cites) != str(count):
        g.add((URIRef(uri), VLOCAL.timesCited,
              Literal('{}'.format(count), datatype=XSD.int)))
        if old_cites:
            gout.add((URIRef(uri), VLOCAL.timesCited,
                     Literal('{}'.format(old_cites), datatype=XSD.int)))


# Instantiate a graph and namespace
g = Graph(namespace_manager=ns.ns_manager)
gout = Graph(namespace_manager=ns.ns_manager)

if args.updateall is True or args.manual is True:
    if not args.crossref and not args.opencitations:
            log.exception('No service specified. Use the flag --crossref '
                          'or --opencitations')
            quit()
    log.info("Setting up...")
    (dois) = setup()
    log.info('DOIs retrieved from database')
else:
    log.exception('No DOIs provided. Use the flag --updateall or --manual')
    quit()

if args.manual is True:
    doi_input = raw_input('Enter a comma-separated list of DOIs\n')
    if dois == '':
        while True:
            log.info('No DOI entered, try again')
    else:
        dois_subset = {}
        doi_input = [x.strip() for x in doi_input.split(',')]
        for doi in doi_input:
            doi_uri = get_uri_4_doi(doi)
            dois_subset[doi] = {}
            dois_subset[doi]['uri'] = doi_uri
        log.debug(dois_subset)

if args.updateall:
    dois_subset = dois
totaldoi = len(dois_subset)
count = 0
log.info('Checking citation records for ' + str(totaldoi) + ' DOIs.')


def doWerk(doi):
    # Instantiate a graph and namespace
    g1 = Graph(namespace_manager=ns.ns_manager)
    g2 = Graph(namespace_manager=ns.ns_manager)
    log.debug('Processing DOI {} with URI {}'.format(doi, dois[doi]['uri']))
    if args.crossref:
        cites = crossref_lookup(doi)
        cited_doi = None
        if cites and "is-referenced-by-count" in cites:
            cited_num = int(cites["is-referenced-by-count"])
            if cited_num > 0:
                if 'cited' in dois[doi]:
                    cites_old = dois[doi]['cited']
                else:
                    cites_old = None
                gen_citation_count_triples(dois[doi]['uri'], cited_num,
                                           cites_old, g1, g2)

        if cites and "reference" in cites:
            for indiv_cite in cites["reference"]:
                if "DOI" in indiv_cite:
                    cited_doi = indiv_cite["DOI"]
                if "doi" in indiv_cite:
                    cited_doi = indiv_cite["doi"]
                if cited_doi:
                    if cited_doi in dois:
                        log.debug('Match found: ' + doi + ' cites ' +
                                  cited_doi)
                        gen_triples(dois[doi]['uri'], dois[cited_doi]['uri'])

    if args.opencitations:
        cites = grab_corpus(doi)
        for cited_doi in cites:
            if cited_doi in dois:
                log.debug('Match found: ' + doi + ' cites ' + cited_doi)
                gen_triples(dois[doi]['uri'], dois[cited_doi]['uri'])
            else:
                log.debug('DOI ' + cited_doi + ' not found in database.')
    if not g1:
        g1 = None
    if not g2:
        g2 = None
    return (g1, g2)


pool = multiprocessing.Pool(processes=args.threads)
results = pool.map(doWerk, dois_subset)

log.debug(results)

if isinstance(results, list):
    log.debug('splitting...')
    for r in results:
        log.debug(r)
        if r[0]:
            g = g + r[0]
        if r[1]:
            gout = gout + r[1]
else:
    log.debug(r)
    print(r.serialize(format="turtle"))

if len(g) > 0:
    try:
        with open("rdf/cites-" + timestamp + "-in.ttl", "w") as f:
            f.write(g.serialize(format=args.format))
            print('Wrote RDF to rdf/cites-' + timestamp +
                  '-in.ttl in ' + args.format + ' format.')
    except IOError:
        # Handle the error.
        print("Failed to write RDF file. "
              "Does a directory named 'rdf' exist?")
        print("The following RDF was not saved: \n" +
              g.serialize(format=args.format))
else:
    print('No triples to INSERT.')

if len(gout) > 0:
    try:
        with open("rdf/cites-" + timestamp + "-out.ttl", "w") as fout:
            fout.write(gout.serialize(format=args.format))
            log.info('Wrote RDF to rdf/cites-' + timestamp +
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
