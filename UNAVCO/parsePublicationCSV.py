#This python script reads a formatted publication CSV file and generates RDF in n-triple format.
#The script has strict formatting requirements to work, see the included example files.
#One major limitation of this script is that it won't match against objects already ingested into VIVO, though it will match identical names and journal titles in the input file.
#P.S. I know rdflib exists and I probably should have used it... whatever.
#Benjamin Gross 2015, mbgross@unavco.org

#settings
namespace = 'http://vivo.yourdomain.edu/vivo/individual/' #my gut says you will want to change this
inputfile = 'Citations_Example.csv'
uriList = 'uriList_example.txt' #this text file should be a list of URIs already in use, one per line. This prevents collisions with new URIs.
outputfile = 'pubRDF.txt'

import csv
import random
import sys
usedURIs = []
namelist = [[],[]]
journallist = [[],[]]
count = 0

with open(uriList) as uriFile:
    for line in uriFile:
        line = line.replace('\n','')
        usedURIs.append(line)

f = open(inputfile,'rU') # open the csv file
row_count = sum(1 for row in f)-1 #count the rows to update progress. it reads the whole file, so if your file is huge it might make sense to set this manually.
f.seek(0)
csv_f = csv.reader(f)
next(csv_f, None)  #skip the headers


with open(outputfile,'w') as newfile:
    print 'Creating RDF for '+str(row_count)+' publications...'
    for row in csv_f:
        title = row[0]
        journal_title = row[1]
        year = row[2]
        volume = row[3]
        issue = row[4]
        doi = row[5]
        authors = row[6]

        #mint URI for the publication date, making sure it doesn't already exist
        while True:
            vivoDateTime = 'n' + str(random.randint(100000,999999))
            if vivoDateTime not in usedURIs:
                usedURIs.append(vivoDateTime)
                break

        #mint URI for the publication object
        while True:
            vivoPublication = 'pub' + str(random.randint(100000,999999))
            if vivoPublication not in usedURIs:
                usedURIs.append(vivoPublication)
                break

        #vivo:AcademicArticle
        newfile.write('<'+namespace+vivoPublication+'> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://purl.org/ontology/bibo/AcademicArticle> .\n')
        newfile.write('<'+namespace+vivoPublication+'> <http://www.w3.org/2000/01/rdf-schema#label> "'+title+'"^^<http://www.w3.org/2001/XMLSchema#string> .\n')
        if doi:
            newfile.write('<'+namespace+vivoPublication+'> <http://purl.org/ontology/bibo/doi> "'+doi+'" .\n')
        if volume:
            newfile.write('<'+namespace+vivoPublication+'> <http://purl.org/ontology/bibo/volume> "'+volume+'" .\n')
        if issue:
            newfile.write('<'+namespace+vivoPublication+'> <http://purl.org/ontology/bibo/issue> "'+issue+'" .\n')

        #vivo:DateTime
        if year:
            newfile.write('<'+namespace+vivoPublication+'> <http://vivoweb.org/ontology/core#dateTimeValue> <'+namespace+vivoDateTime+'> .\n')
            newfile.write('<'+namespace+vivoDateTime+'> <http://vivoweb.org/ontology/core#dateTime> "'+year+'-01-01T00:00:00"^^<http://www.w3.org/2001/XMLSchema#dateTime> .\n')
            newfile.write('<'+namespace+vivoDateTime+'> <http://vivoweb.org/ontology/core#dateTimePrecision> <http://vivoweb.org/ontology/core#yearPrecision> .\n')
            newfile.write('<'+namespace+vivoDateTime+'> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://vivoweb.org/ontology/core#DateTimeValue> .\n')

        #bibo:Journal; check if journal with matching title exists, ignoring case
        if journal_title.upper() not in (journcheck.upper() for journcheck in journallist[0]):
            while True: #no match, mint a new uri
                biboJournal = 'n' + str(random.randint(100000,999999))
                if biboJournal not in usedURIs:
                    usedURIs.append(biboJournal)
                    break

            journallist[0].append(journal_title)
            journallist[1].append(biboJournal)

            #bibo Journal
            newfile.write('<'+namespace+biboJournal+'> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://purl.org/ontology/bibo/Journal> .\n')
            newfile.write('<'+namespace+biboJournal+'> <http://www.w3.org/2000/01/rdf-schema#label> "'+journal_title+'" .\n')


        else: #matched, use the existing uri
            pos = next(i for i,v in enumerate(journallist[0]) if v.lower() == journal_title.lower())
            biboJournal = journallist[1][pos]
        newfile.write('<'+namespace+vivoPublication+'> <http://vivoweb.org/ontology/core#hasPublicationVenue> <'+namespace+biboJournal+'> .\n')


        #split our authors if more than one (separated by semicolons in source csv)
        authorlist = authors.split('; ')
        for peeps in authorlist:

            #Names need to be split into first and last names for VIVO (separated by a comma in source)
            name = peeps.rsplit(', ',1)
            rank = authorlist.index(peeps)+1
            lastname = name[0]
            if len(name)>1: #Check if first name is blank
                firstname = name[-1]

            while True:
                vivoAuthorship = 'n' + str(random.randint(100000,999999))
                if vivoAuthorship not in usedURIs:
                    usedURIs.append(vivoAuthorship)
                    break

            #Check to see if the exact name already exists in the file, ignoring case. If not, create new vcard individual.
            if peeps.upper() not in (namecheck.upper() for namecheck in namelist[0]):
                while True:
                    vcardName = 'n' + str(random.randint(100000,999999))
                    if vcardName not in usedURIs:
                        usedURIs.append(vcardName)
                        break

                while True:
                    vcardIndividual = 'per' + str(random.randint(100000,999999))
                    if vcardIndividual not in usedURIs:
                        usedURIs.append(vcardIndividual)
                        break

                #add name and corresponding uri to the list
                namelist[0].append(peeps)
                namelist[1].append(vcardIndividual)

                #vcard individual
                newfile.write('<'+namespace+vcardIndividual+'> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2006/vcard/ns#Individual> .\n')
                newfile.write('<'+namespace+vcardIndividual+'> <http://www.w3.org/2006/vcard/ns#hasName> <'+namespace+vcardName+'> .\n')
                #match individual to authorship
                newfile.write('<'+namespace+vivoAuthorship+'> <http://vivoweb.org/ontology/core#relates> <'+namespace+vcardIndividual+'> .\n')
                #Last name
                newfile.write('<'+namespace+vcardName+'> <http://www.w3.org/2006/vcard/ns#familyName> "'+lastname+'" .\n')
                newfile.write('<'+namespace+vcardName+'> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2006/vcard/ns#Name> .\n')
                #First name
                if len(name)>1:
                    newfile.write('<'+namespace+vcardName+'> <http://www.w3.org/2006/vcard/ns#givenName> "'+firstname+'" .\n')

            else:
                pos = next(i for i,v in enumerate(namelist[0]) if v.lower() == peeps.lower())
                vcardIndividual = namelist[1][pos]
                newfile.write('<'+namespace+vivoAuthorship+'> <http://vivoweb.org/ontology/core#relates> <'+namespace+vcardIndividual+'> .\n')

            #vivo:Authorship
            newfile.write('<'+namespace+vivoAuthorship+'> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://vivoweb.org/ontology/core#Authorship> .\n')
            newfile.write('<'+namespace+vivoAuthorship+'> <http://vivoweb.org/ontology/core#rank> "'+str(rank)+'"^^<http://www.w3.org/2001/XMLSchema#int> .\n')
            newfile.write('<'+namespace+vivoPublication+'> <http://vivoweb.org/ontology/core#relatedBy> <'+namespace+vivoAuthorship+'> .\n')

        count+=1
        i = float(count)/row_count*100
        sys.stdout.write("\rProgress: %i%%" % i)
        sys.stdout.flush()

    print "\nRDF saved as "+newfile.name+"."
