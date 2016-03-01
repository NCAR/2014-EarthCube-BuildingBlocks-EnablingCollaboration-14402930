# Query VIVO to generate the word cloud variable list
# This is a ghetto caching mechanism when paired with a cron job

import urllib
import logging
from logging import handlers
from datetime import datetime
from rdflib import Literal, Graph, XSD, URIRef
from rdflib.namespace import Namespace
import namespace as ns
import argparse
from namespace import VIVO, OBO, D, RDFS, RDF, VLOCAL
from api_fx import (vivo_api_query)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Set logging "
                        "level to DEBUG.")
    parser.add_argument("-d", "--directory", default="/usr/local/apache-tomcat"
                        "-8.0.24/webapps/vivo/templates/freemarker/page/"
                        "partials/", dest="WC_TERM_DIRECTORY", help="The"
                        " directory where wordCloudTerms.ftl is stored.")
    # Parse
    args = parser.parse_args()

# Set up logging to file and console
LOG_FILENAME = 'logs/concepts-update.log'
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


def get_concepts_in_vivo():
    query = ("PREFIX rdf: <"+RDF+"> "
             "PREFIX rdfs: <"+RDFS+"> "
             "PREFIX vivo: <"+VIVO+"> "
             "PREFIX obo: <"+OBO+"> "
             "PREFIX vlocal: <"+VLOCAL+"> "

             "SELECT ?theURI (str(?label) as ?name) (COUNT(?label) as ?size) "
             "WHERE { "
             "{?person vlocal:hasExpertise ?theURI} "
             "UNION{?person vivo:hasResearchArea ?theURI} "
             "UNION{?person obo:ERO_0000031 ?theURI}. "
             " ?theURI rdfs:label ?label . "
             "} GROUP BY ?theURI ?label ORDER BY DESC(?size) ")

    r_concepts = vivo_api_query(query=query)
    return r_concepts

try:
    with open(args.WC_TERM_DIRECTORY+"wordCloudTerms.ftl", "w") as f:
        r = get_concepts_in_vivo()
        log.info('VIVO API returned ' + str(len(r)) + ' concepts.')

        lines = []

        for concept in r:
            concept_var = ('{"text":"' + concept['name']['value'] +
                           '","size":' + concept['size']['value']+',"uri":"' +
                           urllib.quote_plus(concept['theURI']['value']) +
                           '"}')
            lines.append(concept_var)

        log.info('Building word cloud data file.')

        timestamp = str(datetime.now())[:-7]
        f.write("<#-- $This file is distributed under the terms of the license"
                " in /doc/license.txt$ -->\n"
                "<#-- File created: " + timestamp + " --> \n\n"
                "<script>\n"
                "\n"
                "var word_list = [")

        f.write(",\n      ".join(item for item in lines))

        f.write("];\n\n      "
                "var urlsBase = '${urls.base}';\n"
                "</script>  ")

        log.info("Wrote file to " + args.WC_TERM_DIRECTORY +
                 "wordCloudTerms.ftl")

except IOError:
    # Handle the error.
    log.exception("Failed to write RDF file. "
                  "Does a directory named 'rdf' exist?")
