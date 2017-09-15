from rdflib import Literal, Graph, XSD, URIRef
from rdflib.namespace import Namespace
import namespace as ns
from api_fx import vivo_api_query, uri_gen, email_lookup
from namespace import *
import csv
import sys
import unicodedata

# Support Python 2 and 3
input_func = None
try:
    input_func = raw_input
except NameError:
    input_func = input

# Instantiate a graph and namespace
g = Graph(namespace_manager=ns.ns_manager)

count = 0

newfile = open('addExpertise.ttl', 'wb')
f = open('EarthCollab Fields of Study and Expertise.csv', 'r')
row_count = sum(1 for row in f)-1  # count the rows to update progress.
f.seek(0)
csv_f = csv.reader(f)
next(csv_f, None)  # skip the headers
next(csv_f, None)


# SurveyMonkey puts weird characters into the result document
def remove_control_characters(s):
    return s.replace("\xa0", " ").encode('utf-8')


# Retreive a list of skos:Concepts from VIVO
def get_concepts():
    query = ("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> "
             "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> "
             "PREFIX skos: <http://www.w3.org/2004/02/skos/core#> "
             "SELECT ?uri ?label "
             "WHERE { "
             "GRAPH <http://vitro.mannlib.cornell.edu/default/vitro-kb-2> "
             "{ "
             "?uri rdf:type skos:Concept . "
             "?uri rdfs:label ?label "
             "}}")

    concepts = [[], []]
    bindings = vivo_api_query(query)
    if bindings:
        for idx, concept in enumerate(bindings):
            uri = bindings[idx]["uri"]["value"]
            label = bindings[idx]["label"]["value"].lower()
            concepts[0].append(label)
            concepts[1].append(uri)
        return concepts


# Retreive a list of software from VIVO
def get_software():
    query = ("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> "
             "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> "
             "PREFIX obo: <http://purl.obolibrary.org/obo/> "
             "SELECT ?uri ?label "
             "WHERE { "
             "GRAPH <http://vitro.mannlib.cornell.edu/default/vitro-kb-2> "
             "{ "
             "?uri rdf:type obo:ERO_0000071 . "
             "?uri rdfs:label ?label "
             "}}")

    software = [[], []]
    bindings = vivo_api_query(query)
    if bindings:
        for idx, concept in enumerate(bindings):
            uri = bindings[idx]["uri"]["value"]
            label = bindings[idx]["label"]["value"].lower()
            software[0].append(label)
            software[1].append(uri)
        return software


# Retreive a list of techniques from VIVO
def get_techniques():
    query = ("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> "
             "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> "
             "PREFIX obo: <http://purl.obolibrary.org/obo/> "
             "SELECT ?uri ?label "
             "WHERE { "
             "GRAPH <http://vitro.mannlib.cornell.edu/default/vitro-kb-2> "
             "{ "
             "?uri rdf:type obo:ERO_0000007 . "
             "?uri rdfs:label ?label "
             "}}")
    techniques = [[], []]
    bindings = vivo_api_query(query)
    if bindings:
        for idx, concept in enumerate(bindings):
            uri = bindings[idx]["uri"]["value"]
            label = bindings[idx]["label"]["value"].lower()
            techniques[0].append(label)
            techniques[1].append(uri)
        return techniques


concepts = get_concepts()
software = get_software()
techniques = get_techniques()

