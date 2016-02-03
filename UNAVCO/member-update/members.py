# The goal here is to parse our XML file. Automate this with cron jobs
# to keep our Connect UNAVCO database current.

from lxml import html
import logging
from logging import handlers
from datetime import datetime
from rdflib import Literal, Graph, XSD, URIRef
from rdflib.namespace import Namespace
import namespace as ns
import argparse
from namespace import VIVO, VCARD, OBO, BIBO, FOAF, SKOS, D, RDFS, RDF, VLOCAL
from api_fx import vivo_api_query, uri_gen, new_vcard, sparql_update

UNAVCO_ID = 'org253530'

MEMBERS_XML = 'http://www.unavco.org/community/membership/members/member-data.xml'
            
KNOWN_ORGS = {'University Of Alaska Fairbanks': 'org420111',
                'University of Colorado': 'org994657',
                'University of Hawaii': 'org450201',
                'University of Missouri - Columbia': 'org752242',
                'University of Puerto Rico at Mayaguez': 'org748742',
                'University of Texas, Arlington': 'org688241',
                'University of Wisconsin - Madison': 'org783742',
                'Virginia Polytechnic Institute State University': 'org256242',
                'CICESE': 'org162731',
                'CIDCO': 'org598477',
                'CIVISA': 'org995776',
                'INGEOMINAS - Geological Survey': 'org339385',
                'Instituto Nacional de Pesquisas Espaciais - INPE': 'org376331',
                'Instituto Nicaragense de Estudios Territoriales': 'org910471',
                'Ist. Naz. Oceanografia Geofisica Sperimentale-OGS': 
                'org656338',
                'Kandilli Observatory and Earthquake Research Insti': 
                'org984832',
                'KNMI': 'org821794',
                'MCT-Observatorio Nactional': 'org671371',
                'Montserrat Volcano Observatory': 'org362013',
                'U.S. Geological Survey, Cascade Volcano Observator': 
                'org686835',
                'Universidad Nacional Pdro Henriquez Urena': 'org774882',
                'Universite du Quebec a Montreal (UQAM)': 'org198624'}
         
REP_NICKNAMES = {'Cliff Muginer': 'Cliff Mugnier',
                'Daniel Lao Davila': u'Daniel La\u00F3 D\u00E1vila',
                'Pete LaFemina': 'Peter La Femina',
                'Michael Starek': 'Michael J. Starek',
                'Jeff Freymueller': 'Jeffrey T. Freymueller',
                'Rick Bennett': 'Richard A. Bennett',
                'Roland Burgmann': u'Roland B\u00FCrgmann',
                'Zhengkang Shen': 'Zheng-Kang Shen',
                'Kristine Larson': 'Kristine M. Larson',
                'James Foster': 'James H. Foster',
                'Robert, Jr. Smalley': 'Robert Smalley Jr.',
                'Sarah Stamps': 'D. Sarah Stamps',
                'Phillip Resor': 'Phillip G. Resor',
                'Shui-Beih yu': 'Shui-Beih Yu',
                'Angelica Munoz': u'Angelica Mu\u00F1oz',
                'Haluk Ozener': u'Haluk \u00D6zener',
                'Darcy Nascimento Jr.': 'Darcy Nascimento',
                'G. ESTEBAN VAZQUEZ': 'Guadalupe Esteban Vazquez',
                'Dr Nick Rosser': 'Nick Rosser',
                'JOAO MONICO': u'Jo\u00E3o Monico',
                'Richard Aster': 'Richard C. Aster'
                }

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default=False, dest="use_api", 
                        action="store_true", help="Send the newly created "
                        "triples to VIVO using the update API. Note, there "
                        "is no undo button! You have been warned!")
    parser.add_argument("-a","--auto", default=False, dest="auto_mode", 
                        action="store_true", help="Run in auto mode. "
                        "Unknown organizations and people will automatically "
                        "be created instead of asking the user for input.")
    parser.add_argument("-f","--format", default="turtle", choices=["xml", "n3",
                        "turtle", "nt", "pretty-xml", "trix"], help="The RDF " 
                        "format for serializing. Default is turtle.")
                        
    parser.add_argument("--debug", action="store_true", help="Set logging " 
                        "level to DEBUG.")
                        
    #Parse
    args = parser.parse_args()
    
# Set up logging to file and console

LOG_FILENAME = 'logs/members-update.log'
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
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, 
                        maxBytes=5000000, backupCount=5, encoding=None, delay=0)
handler.setLevel(LOGGING_LEVEL)
formatter = logging.Formatter(LOG_FORMAT)
handler.setFormatter(formatter)
logger.addHandler(handler)
                        
log = logging.getLogger(__name__)
    
