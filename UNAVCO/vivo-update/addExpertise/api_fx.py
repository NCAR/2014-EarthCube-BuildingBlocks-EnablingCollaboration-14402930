import requests
import random
import logging
from rdflib import Literal, Graph
from rdflib.namespace import Namespace, RDF, RDFS
import namespace
from namespace import VIVO, VCARD, OBO, BIBO, FOAF, SKOS, D, CITO
logging.basicConfig(level=logging.ERROR)

#API info
email='username'
password='password'
api_url='api_url'
aboxgraph='http://vitro.mannlib.cornell.edu/default/vitro-kb-2' #this is the default

# Support Python 2 and 3
input_func = None
try:
    input_func = raw_input
except NameError:
    input_func = input
    

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

#find a person uri based on email address
def email_lookup(email2find):
    payload = {'email': email, 'password': password, 'query': 'SELECT ?foaf WHERE {GRAPH <'+aboxgraph+'> { ?foaf <'+OBO.ARG_2000028+'> ?individual . ?individual <'+VCARD.hasEmail+'> ?email . ?email <'+VCARD.email+'> ?emailaddy . FILTER (lcase(str(?emailaddy)) = "'+email2find.lower()+'") }  }' }
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url,params=payload, headers=headers)
    uri_found=r.json()

    bindings = uri_found["results"]["bindings"]

    if bindings:
        rel_uri = bindings[0]["foaf"]["value"] if "foaf" in bindings[0] else None
        return rel_uri.replace(D,'')


#Generic query
def vivo_api_query(query):
    while True:
        payload = {'email': email, 'password': password, 'query':''+query}
        headers = {'Accept': 'application/sparql-results+json'}
        r = requests.post(api_url,params=payload, headers=headers)
        concepts_json=r.json()
        bindings = concepts_json["results"]["bindings"]
        if bindings:
            return bindings



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
            print('\n')
            for idx, val in enumerate(roll):
                    print(idx, val)

            pick = input_func("Author "+full_name+" may already exist in the database. Please choose a number or press Enter for none ")
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
                        pick = input_func('invalid input, try again ') #number out of range

                else:
                    pick = input_func('invalid input, try again ') #either not a number or not empty
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
'''
def assign_authorship(author_id,g,pub_uri,full_name,matchlist):
    authorship_uri = uri_gen('n')
    g.add((D[author_id], VIVO.relatedBy, D[authorship_uri]))
    g.add((D[authorship_uri], RDF.type, VIVO.Authorship))
    g.add((D[authorship_uri], VIVO.relates, D[author_id]))
    g.add((D[authorship_uri], VIVO.relates, D[pub_uri]))
    matchlist[0].append(full_name)
    matchlist[1].append(author_id)
    return matchlist
'''




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
                print('<'+rel_rb + '> <http://vivoweb.org/ontology/core#relates> <'+rel_uri+'> .')

def data_cite():
    r = requests.post('http://search.datacite.org/api?q=UNAVCO&fl=doi,creator,title,publisher,publicationYear,datacentre&fq=is_active:true&fq=has_metadata:true&rows=500&wt=json&indent=true')
    r = r.json()
    docs = r['response']['docs']
    dois = []
    if docs:
        for docs in docs:
            doi = docs["doi"]
            if uri_lookup_doi(doi) is None:
                print(doi)
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
            sub_uri = sub_uri.replace(D,'')
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
            sub_uri = sub_uri.replace(D,'')
            return sub_uri