# Loop through the survey concepts, match to exisiting VIVO concepts if
# they exist and generate rdf
for row in csv_f:
    name = row[9]
    email = row[17]
    orcid = row[19]

    if email:
        per_uri = email_lookup(email)
    else:
        per_uri = None
    if not per_uri:
        per_uri = input_func(name+' not found in VIVO. Enter the URI '
                             '(e.g. per512522)\n')

    if orcid:
        # TODO Check if ORCID already in VIVO
        # if so ensure it's assigned to the right person
        if orcid.startswith("orcid.org/"):
            orcid = 'http://'+orcid
        elif not orcid.startswith("http://orcid.org/"):
            orcid = 'http://orcid.org/'+orcid

        g.add((D[per_uri], VIVO.orcidId, URIRef(orcid)))
        g.add((URIRef(orcid), VIVO.confirmedOrcidId, D[per_uri]))
        g.add((URIRef(orcid), RDF.type, OWL.Thing))
        g.add((URIRef(orcid), VITROPUBLIC.mostSpecificType, OWL.Thing))

    cols = len(row)

    i = 20  # Shuffle on over to the techniques part of the survey
    while i < 41:
        per_concept = row[i]
        per_concept = remove_control_characters(per_concept)
        if per_concept and len(per_concept) > 0:
            if per_concept.lower() in techniques[0]:  # The technique's in VIVO
                # Pull out the uri
                uri = techniques[1][techniques[0].index(per_concept.lower())]
                # Uses technique
                g.add((D[per_uri], OBO.ERO_0000031, URIRef(uri)))
                # Technique is used by
                g.add((URIRef(uri), OBO.ERO_0000070, D[per_uri]))

            else:  # The technique is not in VIVO, make a new one
                uri = uri_gen('n')
                g.add((D[uri], RDF.type, OBO.ERO_0000007))
                g.add((D[uri], RDFS.label, Literal(per_concept,
                      datatype=XSD.string)))
                g.add((D[per_uri], OBO.ERO_0000031, D[uri]))
                g.add((D[uri], OBO.ERO_0000070, D[per_uri]))

                techniques[1].append(uri)
                techniques[0].append(per_concept.lower())
        i += 1

    i = 41  # Shuffle on over to the research areas part of the survey
    while i < 71:
        per_concept = row[i]
        per_concept = remove_control_characters(per_concept)
        if per_concept and len(per_concept) > 0:
            if per_concept.lower() in concepts[0]:
                uri = concepts[1][concepts[0].index(per_concept.lower())]
                g.add((D[per_uri], VIVO.hasResearchArea, URIRef(uri)))
                g.add((URIRef(uri), VIVO.researchAreaOf, D[per_uri]))

            elif per_concept.lower() != 'none of the above':
                uri = uri_gen('sub')
                g.add((D[uri], RDF.type, SKOS.Concept))
                g.add((D[uri], RDFS.label,
                      Literal(per_concept.capitalize(), datatype=XSD.string)))

                g.add((D[per_uri], VIVO.hasResearchArea, D[uri]))
                g.add((D[uri], VIVO.researchAreaOf, D[per_uri]))

                concepts[1].append(uri)
                concepts[0].append(per_concept.lower())
        i += 1

    i = 71  # Shuffle on over to the expertise area part of the survey
    while i < cols:
        per_concept = row[i]
        per_concept = remove_control_characters(per_concept)
        if per_concept and len(per_concept) > 0:
            # Check if the concept is in VIVO and isn't an empty string
            if per_concept.lower() in concepts[0]:
                uri = concepts[1][concepts[0].index(per_concept.lower())]
                if per_concept == '':
                    input_func('Ruh roh, concept not parsed correctly')
                g.add((D[per_uri], VLOCAL.hasExpertise, URIRef(uri)))
                g.add((URIRef(uri), VLOCAL.expertiseOf, D[per_uri]))
            elif per_concept.lower() in software[0]:
                uri = software[1][software[0].index(per_concept.lower())]
                g.add((D[per_uri], OBO.ERO_0000031, URIRef(uri)))
                g.add((URIRef(uri), OBO.ERO_0000070, D[per_uri]))

            else:  # Make new concept, keep track of it locally
                uri = uri_gen('sub')
                g.add((D[uri], RDF.type, SKOS.Concept))
                g.add((D[uri], RDFS.label, Literal(per_concept,
                      datatype=XSD.string)))
                g.add((D[per_uri], VLOCAL.hasExpertise, D[uri]))
                g.add((D[uri], VLOCAL.expertiseOf, D[per_uri]))

                concepts[1].append(uri)
                concepts[0].append(per_concept.lower())
        i += 1


#    for idx, col in enumerate(row):
#        per_concept = row [idx]
#        if per_concept:
#            print per_concept
#            if per_concept.lower() in concepts[0]:
#                uri = concepts[1][concepts[0].index(per_concept.lower())]

output = g.serialize(format='turtle')
newfile.write(output)