#Instantiate a graph and namespace
g = Graph(namespace_manager=ns.ns_manager)
gout = Graph(namespace_manager=ns.ns_manager)


def get_member(institution,uri=None): 
    ''' Get existing org info using the VIVO query API
    
    The get_member function calls the VIVO query API.
    The query looks for info based on the organization name, 
    a URI supplied by the KNOWN_ORGS list or by user input.
    
    Args:
        institution: Organization name
        uri (Optional[str]): Known uri for organization. Default is None.
        
    Returns:
        Dictionary of organization info if successful, None otherwise.
    
    '''
    
    q_info = {} # Create an empty dictionary 
    
    if uri:
        query = ("PREFIX rdf: <"+RDF+"> "
                "PREFIX rdfs: <"+RDFS+"> "
                "PREFIX vlocal: <"+VLOCAL+"> "
                "PREFIX obo: <"+OBO+"> "
                "PREFIX vcard: <"+VCARD+"> "
                "PREFIX d: <"+D+"> "
                "PREFIX foaf:<"+FOAF+"> "
                "PREFIX vivo: <"+VIVO+"> "
                "SELECT ?orgLabel ?rep ?repName ?vCard ?urlObj ?url ?urlRank "
                "WHERE { "
                    "d:"+uri+" rdfs:label ?orgLabel . "
                    "d:"+uri+" a foaf:Organization . "
                    "OPTIONAL{d:"+uri+" obo:RO_0000053 ?memberRole .} "
                    "OPTIONAL{d:"+uri+" vlocal:hasLiaison ?rep . "
                    "?rep rdfs:label ?repName . } "
                    "OPTIONAL{ d:"+uri+" obo:ARG_2000028 ?vCard . } "
                      "OPTIONAL{ d:"+uri+" obo:ARG_2000028 ?vCard . "
                      " ?vCard vcard:hasURL ?urlObj . "
                      "?urlObj vcard:url ?url . } "
                    "OPTIONAL{ d:"+uri+" obo:ARG_2000028 ?vCard . "
                      "?vCard vcard:hasURL ?urlObj . "
                      "?urlObj vivo:rank ?urlRank . } "
                "} ")
                
    else:
        query = ("PREFIX rdf: <"+RDF+"> "
                "PREFIX rdfs: <"+RDFS+"> "
                "PREFIX vlocal: <"+VLOCAL+"> "
                "PREFIX obo: <"+OBO+"> "
                "PREFIX vcard: <"+VCARD+"> "
                "PREFIX foaf:<"+FOAF+"> "
                "PREFIX vivo: <"+VIVO+"> "
                "SELECT ?org ?orgLabel ?rep ?repName "
                "?vCard ?urlObj ?url ?urlRank "
                "WHERE { "
                    "?org rdfs:label ?orgLabel . "
                    "?org a foaf:Organization . "
                    "OPTIONAL{?org obo:RO_0000053 ?memberRole .} "
                    "OPTIONAL{?org vlocal:hasLiaison ?rep . "
                    "?rep rdfs:label ?repName . } "
                    "OPTIONAL{ ?org obo:ARG_2000028 ?vCard . } "
                      "OPTIONAL{ ?org obo:ARG_2000028 ?vCard . "
                      "?vCard vcard:hasURL ?urlObj . "
                      "?urlObj vcard:url ?url . } "
                    "OPTIONAL{ ?org obo:ARG_2000028 ?vCard . "
                      "?vCard vcard:hasURL ?urlObj . "
                      "?urlObj vivo:rank ?urlRank . } "                      
                    "FILTER (lcase(STR(?orgLabel)) = '"+institution.lower()+"')"
                "} ")

    bindings = vivo_api_query(query)
    if bindings:
        bindings = bindings[0] # We hope there's only one result
        if "org" in bindings:
            q_info['orgURI'] = bindings["org"]["value"].replace(D,'')
        elif uri:
            q_info['orgURI'] = uri
        else:
            q_info['orgURI'] = None 
        if "vCard" in bindings:
            q_info['vCard'] = bindings["vCard"]["value"].replace(D,'')
        else: 
            q_info['vCard'] = None
        if "url" in bindings:
            q_info['url'] = bindings["url"]["value"].replace(D,'')
            if "datatype" in bindings["url"]:
                q_info['url_datatype'] = bindings["url"]["datatype"]
            else:
                q_info['url_datatype'] = None
        else: 
            q_info['url'] = None
            q_info['url_datatype'] = None
        if "urlRank" in bindings:
            q_info['urlRank'] = bindings["urlRank"]["value"]
            if "datatype" in bindings["urlRank"]:
                q_info['urlRankDatatype'] = bindings["urlRank"]["datatype"]
            else:
                q_info['urlRankDatatype'] = None
        else: 
            q_info['urlRank'] = None
            q_info['urlRankDatatype'] = None
        if "urlObj" in bindings:
            q_info['urlObj'] = bindings["urlObj"]["value"].replace(D,'')
        else: 
            q_info['urlObj'] = None
        if "rep" in bindings:
            q_info['repURI'] = bindings["rep"]["value"].replace(D,'')
        else:
            q_info['repURI'] = None
        if "repName" in bindings:
            q_info['repName'] = bindings["repName"]["value"]
        else:
            q_info['repName'] = None
        
        log.debug('VIVO database returned '+str(q_info))    
        return q_info
    else:
        return None


