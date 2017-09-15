from rdflib import Literal, Graph, XSD
from rdflib.namespace import Namespace
import namespace as ns
from api_fx import vivo_api_query, uri_gen, email_lookup
from namespace import VIVO, VCARD, OBO, BIBO, FOAF, SKOS, D, RDFS, RDF, VLOCAL, WGS84


#Instantiate a graph and namespace
g = Graph(namespace_manager=ns.ns_manager)
softwarelist = ['GSAC','Dataworks for GNSS','GIPSY - OASIS (GOA II)','TEQC','runpkr00','GAMIT/GLOBK/TRACK','Trimble Business Center','Trimble Pivot','RTNet','Bernese','RTKLIB','GPSTk','CATS','Hector','Blocks','PyLith','ISCE','GIAnT','StaMPS','GMTSAR','GMTSAR','Abaqus','ROI_PAC','3D-Def','TDEFNODE','Coulomb','VISCO1D','Relax','RiSCAN PRO','Cyclone','Geographic Calculator','Polyworks','Quick Terrain (QT) Modeler']
        
#Retreive a list of software from VIVO
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
    
    software=[[],[]]        
    bindings = vivo_api_query(query)
    if bindings:
        for idx, concept in enumerate(bindings):
            uri = bindings[idx]["uri"]["value"].replace(D,'')
            label = bindings[idx]["label"]["value"].lower()
            software[0].append(label)
            software[1].append(uri)
        return software
             
software = get_software()

#loop through the survey concepts, match to exisiting VIVO concepts if they exist and generate rdf
for software_name in softwarelist:
    
    if software_name.lower() not in software[0]:
        uri = uri_gen('sub')
        g.add((D[uri], RDF.type, OBO.ERO_0000071))
        g.add((D[uri], RDFS.label, Literal(software_name,datatype=XSD.string)))
        print software_name+' added to ttl file'
        
    else: #make new concept, keep track of it locally
        print software_name+' is already in VIVO'

        
output = g.serialize(format='turtle')
print output
