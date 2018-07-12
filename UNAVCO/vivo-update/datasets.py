import requests
import argparse
import pickle
from datetime import datetime
import sys
from rdflib import Literal, Graph, URIRef
from rdflib.namespace import Namespace
import vivo_update_fx.namespace as ns
from vivo_update_fx.namespace import (VIVO, VCARD, OBO, BIBO, FOAF, SKOS, D,
                                      RDFS, RDF, EC)
from vivo_update_fx.data_api_fx import data_api_lookup
from vivo_update_fx.api_fx import (uri_gen, name_lookup,
                                   name_selecter, assign_authorship,
                                   get_datasets_in_vivo, sparql_update,
                                   get_stations_in_vivo)
from vivo_update_fx.json_fx import parse_authors_datacite
from vivo_update_fx.utility import join_if_not_empty, add_date, load_matchlist

orphans = {}
matchlist = []
count = 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default=False, dest="use_api",
                        action="store_true", help="Send the newly created "
                        "triples to VIVO using the update API. Note, there "
                        "is no undo button! You have been warned!")
    parser.add_argument("-f", "--format", default="turtle", choices=["xml",
                        "n3", "turtle", "nt", "pretty-xml", "trix"], help="The"
                        " RDF format for serializing. Default is turtle.")

    args = parser.parse_args()


matchlist = load_matchlist()

timestamp = str(datetime.now())[:-7]

# Instantiate a graph and namespace
g = Graph(namespace_manager=ns.ns_manager)

datasets_in_vivo = get_datasets_in_vivo()
stations_in_vivo = get_stations_in_vivo()

def process_doi(doi, matchlist):
    # Grab full metadata for the doi in json format
    print('Processing {}'.format(doi))

    attr = data_api_lookup(doi.replace('10.7283/',''))

    # Publication type; coming from UNAVCO data API so assume it's a dataset
    pubtype = VIVO.Dataset
    pub_uri = uri_gen('dat')

    # Article info
    if "title" in attr:
        title = attr['title'].strip()

        if 'INTERFEROGRAM' in title:
            g.add((D[pub_uri], EC.hasDatasetType, D['n803942']))
        elif 'TLS' in title:
            g.add((D[pub_uri], EC.hasDatasetType, D['n471427']))
        else:
            g.add((D[pub_uri], EC.hasDatasetType, D['n546123']))
    else:
        title = None

    # Authors
    authors = parse_authors_datacite(attr['creators'])

    # Publication date
    pub_year = (attr['publicationYear'] if 'publicationYear'
                in attr else None)
    date_uri = uri_gen('n')
    g.add((D[pub_uri], VIVO.dateTimeValue, D[date_uri]))
    add_date(D[date_uri], pub_year, g)

    # Add things to the graph
    if pubtype:
        g.add((D[pub_uri], RDF.type, pubtype))
    g.add((D[pub_uri], BIBO.doi, Literal(doi)))
    if title:
        g.add((D[pub_uri], RDFS.label, Literal(title)))

    # Loop through the list of authors, trying to check for existing
    # authors in the database
    if authors:
        for idx, (first_name, surname) in enumerate(authors):
            full_name = join_if_not_empty((first_name, surname))
            rank = idx+1
            if full_name in matchlist[0]:
                pos = matchlist[0].index(full_name)
                assign_authorship(matchlist[1][pos], g, pub_uri,
                                  full_name, matchlist, rank)
            else:
                roll = name_lookup(surname)
                matchlist = name_selecter(roll, full_name, g,
                                          first_name, surname, pub_uri,
                                          matchlist, rank)

    if "relatedIdentifiers" in attr:
        if attr['relatedIdentifiers']:
            print("Related DOIs: {}".format(attr['relatedIdentifiers']))
            for rel_doi in attr['relatedIdentifiers']:
                if rel_doi in datasets_in_vivo[0]:
                    rel_uri = (datasets_in_vivo[1]
                               [datasets_in_vivo[0].index(rel_doi)])
                # Try the local graph
                else:
                    rel_uri = next(g.subjects(BIBO.doi,
                                   Literal(rel_doi)), None)

                # All related DOIs are assumed to be children
                if rel_uri:
                    g.add((URIRef(rel_uri), OBO.BFO_0000050, D[pub_uri]))
                    g.add((D[pub_uri], OBO.BFO_0000051, URIRef(rel_uri)))
                else:
                    if pub_uri in orphans:
                        orphans[pub_uri].append(rel_doi)
                    else:
                        orphans[pub_uri] = [rel_doi]

    if "relatedPublications" in attr:
        if attr['relatedPublications']:
            print("Found related pubs, but there isn't support for this (yet)")
            # print(attr['relatedPublications'])


    if "stationCode" in attr:
        if attr['stationCode']:
            # dataset obo:RO_0002353 station
            # station obo:RO_0002234 dataset
            if stations_in_vivo[attr['stationCode']]:
                g.add((D[pub_uri], OBO.RO_0002353,
                       URIRef(stations_in_vivo[attr['stationCode']])))
                g.add((URIRef(stations_in_vivo[attr['stationCode']]),
                       OBO.RO_0002234, D[pub_uri]))
            else:
                print("Ruh roh, could not find URI for station {}".format(
                      attr['stationCode']))

    with open('matchlistfile.pickle', 'wb') as f:
        pickle.dump(matchlist, f)


# Query the data api for all DOIs
api_url = ('http://ws-beta.int.unavco.org:9090/'
          'external-aja/gps-archive/doi/summary')
r = requests.post(api_url)

if r.status_code == 200:
    data = r.json()
    for rec in data:
        doi = rec['doiKey'].replace('doi:','')
        if doi.lower() not in datasets_in_vivo[0]:
            process_doi(doi, matchlist)

else:
    sys.exit("API error! Script is aborting.\nVerify your API "
             "info in vivo_uri.py file.")

row_count = (len(data))

# Process orphans, see if they are in the graph now
print('Processing orphaned DOIs... ')
for parent in orphans:
    for orphaned_doi in orphans[parent]:
        rel_uri = next(g.subjects(BIBO.doi,
                       Literal(orphaned_doi)), None)
        if rel_uri:
           g.add((URIRef(rel_uri), OBO.BFO_0000050, D[parent]))
           g.add((D[parent], OBO.BFO_0000051, URIRef(rel_uri)))

if len(g) > 0:
    try:
        with open("rdf/datacite-update-"+timestamp+"-in.ttl", "w") as f:
            f.write(g.serialize(format=args.format))
            print(u'Wrote RDF to rdf/datacite-update-' + timestamp +
                  '-in.ttl in ' + args.format + ' format.')
    except IOError:
        # Handle the error.
        print("Failed to write RDF file. "
              "Does a directory named 'rdf' exist?")
        print("The following RDF was not saved: \n" +
              g.serialize(format=args.format))
else:
    print(u'No triples to INSERT.')

# The database will be updated directly if the --api flag is set
if args.use_api:
    if len(g) > 0:
        sparql_update(g, 'INSERT')