# Get and parse the XML file 
try:
    xml = html.parse(MEMBERS_XML)
    log.info('Loaded XML file from '+MEMBERS_XML)
except IOError:
    log.info('Failed to load XML file from '+MEMBERS_XML)
    raise RuntimeError('Could not load XML file. See log for details.')

# Loop through all the XML elements. Our XML file has one per organization. 
for element in xml.iter():
    
    # Create an empty dictionary 
    info = {}
    
    # Populate the dictionary using element attributes
    institution = element.get('institution')
    if institution:
        log.debug('Attempting to get info for '+institution)
        if institution.endswith('-F'): # Founding institutions have this flag
            institution = institution[:-2]
        
        if institution in KNOWN_ORGS: # This helps us deal with abbreviations
            org_uri = KNOWN_ORGS[institution]
            log.debug('Using stored URI for '+institution+': '+org_uri)
            q_info = get_member(None,org_uri)
            
        else:
            q_info = get_member(institution)
                
        info['Inst'] = institution    
        info['Type'] = element.get('membertype')
        info['Rep'] = element.get('rep')
        info['Website'] = element.get('web')
        
        log.debug('Comparing to XML info: '+str(info))
            
        # Assign the variables pulled in the query                
        attempt=0
        while True:
            if q_info:
                org_uri = q_info['orgURI']
                rep_name = q_info['repName']
                vcard_uri = q_info['vCard']
                url = q_info['url']
                url_datatype = q_info['url_datatype']
                url_rank = q_info['urlRank']
                url_rank_datatype = q_info['urlRankDatatype']
                url_uri = q_info['urlObj']
                rep_uri = q_info['repURI']
                log.debug(institution+' found in database with ID '+org_uri)
                break
            elif attempt > 5: # This is taking too long, skip it
                log.warn('Skipping '+institution+
                        '. Failed to find in database.')
                break
            else:
                rep_name = vcard_uri = url = url_uri = url_rank = \
                        url_rank_datatype = rep_uri = None

                log.info(institution+' NOT found in the database. ')
                if args.auto_mode:
                    user_input = ''
                else:
                    user_input = raw_input('\n'+institution+
                        ' not found in the database. '
                        'Supply a URI (e.g. org123456) or press Enter to '
                        'create a new organization.\n ')
                if user_input == '':
                    # Create a new organization
                    org_uri = uri_gen('org')
                    role_uri = uri_gen('n')
                    g.add((D[org_uri], RDF.type, FOAF.Organization))
                    g.add((D[org_uri], RDFS.label, Literal(institution)))
                    g.add((D[org_uri], OBO.RO_0000053, D[role_uri]))
                    if info['Type'] == 'Member Institution':
                        g.add((D[role_uri], RDF.type, VIVO.MemberRole))
                    else:
                        g.add((D[role_uri], RDF.type, 
                                VLOCAL.AssociateMemberRole))
                        
                    g.add((D[role_uri], OBO.RO_0000052, D[org_uri]))                        
                    g.add((D[role_uri], VIVO.roleContributesTo, D[UNAVCO_ID]))
                    g.add((D[UNAVCO_ID], OBO.RO_0000053, D[role_uri]))
                    g.add((D[org_uri], OBO.RO_0000053, D[role_uri]))
                    
                    log.info('Added triples for new organization with uri '+
                            org_uri)
                    break      
                    
                else:
                    q_info = get_member(None,user_input)
            attempt+=1

        
        # Create triples for the organization's website url
        if info['Website']:
            # Don't do anything if the URLs are the same   
            if info['Website'] != url: 
                log.info('Updating '+institution+' website to '+info['Website'])
                if url_uri: # Add triples to the OUT graph for the old URL
                    gout.add((D[vcard_uri], VCARD.hasURL, D[url_uri]))

                    if url_datatype:
                        gout.add((D[url_uri], VCARD.url, 
                                Literal(url,datatype=URIRef(url_datatype))))
                    else:
                        gout.add((D[url_uri], VCARD.url, Literal(url)))
                
                    if url_rank:
                        if url_rank_datatype:
                            gout.add((D[url_uri], VIVO.rank, 
                                    Literal(url_rank,
                                    datatype=URIRef(url_rank_datatype))))
                        else:
                            gout.add((D[url_uri], VIVO.rank, Literal(url_rank)))
                                         
                if not vcard_uri: 
                    # Make a new vCard object if doesn't exist
                    vcard_uri = uri_gen('n')
                url_uri = uri_gen('n') # Make a new URL object
                g.add((D[org_uri], OBO.ARG_2000028, D[vcard_uri])) #vCard object
                g.add((D[vcard_uri], RDF.type, VCARD.Kind)) #vCard object
                g.add((D[vcard_uri], VCARD.hasURL, D[url_uri])) #vCard URL
                g.add((D[url_uri], RDF.type, VCARD.URL)) #vCard URL
                g.add((D[url_uri], VCARD.url, Literal(info['Website'],
                        datatype=XSD.anyURI))) #create the URL
                g.add((D[url_uri], VIVO.rank, Literal("1",datatype=XSD.int)))
                            
        # Create triples for the member representative
        while True:
            if info['Rep']:
                if info['Rep'] in REP_NICKNAMES:
                    # Change the nickname to the real name
                    info['Rep'] = REP_NICKNAMES[info['Rep']]
                                                    
                if rep_name:
                    rep_name = rep_name.split(', ',1)
                    rep_name = rep_name[1]+' '+rep_name[0]
                    
                    # Not equal, remove the old liasion triples
                    if (info['Rep'].replace(' ','').lower() != 
                            rep_name.replace(' ','').lower()):
                        gout.add((D[org_uri], VLOCAL.hasLiaison, D[rep_uri]))
                        gout.add((D[UNAVCO_ID], VLOCAL.hasLiaison, D[rep_uri]))
                        if info['Type'] == 'Member Institution':
                            gout.add((D[rep_uri], RDF.type, VLOCAL.MemberRep))
                        else:
                            gout.add((D[rep_uri], RDF.type,
                                    VLOCAL.AssociateMemberRep))
                        log.info(info['Rep']+' is not the same as '+rep_name)  
                        
                    # They are identical, exit the loop
                    else:
                        break
                
                # Create triples for a new foaf:Person      
                log.info('Updating '+institution+' representative to '+info['Rep'])        
                new_rep_name = info['Rep'].rsplit(' ',1)
                first_name = new_rep_name[0]
                last_name = new_rep_name[1]
                rep_label = last_name+', '+first_name
                
                per_uri = uri_gen('per')
                g.add((D[per_uri], RDF.type, FOAF.Person))
                g.add((D[per_uri], RDFS.label, Literal(rep_label)))
                
                vcard_uri = new_vcard(first_name,last_name,None,g)

                g.add((D[per_uri], OBO.ARG_2000028, D[vcard_uri]))
                g.add((D[org_uri], VLOCAL.hasLiaison, D[per_uri]))
                g.add((D[UNAVCO_ID], VLOCAL.hasLiaison, D[per_uri]))
                if info['Type'] == 'Member Institution':
                    g.add((D[per_uri], RDF.type, VLOCAL.MemberRep))
                else:
                    g.add((D[per_uri], RDF.type, VLOCAL.AssociateMemberRep))
                log.info('Added triples for new person with uri '+per_uri) 
                break # Our work here is done
            else:
                break     
                