def temp_smush(rel_uri,g,doi_uri):
    payload = {'email': email, 'password': password, 'query': 'SELECT ?p ?o WHERE {  <'+D+rel_uri+'> ?p ?o . } ' }
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url,params=payload, headers=headers)
    uri_found=r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        for bindings in bindings:
            p = bindings["p"]["value"] if "p" in bindings else None
            o = bindings["o"]["value"] if "o" in bindings else None
            o=o.replace(D,"")
            p=p.replace("http://purl.org/spar/cito/","")
            doi_uri=doi_uri.replace(D,"")
            g.add((D[doi_uri], CITO[p], D[o]))


    payload = {'email': email, 'password': password, 'query': 'SELECT ?s ?p2 WHERE {  ?s ?p2 <'+D+rel_uri+'> . } ' }
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url,params=payload, headers=headers)
    uri_found=r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        for bindings in bindings:
            s = bindings["s"]["value"] if "s" in bindings else None
            p2 = bindings["p2"]["value"] if "p2" in bindings else None
            s=s.replace(D,"")
            p2=p2.replace("http://purl.org/spar/cito/","")
            doi_uri=doi_uri.replace(D,"")
            g.add((D[s], CITO[p2], D[doi_uri]))

#This crazy function will match an author with a vcard or person if its an exact match, otherwise it will ask for help
def orgtype_selecter(orgname,org_uri,website,g):
    roll = ['University','Association','College','Consortium','GovernmentAgency','Institute','Laboratory','ResearchOrganization']
    if 'University' in orgname:
        g.add((D[org_uri], RDF.type, VIVO.University))
        g.add((D[org_uri], RDFS.label, Literal(orgname)))

    else:
        print('\n')
        for idx, val in enumerate(roll):
            print(idx, str(val))

        pick = input_func("Choose a type for "+orgname+". Please choose a number.")
        while True:
            if pick.isdigit():
                if int(pick) < len(roll): #make sure the number is valid
                    pick=roll[int(pick)]
                    g.add((D[org_uri], RDF.type, VIVO[pick]))
                    g.add((D[org_uri], RDFS.label, Literal(orgname)))
                    break
                else:
                    pick = input_func('invalid input, try again ') #number out of range

            else:
                pick = input_func('invalid input, try again ') #not a number

def tempname_selecter(roll,full_name,g,first_name,surname,pub_uri,matchlist,email):
    if len(roll)>0: #the api found matching last names
        exit=False
        for idx, val in enumerate(roll):
            if str(roll[idx][0]+roll[idx][2]).upper().replace(' ','').replace('.','')==full_name.replace(' ','').replace('.','').upper():
                if roll[idx][4]:
                    author_uri = str(roll[idx][4])
                    author_uri = author_uri.replace(D,'')
                    assign_email(roll[idx][3],g,email)

                else:
                    vcard_uri = str(roll[idx][3])
                    vcard_uri = vcard_uri.replace(D,'')
                    assign_email(vcard_uri,g,email)
                    author_uri = uri_gen('per')
                    g.add((D[author_uri], RDF.type, FOAF.Person))
                    g.add((D[author_uri], RDFS.label, Literal(surname+', '+first_name)))
                    g.add((D[author_uri], OBO.ARG_2000028, D[vcard_uri]))
                exit=True
                return assign_authorship(author_uri,g,pub_uri,full_name,matchlist)

                break
        if not exit:
            print('\n')
            for idx, val in enumerate(roll):
                    print(idx, val)

            pick = input_func("Author "+full_name+" may already exist in the database. Please choose a number or press Enter for none ")
            while True:
                if pick=='': #none of the above
                    author_uri = tempnew_vcard(first_name,surname,full_name,g,email) #create a new vcard individual
                    matchlist = assign_authorship(author_uri,g,pub_uri,full_name,matchlist)
                    break
                elif pick.isdigit():
                    if int(pick) < len(roll): #make sure the number is valid
                        if roll[int(pick)][4]:
                            author_uri = roll[int(pick)][4]
                            author_uri = author_uri.replace(D,'')
                            assign_email(roll[int(pick)][3],g,email)

                        else:
                            vcard_uri = roll[int(pick)][3]
                            vcard_uri = vcard_uri.replace(D,'')
                            assign_email(vcard_uri,g,email)
                            author_uri = uri_gen('per')
                            g.add((D[author_uri], RDF.type, FOAF.Person))
                            g.add((D[author_uri], RDFS.label, Literal(surname+', '+first_name)))
                            g.add((D[author_uri], OBO.ARG_2000028, D[vcard_uri]))

                        matchlist = assign_authorship(author_uri,g,pub_uri,full_name,matchlist)
                        break
                    else:
                        pick = input_func('invalid input, try again ') #number out of range

                else:
                    pick = input_func('invalid input, try again ') #either not a number or not empty
            return matchlist
    else:
        #no matches, make new uri
        vcard_uri = tempnew_vcard(first_name,surname,full_name,g,email)
        author_uri = uri_gen('per')
        g.add((D[author_uri], RDF.type, FOAF.Person))
        g.add((D[author_uri], RDFS.label, Literal(full_name)))
        g.add((D[author_uri], OBO.ARG_2000028, D[vcard_uri]))

        matchlist = assign_authorship(author_uri,g,pub_uri,full_name,matchlist)
        return matchlist


