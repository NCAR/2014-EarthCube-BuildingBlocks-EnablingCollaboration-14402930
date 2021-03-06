from rdflib.namespace import Namespace, NamespaceManager
from rdflib import Graph

#Our data namespace
D = Namespace('http://connect.unavco.org/individual/')
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
#LThe local namespace
VLOCAL = Namespace ('http://connect.unavco.org/ontology/vlocal#')
#WGS84 namespace
WGS84 = Namespace ('http://www.w3.org/2003/01/geo/wgs84_pos#')
#OWL namespace
OWL = Namespace('http://www.w3.org/2002/07/owl#')

VITROPUBLIC = Namespace('http://vitro.mannlib.cornell.edu/ns/vitro/public#')


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
ns_manager.bind("vlocal", VLOCAL)
ns_manager.bind("wgs84", WGS84)
ns_manager.bind("vitropublic", VITROPUBLIC)
ns_manager.bind("owl", OWL)
