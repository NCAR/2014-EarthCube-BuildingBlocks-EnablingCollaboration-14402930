import requests
import random
from rdflib import Literal, Graph
from rdflib.namespace import Namespace, RDF, RDFS
import namespace
from namespace import VIVO, VCARD, OBO, BIBO, FOAF, SKOS, D, CITO


#API info
email='eml@unavco.org'
password='pass'
api_url='http://vivodev.int.unavco.org/vivo/api/sparqlQuery'
aboxgraph='http://vitro.mannlib.cornell.edu/default/vitro-kb-2' #this is the default
namespace='http://vivo.unavco.org/vivo/individual/'

#Create unique URIs
def uri_gen(prefix):
    while True:
        vivouri = prefix + str(random.randint(100000,999999))
        payload = {'email': email, 'password': password, 'query': 'ASK WHERE {GRAPH <'+aboxgraph+'> { <'+D+vivouri+'> ?p ?o . }  }' }
        r = requests.post(api_url,params=payload)
        exists=r.text
        if exists=='false':
            return vivouri
            break

        if exists not in ('true','false'):
            sys.exit("VIVO API error! Script is aborting.\nVerify your API info in vivo_uri.py file.")

#Determine if a doi exists in the VIVO database
def uri_lookup_doi(doi):
    payload = {'email': email, 'password': password, 'query': 'SELECT ?uri WHERE {GRAPH <'+aboxgraph+'> { ?uri <http://purl.org/ontology/bibo/doi> "'+doi+'" . }  }' }
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url,params=payload, headers=headers)

    uri_found=r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        rel_uri = bindings[0]["uri"]["value"] if "uri" in bindings[0] else None
        return rel_uri

#Generate a list of vcard:individuals and foaf:persons with a given last name
def name_lookup(name):
    payload = {'email': email, 'password': password, 'query': 'SELECT ?gname ?mname ?fname ?vcardname ?vcard ?foaf WHERE { GRAPH <http://vitro.mannlib.cornell.edu/default/vitro-kb-2> {?vcard <http://www.w3.org/2006/vcard/ns#hasName> ?vcardname .  ?vcardname <http://www.w3.org/2006/vcard/ns#givenName> ?gname.  ?vcardname <http://www.w3.org/2006/vcard/ns#familyName> ?fname . FILTER (STR(?fname)="'+name+'") OPTIONAL{?foaf <http://purl.obolibrary.org/obo/ARG_2000028> ?vcard . }OPTIONAL{?vcardname <http://vivoweb.org/ontology/core#middleName> ?mname .}}}' }
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url,params=payload, headers=headers)
    matched_names=r.json()

    bindings = matched_names["results"]["bindings"]
    roll=[]
    for bindings in bindings:
        givenname = bindings["gname"]["value"] if "gname" in bindings else ''
        midname = bindings["mname"]["value"] if "mname" in bindings else ''
        familyname = bindings["fname"]["value"] if "fname" in bindings else ''
        familyname = bindings["fname"]["value"] if "fname" in bindings else ''
        vcard_uri = bindings["vcard"]["value"] if "vcard" in bindings else ''
        foaf_uri = bindings["foaf"]["value"] if "foaf" in bindings else ''
        preroll = []
        preroll.append(givenname)
        preroll.append(midname)
        preroll.append(familyname)
        preroll.append(vcard_uri)
        preroll.append(foaf_uri)
        roll.append(preroll)
    return roll

#Return the crossref metadata, given a doi
def crossref_lookup(doi):
    #derived from orcid2vivo
    r = requests.get('http://api.crossref.org/works/%s' % doi)
    if r.status_code == 404:
        #Not a crossref DOI.
        return None
    if r:
        return r.json()["message"]
    else:
        raise Exception("Request to fetch DOI %s returned %s" % (doi, r.status_code))

#This crazy function will match an author with a vcard or person if its an exact match, otherwise it will ask for help
def name_selecter(roll,full_name,g,first_name,surname,pub_uri,matchlist):
    if len(roll)>0: #the api found matching last names
        exit=False
        for idx, val in enumerate(roll):
            if str(roll[idx][0]+roll[idx][2]).upper().replace(' ','').replace('.','')==full_name.replace(' ','').replace('.','').upper():
                author_uri = roll[int(idx)][4] if roll[int(idx)][4] else roll[int(idx)][3] #map to foaf object if it exists, otherwise vcard individual
                author_uri = author_uri.replace(D,'') #pull out just the identifier
                matchlist = assign_authorship(author_uri,g,pub_uri,full_name,matchlist)
                exit=True
                return matchlist
                break
        if not exit:
            print '\n'
            for idx, val in enumerate(roll):
                    print idx, val

            pick = raw_input("Author "+full_name+" may already exist in the database. Please choose a number or press Enter for none ")
            while True:
                if pick=='': #none of the above
                    author_uri = new_vcard(first_name,surname,full_name,g) #create a new vcard individual
                    matchlist = assign_authorship(author_uri,g,pub_uri,full_name,matchlist)
                    break
                elif pick.isdigit():
                    if int(pick) < len(roll): #make sure the number is valid
                        author_uri = roll[int(pick)][4] if roll[int(pick)][4] else roll[int(pick)][3] #map to foaf object if it exists, otherwise vcard individual
                        author_uri = author_uri.replace(D,'') #pull out just the identifier
                        matchlist = assign_authorship(author_uri,g,pub_uri,full_name,matchlist)
                        break
                    else:
                        pick = raw_input('invalid input, try again ') #number out of range

                else:
                    pick = raw_input('invalid input, try again ') #either not a number or not empty
            return matchlist
    else:
        #no matches, make new uri
        author_uri = new_vcard(first_name,surname,full_name,g)
        matchlist = assign_authorship(author_uri,g,pub_uri,full_name,matchlist)
        return matchlist


