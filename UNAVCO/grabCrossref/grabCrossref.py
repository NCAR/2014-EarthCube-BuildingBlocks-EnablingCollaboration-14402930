import requests
import argparse
import codecs
from rdflib import Literal, Graph
from rdflib.namespace import Namespace
import namespace as ns
from namespace import VIVO, VCARD, OBO, BIBO, FOAF, SKOS, D, RDFS, RDF
from api_fx import crossref_lookup, uri_gen, uri_lookup_doi, name_lookup, name_selecter, assign_authorship, temp_journal, data_cite, temp_subject
from json_fx import parse_publication_date, parse_authors
from utility import join_if_not_empty, add_date
journallist = [[],[]]
matchlist=[[],[]]
subjectlist = [[],[]]

#dois = ['10.1029/2011GL046680','10.1002/2013JB010901','10.1002/2013JF002842','10.1002/2014EO020001','10.1002/grl.50130','10.1002/hyp.7262','10.1016/j.epsl.2009.09.014','10.1016/j.epsl.2014.04.019','10.1016/j.gloplacha.2003.11.012','10.1016/j.jhydrol.2005.06.028','10.1016/j.jvolgeores.2007.09.008','10.1016/j.jvolgeores.2013.11.005','10.1016/j.rse.2008.09.015','10.1029/2000GC000100','10.1029/2004JB003397','10.1029/2005JB003626','10.1029/2005JB004051','10.1029/2006GL028477','10.1029/2007JF000764','10.1029/2007JF000764','10.1029/2008GL033268','10.1029/2008WR007424','10.1029/2009gc002642','10.1029/2009GL038072','10.1029/2011JC006949','10.1029/2011JC007463','10.1029/91JB00618','10.1029/GD023p0177','10.1038/384450a0','10.1126/science.1153288','10.1126/science.1153360','10.1130/0091-7613(1998)026<0435:NCFAMR>2.3.CO;2','10.1190/1.2987399','10.1785/0120000931','10.1785/gssrl.73.5.762','10.1785/gssrl.81.5.699','10.2136/vzj2006.0161','10.3189/002214307784409225','10.3189/172756409789097531','10.3189/2012JoG11J176','10.3189/2014JoG14J038']
dois = ['10.1002/humu.22073','10.1111/j.1540-6210.2008.01939_2.x','10.1029/2011GL046680','10.1002/2013JB010901','10.1130/G36702.1']


#Instantiate a graph and namespace
g = Graph(namespace_manager=ns.ns_manager)

for doi in dois:
    rel_uri = uri_lookup_doi(doi)
    if rel_uri:

        rel_uri = rel_uri.replace('http://vivo.unavco.org/vivo/individual/','')
        cr_result = crossref_lookup(doi) #grab metadata for the doi in json format

        journal = max(cr_result["container-title"], key=len) if "container-title" in cr_result else None #choose the longer (hopefully non-abbreviated) title
        if journal:
            #NEED TO FIND EXISTING JOURNALS
            #THiS was put here because it was previously left out of the script. It will create RDF to define journals for publications already in VIVO. It should be moved to the big else statement below eventually.
            journal_uri = temp_journal(journal,g)


            if journal_uri:
                print 'found existing '+journal
                g.add((D[rel_uri], VIVO.hasPublicationVenue, D[journal_uri]))
            elif journal in journallist[0]:
                print 'already made a new one this round '+journal
                match = journallist[0].index(journal)
                journal_uri = journallist[1][match]
                g.add((D[rel_uri], VIVO.hasPublicationVenue, D[journal_uri]))
            else:
                print 'made new '+journal
                journal_uri = uri_gen('n')
                journallist[0].append(journal)
                journallist[1].append(journal_uri)
                g.add((D[rel_uri], VIVO.hasPublicationVenue, D[journal_uri]))
                g.add((D[journal_uri], RDF.type, BIBO.Journal))
                g.add((D[journal_uri], RDFS.label, Literal(journal)))

    else:
        cr_result = crossref_lookup(doi) #grab metadata for the doi in json format

        pub_uri = uri_gen('pub')
        #Article info
        subjects = cr_result["subject"] if "subject" in cr_result else None
        title = cr_result["title"][0] if "title" in cr_result else None
        journal=cr_result["container-title"]
        journal = max(journal, key=len) if journal else None #choose the longer (hopefully non-abbreviated) title
        issue = cr_result["issue"] if "issue" in cr_result else None
        volume = cr_result["volume"] if "volume" in cr_result else None
        pages = cr_result["page"] if "page" in cr_result and 'n/a' not in cr_result["page"] else None

        #Authors
        authors = parse_authors(cr_result) if cr_result else None

        #Publication date
        (publication_year, publication_month, publication_day) = parse_publication_date(cr_result) \
            if cr_result else None
        date_uri = uri_gen('n')
        g.add((D[pub_uri], VIVO.dateTimeValue, D[date_uri]))
        add_date(D[date_uri], publication_year, g, publication_month, publication_day)

        #Publication type
        if cr_result["type"] == 'journal-article': pubtype = BIBO.AcademicArticle
        elif cr_result["type"] == 'book-chapter': pubtype = BIBO.chapter
        else: raw_input('ruh roh! unknown type for doi: '+doi)

        #Add things to the graph
        g.add((D[pub_uri], RDF.type, pubtype))
        g.add((D[pub_uri], BIBO.doi, Literal(doi)))
        if issue: g.add((D[pub_uri], BIBO.issue, Literal(issue)))
        if volume: g.add((D[pub_uri], BIBO.volume, Literal(volume)))
        if title: g.add((D[pub_uri], RDFS.label, Literal(title)))


        #Loop through the list of authors, trying to check for existing authors in the database
        if authors:
            for (first_name, surname) in authors:
                full_name = join_if_not_empty((first_name, surname))

                if full_name in matchlist[0]:
                    pos=matchlist[0].index(full_name)
                    assign_authorship(matchlist[1][pos],g,pub_uri,full_name,matchlist)
                else:
                    roll = name_lookup(surname)
                    matchlist = name_selecter(roll,full_name,g,first_name,surname,pub_uri,matchlist)

        #subjects
        if subjects:
            for subject in subjects:
                #NEED TO FIND SUBJECT IN VIVO
                concept_uri = temp_subject(subject,g)

                if concept_uri:
                #    print 'found existing '+subject
                    g.add((D[pub_uri], VIVO.hasSubjectArea, D[concept_uri]))
                elif subject in subjectlist[0]:
                #    print 'already made a new one this round '+subject
                    match = subjectlist[0].index(subject)
                    subject_uri = subjectlist[1][match]
                    g.add((D[pub_uri], VIVO.hasSubjectArea, D[subject_uri]))
                else:
                #    print 'made new '+subject
                    subject_uri = uri_gen('sub')
                    subjectlist[0].append(subject)
                    subjectlist[1].append(subject_uri)
                    g.add((D[pub_uri], VIVO.hasSubjectArea, D[subject_uri]))
                    g.add((D[subject_uri], RDF.type, SKOS.Concept))
                    g.add((D[subject_uri], RDFS.label, Literal(subject)))

        if pages:
            pages = pages.split("-")
            startpage = pages[0]
            g.add((D[pub_uri], BIBO.pageStart, Literal(startpage)))
            if len(pages)>1:
                endpage = pages[1]
                g.add((D[pub_uri], BIBO.pageEnd, Literal(endpage)))
            else: endpage = None

print g.serialize(format='turtle')
