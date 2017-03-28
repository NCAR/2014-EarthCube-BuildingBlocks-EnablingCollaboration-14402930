# The goal here is to query the NSF grants API. Automate this with cron jobs
# to keep our Connect UNAVCO database current.

import requests
import logging
from logging import handlers
from datetime import datetime
from rdflib import Literal, Graph, XSD, URIRef
from rdflib.namespace import Namespace
import namespace as ns
import argparse
import csv
import time
from namespace import VIVO, VCARD, OBO, BIBO, FOAF, SKOS, D, RDFS, RDF, VLOCAL, WGS84, EC
from api_fx import (vivo_api_query, uri_gen, new_vcard, sparql_update)




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
LOG_FILENAME = 'logs/stations-update.log'
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

# If you're going for station retire dates, change the last line to "} FILTER NOT EXISTS {?station vivo:dateTimeValue ?dtval. }} ")
def get_stations_in_vivo():
    query = ("PREFIX rdf: <"+RDF+"> "
             "PREFIX vcard: <"+VCARD+"> "
             "PREFIX rdfs: <"+RDFS+"> "
             "PREFIX vivo: <"+VIVO+"> "
             "PREFIX obo: <"+OBO+"> "
             "PREFIX vlocal: <"+VLOCAL+"> "
             "PREFIX ec: <"+EC+"> "

             "SELECT * WHERE { "
             "GRAPH <http://vitro.mannlib.cornell.edu/default/vitro-kb-2> { "
             "?station a ec:Station . "
             "?station rdfs:label ?stationLabel . "
             "?station vlocal:has4CharID ?id "
             "}} ")

    gstat = vivo_api_query(query=query)
    in_vivo_list = []

    for station in gstat:
        in_vivo_list.append(station['id']['value'])
    return in_vivo_list


def get_station_list():
    ''' Get existing station list from beta web services

    NOTE: This service is available on the internal UNAVCO network only!

    Args:
        None

    Returns:
        List of 4-character station IDs

    '''
    
    API_URL = ('http://web-services.unavco.org:80/internalWS/gps/'
              'metadata/name/sites/beta')
    headers = {'Accept': 'application/json'}

    r = requests.get(API_URL, headers=headers)
                     
    try:
        json = r.json()
        return json['stationnames']
    except ValueError:
        logging.exception("Nothing returned from query API. "
                          "Ensure the API address is correct.")
        return None
        

def get_station_meta(FourChID=None):
    API_URL = ('http://web-services.unavco.org:80/metadata/stationlist/'
               'sites/beta')
    headers = {'Accept': 'application/json'}

    r = requests.get(API_URL, headers=headers)
                     
    try:
        json = r.json()
        return json
    except ValueError:
        logging.exception("Nothing returned from query API. "
                          "Ensure the API address is correct.")
        return None
        
def get_active_stations():
    active_stations = []

    API_URL = ('http://web-services.unavco.org:80/internalWS/gps/metadata/'
               'stationcoordinate/sites/beta?refframe=igs08&verboseheader=false&stddev=false')
    headers = {'Accept': 'text/csv'}

    r = requests.get(API_URL, headers=headers)
    data = r.text
                     
    try:
        csv_f = csv.reader(data.splitlines(), delimiter=',')
        next(csv_f, None)  #skip the headers
        for row in csv_f:
            FourChID = row[0]
            active_stations.append(FourChID)
        return active_stations
    except ValueError:
        logging.exception("Nothing returned from query API. "
                          "Ensure the API address is correct.")
        return None
        
        
def get_gsac_stations():
    active_stations = []

    API_URL = ('http://www.unavco.org/gsacws/gsacapi/site/search')
    payload = {'site.createdate.from': '1980-12-01', 'output': 'site.json',
               'limit': '50000', 'site.type': 'gnss.site.continuous'}
    
    r = requests.get(API_URL, params = payload)
                     
    try:
        r = r.json()
        for station in r:
            active_stations.append(station['ShortName'])
        return r,active_stations
    except ValueError:
        logging.exception("Nothing returned from query API. "
                          "Ensure the API address is correct.")
        return None     


r,active_stations = get_gsac_stations()
in_vivo_list = get_stations_in_vivo()
donethat = []

for station in r:
    chID = station['ShortName']
    '''
    #Code here adds decommisioning dates for stations
    if station['Status']['Id'] == 'decomissioned' and station['ShortName'] in in_vivo_list and station['ShortName'] not in donethat:
        chID = station['ShortName']
        dt = station['ToDate']
        # Add a prefix if the chID starts with a number
        if chID[0].isdigit():
            chID = 'n' + chID
            
        dt = time.strptime(dt, "%b %d, %Y %I:%M:%S %p")
        dt = time.strftime("%Y-%m-%dT%H:%M:%S", dt)
            
        dt_uri = uri_gen('n', g)

        g.add((D[chID], VIVO.dateTimeValue, D[dt_uri]))
        g.add((D[dt_uri], RDF.type, VIVO.DateTimeValue))
        g.add((D[dt_uri], VIVO.dateTime, Literal(dt,datatype=XSD.dateTime)))
        g.add((D[dt_uri], VIVO.dateTimePrecision, VIVO.yearMonthDayPrecision))
    
        donethat.append(chID)
        print station['ShortName']+' '+station['ToDate']

    '''
    if chID not in in_vivo_list and chID not in donethat:        
        # Add a prefix if the chID starts with a number
        if chID[0].isdigit():
            chID = 'n' + chID
        
        g.add((D[chID], RDF.type, EC.Station))
        g.add((D[chID], VLOCAL.has4CharID, Literal(chID,datatype=XSD.string)))
        
        if 'LongName' in station:    
            title = station['LongName']
        else:
            title = station['ShortName']
        g.add((D[chID], RDFS.label, Literal(title,datatype=XSD.string)))
        
        if 'EarthLocation' in station:
            lat = station['EarthLocation']['Latitude']
            lon = station['EarthLocation']['Longitude']
            g.add((D[chID], WGS84.lat, Literal(lat,datatype=XSD.decimal)))
            g.add((D[chID], WGS84.long, Literal(lon,datatype=XSD.decimal)))
            
        donethat.append(chID)
    
    
timestamp = str(datetime.now())[:-7]

if len(g) > 0:
    try:
        with open("rdf/station-update-"+timestamp+"-in.ttl", "w") as f:
            f.write(g.serialize(format=args.format))
            log.info('Wrote RDF to rdf/station-update-' + timestamp +
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
        with open("rdf/station-update-" + timestamp + "-out.ttl", "w") as fout:
            fout.write(gout.serialize(format=args.format))
            log.info('Wrote RDF to rdf/station-update-' + timestamp +
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