def assign_authorship(author_id,g,org_uri,full_name,matchlist):
    pos_uri = uri_gen('n')
#    g.add((D[author_id], VIVO.relatedBy, D[authorship_uri]))
#    g.add((D[authorship_uri], RDF.type, VIVO.Authorship))
#    g.add((D[authorship_uri], VIVO.relates, D[author_id]))
#    g.add((D[authorship_uri], VIVO.relates, D[pub_uri]))
    g.add((D[org_uri], VIVO.relatedBy, D[pos_uri]))
    g.add((D[pos_uri], VIVO.relates, D[org_uri]))
    g.add((D[pos_uri], VIVO.relates, D[author_id]))
    g.add((D[pos_uri], RDF.type, VIVO.FacultyPosition))
    g.add((D[pos_uri], RDFS.label, Literal("Faculty")))
    matchlist[0].append(full_name)
    matchlist[1].append(author_id)
    return matchlist

def assign_email(vcard_uri,g,email):
    if email:
        email_uri = uri_gen('n')
        g.add((D[vcard_uri], VCARD.hasEmail, D[email_uri]))
        g.add((D[email_uri], VCARD.email, Literal(email)))
        g.add((D[email_uri], RDF.type, VCARD.Email))
        g.add((D[email_uri], RDF.type, VCARD.Work))

def tempnew_vcard(first_name,last_name,full_name,g,email):
    (author_uri,name_uri) = uri_gen('per'),uri_gen('n')
    if email:
        assign_email(author_uri,g,email)
    g.add((D[author_uri], RDF.type, VCARD.Individual))
    g.add((D[author_uri], VCARD.hasName, D[name_uri]))
    g.add((D[name_uri], RDF.type, VCARD.Name))
    g.add((D[name_uri], VCARD.familyName, Literal(last_name)))
    g.add((D[name_uri], VCARD.givenName, Literal(first_name)))
    g.add((D[author_uri], RDFS.label, Literal(full_name)))
    return author_uri

def tempname_selecter2(roll,full_name,g,matchlist):
    if len(roll)>0: #the api found matching last names
        exit=False
        for idx, val in enumerate(roll):
                print(idx, val)

        pick = input_func("Author "+full_name+" may already exist in the database. To smush, type 's', or to create a new object press Enter ")
        while True:
            if pick=='': #none of the above

                break
            elif pick=='s':
                #smush!!!!
                winner = input_func('Choose the master object you want to smush others into ')

                if winner.isdigit():
                    if int(winner) < len(roll): #make sure the number is valid
                        winner_uri = roll[int(winner)][4] if roll[int(winner)][4] else roll[int(winner)][3]
                        losers = input_func('Type the numbers of objects to smush, separated by a comma ')
                        losers = losers.split(',')
                        if winner not in losers:
                            for person in losers:
                                if roll[int(person)][4]:
                                    related(roll[int(person)][4],winner_uri,g)
                                else:
                                    related(roll[int(person)][3],winner_uri,g)
                            break
                        else:
                            print("You can't smush something with itself!")




                    else:
                        pick = input_func('invalid input, try again ') #number out of range
                else:
                    pick = input_func('invalid input, try again ') #either not a number or not empty
            else:
                pick = input_func('invalid input, try again ') #either not a number or not empty
        return matchlist
    else:
        #no matches, make new uri
        vcard_uri = tempnew_vcard(first_name,surname,full_name,g,email)
        author_uri = uri_gen('per')
        g.add((D[author_uri], RDF.type, FOAF.Person))
        g.add((D[author_uri], RDFS.label, Literal(full_name)))
        g.add((D[author_uri], OBO.ARG_2000028, D[vcard_uri]))

        matchlist = assign_authorship(author_uri,g,pub_uri,full_name,matchlist)
        return matchlist