def new_vcard(first_name,last_name,full_name,g):
    (author_uri,name_uri) = uri_gen('per'),uri_gen('n')
    g.add((D[author_uri], RDF.type, VCARD.Individual))
    g.add((D[author_uri], VCARD.hasName, D[name_uri]))
    g.add((D[name_uri], RDF.type, VCARD.Name))
    g.add((D[name_uri], VCARD.familyName, Literal(last_name)))
    g.add((D[name_uri], VCARD.givenName, Literal(first_name)))
    g.add((D[author_uri], RDFS.label, Literal(full_name)))
    return author_uri

def assign_authorship(author_id,g,pub_uri,full_name,matchlist):
    authorship_uri = uri_gen('n')
    g.add((D[author_id], VIVO.relatedBy, D[authorship_uri]))
    g.add((D[authorship_uri], RDF.type, VIVO.Authorship))
    g.add((D[authorship_uri], VIVO.relates, D[author_id]))
    g.add((D[authorship_uri], VIVO.relates, D[pub_uri]))
    matchlist[0].append(full_name)
    matchlist[1].append(author_id)
    return matchlist


#TEMPORARY!!!!!!
def temp_delrb(rel_uri,g):
    payload = {'email': email, 'password': password, 'query': 'SELECT ?rbper ?something WHERE {  <'+rel_uri+'> <http://vivoweb.org/ontology/core#relatedBy> ?auth . ?auth <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://vivoweb.org/ontology/core#Authorship> . ?auth <http://vivoweb.org/ontology/core#relates> ?rbper . ?rbper <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>  <http://www.w3.org/2006/vcard/ns#Individual> . ?rbper <http://vivoweb.org/ontology/core#relates> ?something . } ' }
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url,params=payload, headers=headers)
    uri_found=r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        for bindings in bindings:
            rel_uri = bindings["something"]["value"] if "something" in bindings else None
            rel_rb = bindings["rbper"]["value"] if "rbper" in bindings else None
            if rel_uri and rel_rb:
                print '<'+rel_rb + '> <http://vivoweb.org/ontology/core#relates> <'+rel_uri+'> .'

def data_cite():
    r = requests.post('http://search.datacite.org/api?q=UNAVCO&fl=doi,creator,title,publisher,publicationYear,datacentre&fq=is_active:true&fq=has_metadata:true&rows=500&wt=json&indent=true')
    r = r.json()
    docs = r['response']['docs']
    dois = []
    if docs:
        for docs in docs:
            doi = docs["doi"]
            if uri_lookup_doi(doi) is None:
                print doi
            dois.append(doi)
        return dois

def temp_subject(concept,g):
    payload = {'email': email, 'password': password, 'query': 'SELECT ?suburi WHERE { ?suburi <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2004/02/skos/core#Concept> . ?suburi <http://www.w3.org/2000/01/rdf-schema#label> "'+concept+'" . } ' }
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url,params=payload, headers=headers)
    uri_found=r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        for bindings in bindings:
            sub_uri = bindings["suburi"]["value"] if "suburi" in bindings else None
            sub_uri = sub_uri.replace('http://vivo.unavco.org/vivo/individual/','')
            return sub_uri


def temp_journal(concept,g):
    payload = {'email': email, 'password': password, 'query': 'SELECT ?suburi WHERE { ?suburi <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://purl.org/ontology/bibo/Journal> . ?suburi <http://www.w3.org/2000/01/rdf-schema#label> "'+concept+'" . } ' }
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url,params=payload, headers=headers)
    uri_found=r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        for bindings in bindings:
            sub_uri = bindings["suburi"]["value"] if "suburi" in bindings else None
            sub_uri = sub_uri.replace('http://vivo.unavco.org/vivo/individual/','')
            return sub_uri


def temp_smush(rel_uri,g,doi_uri):
    payload = {'email': email, 'password': password, 'query': 'SELECT ?p ?o WHERE {  <http://vivo.unavco.org/vivo/individual/'+rel_uri+'> ?p ?o . } ' }
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url,params=payload, headers=headers)
    uri_found=r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        for bindings in bindings:
            p = bindings["p"]["value"] if "p" in bindings else None
            o = bindings["o"]["value"] if "o" in bindings else None
            o=o.replace("http://vivo.unavco.org/vivo/individual/","")
            p=p.replace("http://purl.org/spar/cito/","")
            doi_uri=doi_uri.replace("http://vivo.unavco.org/vivo/individual/","")
            g.add((D[doi_uri], CITO[p], D[o]))


    payload = {'email': email, 'password': password, 'query': 'SELECT ?s ?p2 WHERE {  ?s ?p2 <http://vivo.unavco.org/vivo/individual/'+rel_uri+'> . } ' }
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url,params=payload, headers=headers)
    uri_found=r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        for bindings in bindings:
            s = bindings["s"]["value"] if "s" in bindings else None
            p2 = bindings["p2"]["value"] if "p2" in bindings else None
            s=s.replace("http://vivo.unavco.org/vivo/individual/","")
            p2=p2.replace("http://purl.org/spar/cito/","")
            doi_uri=doi_uri.replace("http://vivo.unavco.org/vivo/individual/","")
            g.add((D[s], CITO[p2], D[doi_uri]))
