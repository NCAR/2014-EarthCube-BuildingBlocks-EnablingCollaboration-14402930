#Right now this script makes sure all the URIs in the matchlist pickle file actually exist.
#If they don't exist, vCard triples are created and printed on the screen.

import pickle
from rdflib import Literal, Graph
from rdflib.namespace import Namespace
import namespace as ns
from namespace import VIVO, VCARD, OBO, BIBO, FOAF, SKOS, D, RDFS, RDF
from api_fx import crossref_lookup, uri_gen, person_check, type_check
from json_fx import parse_publication_date, parse_authors
from utility import join_if_not_empty, add_date
from api_fx import name_lookup


#matchlist=[[],[]]
with open('matchlistfile.pickle', 'rb') as f:
    matchlist = pickle.load(f)
added_uris=[]

#Instantiate a graph and namespace
g = Graph(namespace_manager=ns.ns_manager)

#Check to see if there, if not, create a new vCard
'''
for idx, name in enumerate(matchlist[0]):
    pos=matchlist[0].index(name)
    name=name.rsplit(' ', 1)
    last_name,first_name=name[-1],name[0]
    uri = matchlist[1][pos]
    uri_exists = uri_check(uri) #check to see if the author is there
    if uri_exists=='false' and uri not in added_uris:
        print matchlist[0][pos]+": "+matchlist[1][pos] + 'do stuff'
        name_uri = matchlist[1][idx]
        g.add((D[uri], RDF.type, VCARD.Individual))
        g.add((D[uri], VCARD.hasName, D[name_uri]))
        g.add((D[name_uri], RDF.type, VCARD.Name))
        g.add((D[name_uri], VCARD.familyName, Literal(last_name)))
        g.add((D[name_uri], VCARD.givenName, Literal(first_name)))
        g.add((D[uri], RDFS.label, Literal(last_name+', '+first_name)))
        added_uris.append(uri)

    elif uri_exists=='true' and uri not in added_uris:
        uri_type = type_check(uri) #if author is there, make sure it has a type
        if uri_type is None:
            print matchlist[0][pos]+": "+matchlist[1][pos] + 'do stuff'
            name_uri = uri_gen('n')
            g.add((D[uri], RDF.type, VCARD.Individual))
            g.add((D[uri], VCARD.hasName, D[name_uri]))
            g.add((D[name_uri], RDF.type, VCARD.Name))
            g.add((D[name_uri], VCARD.familyName, Literal(last_name)))
            g.add((D[name_uri], VCARD.givenName, Literal(first_name)))
            g.add((D[uri], RDFS.label, Literal(last_name+', '+first_name)))
            added_uris.append(uri)
'''

uri_list = person_check()

#Check to see if there, if not, remove from matchlist
for idx, name in enumerate(matchlist[0]):
    pos=matchlist[0].index(name)
    name=name.rsplit(' ', 1)
    last_name,first_name=name[-1],name[0]
    uri = matchlist[1][pos]
    if uri not in uri_list and uri not in added_uris:
        print 'removing record for '+matchlist[0][pos]+": "+matchlist[1][pos]
#        ippy = raw_input(uri + ' was not found, remove? Type y: ')
        ippy = 'y'
        if ippy.lower() == 'y' or 'yes':
            del matchlist[0][pos]
            del matchlist[1][pos]

with open('matchlistfile.pickle', 'wb') as f:
    pickle.dump(matchlist, f)

if len(g) > 0:
    print g.serialize(format='turtle')