def related(rel_uri,winner_uri,g):
    payload = {'email': email, 'password': password, 'query': 'SELECT ?s WHERE {GRAPH <'+aboxgraph+'> {  ?s <http://vivoweb.org/ontology/core#relates> <'+rel_uri+'> . }} ' }
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url,params=payload, headers=headers)
    uri_found=r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        for bindings in bindings:

    #        p = bindings["p"]["value"] if "p" in bindings else None
            s = bindings["s"]["value"] if "s" in bindings else None
#            print('<'+s+'> <http://vivoweb.org/ontology/core#relates> <'+rel_uri+'> .')
            s=s.replace(D,"")
    #        p=p.replace("http://vivoweb.org/ontology/core#","")
            winner_uri=winner_uri.replace(D,"")
            g.add((D[s], VIVO.relates, D[winner_uri]))

    payload = {'email': email, 'password': password, 'query': 'CONSTRUCT {<'+rel_uri+'> ?p ?o. ?s ?p2 <'+rel_uri+'> . ?name ?p3 ?o4. } WHERE { GRAPH <http://vitro.mannlib.cornell.edu/default/vitro-kb-2> { <'+rel_uri+'> ?p ?o. ?s ?p2 <'+rel_uri+'> . OPTIONAL{<'+rel_uri+'> <http://www.w3.org/2006/vcard/ns#hasName> ?name . ?name ?p3 ?o4. }} }' }
    headers = {'Accept': 'text/plain'}
    r = requests.post(api_url,params=payload, headers=headers)
    print(r.text)

