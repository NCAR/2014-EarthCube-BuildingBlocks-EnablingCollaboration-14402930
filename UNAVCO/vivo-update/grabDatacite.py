import requests
import argparse
import codecs
import pickle
from datetime import datetime
import csv
import os
import sys
from rdflib import Literal, Graph
from rdflib.namespace import Namespace
import vivo_update_fx.namespace as ns
from vivo_update_fx.namespace import (VIVO, VCARD, OBO, BIBO, FOAF, SKOS, D,
                                      RDFS, RDF, EC)
from vivo_update_fx.datacite_fx import datacite_lookup
from vivo_update_fx.api_fx import (uri_gen, name_lookup,
                                   name_selecter, assign_authorship,
                                   get_datasets_in_vivo, sparql_update)
from vivo_update_fx.json_fx import parse_publication_date, parse_authors
from vivo_update_fx.utility import join_if_not_empty, add_date, load_matchlist
journallist = [[], []]
subjectlist = [[], []]
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

# Query datacite for UNAVCO DOIs
while True:
    api_url = 'http://search.datacite.org/api'
    payload = {'q': 'doi:10.7283*', 'fq': 'has_metadata:true', 'rows':
               '999999', 'wt': 'csv', 'fq': 'is_active:true',
               'fl': 'doi'}
    r = requests.post(api_url, params=payload)

    if r.status_code == 200:
        f = r.iter_lines()
        row_count = sum(1 for row in f) - 1  # Count the rows for progress %
        f = r.iter_lines()  # Reload the data
        csv_f = csv.reader(f)
        next(csv_f, None)  # skip the headers
        break

    else:
        sys.exit("Datacite API error! Script is aborting.\nVerify your API "
                 "info in vivo_uri.py file.")

datasets_in_vivo = get_datasets_in_vivo()

for row in csv_f:
    doi = row[0]

    if doi not in datasets_in_vivo[0]:  # It's not already in VIVO
        # Grab full metadata for the doi in json format
        cr_result = datacite_lookup(doi)
        print('\nProcessing ' + doi + '\n')
        if cr_result:
            # Publication type
            if cr_result["resourceTypeGeneral"] == 'Dataset':
                pubtype = VIVO.Dataset
            else:
                pubtype = None
                print('Not a Dataset type: ' + doi + '. Skipping@!')
                continue
            pub_uri = uri_gen('dat')

            # Article info
            subjects = cr_result["subject"] if "subject" in cr_result else None
            if "title" in cr_result:

                if cr_result["title"][0]:
                    s = ", "
                    title = s.join(cr_result["title"])
                    if 'INTERFEROGRAM' in title:
                        g.add((D[pub_uri], EC.hasDatasetType, D['n803942']))
                    elif 'TLS' in title:
                        g.add((D[pub_uri], EC.hasDatasetType, D['n471427']))
                    else:
                        g.add((D[pub_uri], EC.hasDatasetType, D['n546123']))

                elif cr_result["title"]:
                    title = cr_result["title"].strip()

                else:
                    title = None
            else:
                title = None

            # Authors
            authors = (parse_authors(cr_result) if "creator" in cr_result
                       else None)

            # Publication date
            pub_year = (cr_result["publicationYear"] if "publicationYear"
                        in cr_result else None)
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

            if "relatedIdentifier" in cr_result:
                for rel_doi in cr_result["relatedIdentifier"]:
                    if ':DOI:doi:' in rel_doi:
                        rel_doi = rel_doi.split(':DOI:doi:')
                    elif ':URL:' in rel_doi:
                        print('Related document' + rel_doi +
                              ' could not be parsed')
                        rel_doi = None  # No support for related URLs
                    else:
                        rel_doi = rel_doi.split(':DOI:')

                    # Look for the DOI in VIVO
                    if rel_doi:
                        if rel_doi[1] in datasets_in_vivo[0]:
                            rel_uri = (datasets_in_vivo[1]
                                       [datasets_in_vivo[0].index(rel_doi[1])])
                        # Try the local graph
                        else:
                            rel_uri = next(g.subjects(BIBO.doi,
                                           Literal(rel_doi[1])), None)

                    if rel_uri:
                        rel_uri = rel_uri.replace(D, '')
                        if rel_doi[0] == 'IsPartOf':
                            g.add((D[pub_uri], OBO.BFO_0000050, D[rel_uri]))
                            g.add((D[rel_uri], OBO.BFO_0000051, D[pub_uri]))
                        elif rel_doi[0] == 'HasPart':
                            g.add((D[rel_uri], OBO.BFO_0000050, D[pub_uri]))
                            g.add((D[pub_uri], OBO.BFO_0000051, D[rel_uri]))
                        else:
                            print 'The related DOI could not be parsed: ' + doi

                    else:
                        print("Unable to find related DOI in database.")
            with open('matchlistfile.pickle', 'wb') as f:
                pickle.dump(matchlist, f)

        else:
            print("API error, likely a 404 from CrossRef. this script should"
                  "be extended to allow manual input of info instead")

    count += 1
    i = float(count)/row_count*100
    sys.stdout.write("\rProgress: %i%%" % i)
    sys.stdout.flush()
print('\n')

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