timestamp = str(datetime.now())[:-7]

if len(g)>0:
    try:                    
        with open("rdf/member-update-"+timestamp+"-in.ttl", "w") as f:    
            f.write( g.serialize(format=args.format) )
            log.info('Wrote RDF to rdf/member-update-'+timestamp+'-in.ttl in '+
                        args.format+' format.')
    except IOError:
        # Handle the error.
        log.exception("Failed to write RDF file. "
                        "Does a directory named 'rdf' exist?")
        log.exception("The following RDF was not saved: \n"+
                        g.serialize(format=args.format))
else:
    log.info('No triples to INSERT.') 
    
if len(gout)>0:
    try:
        with open("rdf/member-update-"+timestamp+"-out.ttl", "w") as fout:
            fout.write( gout.serialize(format=args.format) )
            log.info('Wrote RDF to rdf/member-update-'+timestamp+'-out.ttl in '+
                        args.format+' format.')            
    except IOError:
        # Handle the error.
        log.exception("Failed to write RDF file. "
                        "Does a directory named 'rdf' exist?")
        log.exception("The following RDF was not saved: \n"+
                        gout.serialize(format=args.format))
else:
    log.info('No triples to DELETE.') 
    
# The database will be updated directly if the --api flag is set
if args.use_api:
    if len(g)>0:
        sparql_update(g,'INSERT')
    if len(gout)>0:
        sparql_update(gout,'DELETE')