#This crazy function will match an author with a vcard or person if its an exact match, otherwise it will ask for help
def newname_selecter(roll,full_name,g,g6,first_name,surname):
    if len(roll)>0: #the api found matching last names
        exit=False
        for idx, val in enumerate(roll):
            if str(roll[idx][0]+roll[idx][2]).upper().replace(' ','').replace('.','')==full_name.replace(' ','').replace('.','').upper():
                vcard_uri = roll[int(idx)][3] #vcard individual
                vcard_uri = vcard_uri.replace(D,'') #pull out just the identifier
                if roll[int(idx)][4]:
                    per_uri = roll[int(idx)][4] #map to foaf object if it exists
                    per_uri = per_uri.replace(D,'') #pull out just the identifier

                else: #else make a foaf
                    per_uri = uri_gen('per')
                    g.add((D[per_uri], RDF.type, FOAF.Person))
                    g.add((D[per_uri], RDFS.label, Literal(full_name)))
                    g.add((D[per_uri], OBO.ARG_2000028, D[vcard_uri]))

                exit=True
                return per_uri
                break
        if not exit:
            print('\n')
            for idx, val in enumerate(roll):
                    print(idx, val)

            pick = input_func("Author "+full_name+" may already exist in the database. Please choose a number or press Enter for none ")
            while True:
                if pick=='': #none of the above
                    vcard_uri = new_vcard(first_name,surname,full_name,g) #create a new vcard individual
                    per_uri = uri_gen('per')
                    g.add((D[per_uri], RDF.type, FOAF.Person))
                    g.add((D[per_uri], RDFS.label, Literal(full_name)))
                    g.add((D[per_uri], OBO.ARG_2000028, D[vcard_uri]))
                    break
                elif pick.isdigit():
                    if int(pick) < len(roll): #make sure the number is valid
                        vcard_uri = roll[int(idx)][3] #vcard individual
                        vcard_uri = vcard_uri.replace(D,'') #pull out just the identifier
                        if roll[int(idx)][4]:
                            per_uri = roll[int(idx)][4] #map to foaf object if it exists
                            per_uri = per_uri.replace(D,'') #pull out just the identifier

                        else: #else make a foaf
                            per_uri = uri_gen('per')
                            g.add((D[per_uri], RDF.type, FOAF.Person))
                            g.add((D[per_uri], RDFS.label, Literal(full_name)))
                            g.add((D[per_uri], OBO.ARG_2000028, D[vcard_uri]))
                            #remap authorship to the new foaf
                            omganotherrelated(vcard_uri,per_uri,g,g6)

                        payload = {'email': email, 'password': password, 'query': 'SELECT ?name ?gname WHERE { <'+D+vcard_uri+'> <http://www.w3.org/2006/vcard/ns#hasName> ?name . ?name <http://www.w3.org/2006/vcard/ns#givenName> ?gname}' }
                        headers = {'Accept': 'application/sparql-results+json'}
                        r = requests.post(api_url,params=payload, headers=headers)
                        uri_found=r.json()
                        bindings = uri_found["results"]["bindings"]
                        if bindings:
                            for bindings in bindings:
                                name_uri = bindings["name"]["value"] if "name" in bindings else None
                                gname = bindings["gname"]["value"] if "gname" in bindings else None
                                name_uri = name_uri.replace(D,'') #pull out just the identifier
                                g.add((D[name_uri], VCARD.givenName, Literal(first_name)))
                                g6.add((D[name_uri], VCARD.givenName, Literal(gname)))

                        break
                    else:
                        pick = input_func('invalid input, try again ') #number out of range

                else:
                    pick = input_func('invalid input, try again ') #either not a number or not empty
            return per_uri
    else:
        #no matches, make new uri
        vcard_uri = new_vcard(first_name,surname,full_name,g)
        per_uri = uri_gen('per')
        g.add((D[per_uri], RDF.type, FOAF.Person))
        g.add((D[per_uri], RDFS.label, Literal(full_name)))
        g.add((D[per_uri], OBO.ARG_2000028, D[vcard_uri]))

        return per_uri

def omganotherrelated(rel_uri,winner_uri,g,g6):
    payload = {'email': email, 'password': password, 'query': 'SELECT ?s WHERE {GRAPH <'+aboxgraph+'> {  ?s <http://vivoweb.org/ontology/core#relates> '+D+rel_uri+'> . }} ' }
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url,params=payload, headers=headers)
    uri_found=r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        for bindings in bindings:

    #        p = bindings["p"]["value"] if "p" in bindings else None
            s = bindings["s"]["value"] if "s" in bindings else None
#            print('<'+s+'> <http://vivoweb.org/ontology/core#relates> <'+rel_uri+'> .')
            s=s.replace(D,"")
    #        p=p.replace("http://vivoweb.org/ontology/core#","")
            winner_uri=winner_uri.replace(D,"")
            g.add((D[s], VIVO.relates, D[winner_uri]))
            g6.add((D[s], VIVO.relates, D[rel_uri]))
'''
def hurdur(full_name,cfull_name,g,g6):
    payload = {'email': email, 'password': password, 'query': 'SELECT ?s WHERE {GRAPH <'+aboxgraph+'> {  ?s <http://www.w3.org/2000/01/rdf-schema#label> "'+full_name+'" . }} ' }
    headers = {'Accept': 'application/sparql-results+json'}
    r = requests.post(api_url,params=payload, headers=headers)
    uri_found=r.json()
    bindings = uri_found["results"]["bindings"]
    if bindings:
        for bindings in bindings:
            s = bindings["s"]["value"] if "s" in bindings else None
#            print('<'+s+'> <http://vivoweb.org/ontology/core#relates> <'+rel_uri+'> .')
            s=s.replace("http://vivo.unavco.org/vivo/individual/","")

            g.add((D[s], RDFS.label, Literal(cfull_name)))
            g6.add((D[s], RDFS.label, Literal(full_name)))
'''
