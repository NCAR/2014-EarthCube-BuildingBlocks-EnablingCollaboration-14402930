#This python script reads the dataset file I have sitting on my hard drive and makes RDF out of it, yay!
#The script creates random URIs unique to this script but does not check the database for collisions with pre-existing URIs!
#Benjamin Gross 2015, mbgross@unavco.org

import re
import csv
import random
namespace = 'http://vivo.unavco.org/vivo/individual/'
usedURIs = []


f = open('dataDOIs.csv')
csv_f = csv.reader(f)
next(csv_f, None)  # skip the headers


with open('datasets.txt','w') as newfile:

    for row in csv_f:
        doi = row[0]
        authors = row [1]

        title = row[2].replace(',',', ')
        title = title.replace('\,',',')
        year = row[4]

        #mint URI for the publication date
        while True:
            vivoDateTime = 'n' + str(random.randint(100000,999999))
            if vivoDateTime not in usedURIs:
                usedURIs.append(vivoDateTime)
                break
        #mint URI for the dataset object
        while True:
            vivoDataset = 'dat' + str(random.randint(100000,999999))
            if vivoDataset not in usedURIs:
                usedURIs.append(vivoDataset)
                break

        #split our authors if multiple are separated by commas
        authorlist = authors.split(',')
        for peeps in authorlist:

            while True:
                vcardName = 'per' + str(random.randint(100000,999999))
                if vcardName not in usedURIs:
                    usedURIs.append(vcardName)
                    break
            while True:
                vivoAuthorship = 'n' + str(random.randint(100000,999999))
                if vivoAuthorship not in usedURIs:
                    usedURIs.append(vivoAuthorship)
                    break

            while True:
                vcardIndividual = 'per' + str(random.randint(100000,999999))
                if vcardIndividual not in usedURIs:
                    usedURIs.append(vcardIndividual)
                    break

            #Names need to be split into first and last names for VIVO
            name = peeps.rsplit(' ',1)
            rank = authorlist.index(peeps)+1

            #First name
            newfile.write('<'+namespace+vcardName+'> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2006/vcard/ns#Name> .\n')
            newfile.write('<'+namespace+vcardName+'> <http://www.w3.org/2006/vcard/ns#givenName> "'+name[0]+'" .\n')

            #Last name
            if len(name)>1:
                newfile.write('<'+namespace+vcardName+'> <http://www.w3.org/2006/vcard/ns#familyName> "'+name[-1]+'" .\n')

            #Authorship
            newfile.write('<'+namespace+vivoAuthorship+'> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://vivoweb.org/ontology/core#Authorship> .\n')
            newfile.write('<'+namespace+vivoAuthorship+'> <http://vivoweb.org/ontology/core#relates> <'+namespace+vcardIndividual+'> .\n')
            newfile.write('<'+namespace+vivoAuthorship+'> <http://vivoweb.org/ontology/core#rank> "'+str(rank)+'"^^<http://www.w3.org/2001/XMLSchema#int> .\n')
            newfile.write('<'+namespace+vivoDataset+'> <http://vivoweb.org/ontology/core#relatedBy> <'+namespace+vivoAuthorship+'> .\n')

            #Vcard individual
            newfile.write('<'+namespace+vcardIndividual+'> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2006/vcard/ns#Individual> .\n')
            newfile.write('<'+namespace+vcardIndividual+'> <http://www.w3.org/2006/vcard/ns#hasName> <'+namespace+vcardName+'> .\n')

        #dateTime
        newfile.write('<'+namespace+vivoDateTime+'> <http://vivoweb.org/ontology/core#dateTime> "'+year+'-01-01T00:00:00"^^<http://www.w3.org/2001/XMLSchema#dateTime> .\n')
        newfile.write('<'+namespace+vivoDateTime+'> <http://vivoweb.org/ontology/core#dateTimePrecision> <http://vivoweb.org/ontology/core#yearPrecision> .\n')
        newfile.write('<'+namespace+vivoDateTime+'> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://vivoweb.org/ontology/core#DateTimeValue> .\n')

        #vivo:dataset
        newfile.write('<'+namespace+vivoDataset+'> <http://vivoweb.org/ontology/core#dateTimeValue> <'+namespace+vivoDateTime+'> .\n')
        newfile.write('<'+namespace+vivoDataset+'> <http://www.w3.org/2000/01/rdf-schema#label> "'+title+'" .\n')
        newfile.write('<'+namespace+vivoDataset+'> <http://purl.org/ontology/bibo/doi> "'+doi+'" .\n')
        newfile.write('<'+namespace+vivoDataset+'> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://vivoweb.org/ontology/core#Dataset> .\n')
#        raw_input("Press Enter to continue...")
