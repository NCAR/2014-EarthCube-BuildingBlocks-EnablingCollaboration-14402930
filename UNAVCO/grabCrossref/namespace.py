from rdflib.namespace import Namespace, NamespaceManager
from rdflib import Graph

#Our data namespace
D = Namespace('http://vivo.unavco.org/vivo/individual/')
#The VIVO namespace
VIVO = Namespace('http://vivoweb.org/ontology/core#')
#The VCARD namespace
VCARD = Namespace('http://www.w3.org/2006/vcard/ns#')
#The OBO namespace
OBO = Namespace('http://purl.obolibrary.org/obo/')
#The BIBO namespace
BIBO = Namespace('http://purl.org/ontology/bibo/')
#The FOAF namespace
FOAF = Namespace('http://xmlns.com/foaf/0.1/')
#The SKOS namespace
SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')
#RDF namespace
RDF = Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#')
#CiTO namespace
CITO = Namespace('http://purl.org/spar/cito/')
#RDFS
RDFS = Namespace('http://www.w3.org/2000/01/rdf-schema#')


ns_manager = NamespaceManager(Graph())
ns_manager.bind('d', D)
ns_manager.bind('vivo', VIVO)
ns_manager.bind('vcard', VCARD)
ns_manager.bind('obo', OBO)
ns_manager.bind('bibo', BIBO)
ns_manager.bind("foaf", FOAF)
ns_manager.bind("skos", SKOS)
ns_manager.bind("cito", CITO)
ns_manager.bind("rdfs", RDFS)
