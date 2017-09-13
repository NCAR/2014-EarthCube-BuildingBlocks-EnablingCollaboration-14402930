import requests
import argparse
import logging
from logging import handlers
# import codecs
from datetime import datetime
from rdflib import Literal, Graph, URIRef
from rdflib.namespace import Namespace
import namespace as ns
from namespace import VIVO, VCARD, OBO, BIBO, FOAF, SKOS, D, RDFS, RDF
from api_fx import (crossref_lookup, uri_gen, uri_lookup_doi, name_lookup,
                    name_selecter, assign_authorship, get_subject,
                    get_publishers, get_journals)
from json_fx import parse_publication_date, parse_authors
from utility import join_if_not_empty, add_date
try:
    import cPickle as pickle
except ImportError:
    import pickle

journallist = [[], []]
subjectlist = [[], []]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--manual', action="store_true",
                        help="Input DOIs manually.")
    parser.add_argument("--debug", action="store_true", help="Set logging "
                        "level to DEBUG.")

    # Parse
    args = parser.parse_args()

# Set up logging to file and console
LOG_FILENAME = 'logs/grabCrossref.log'
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
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=5000000,
                                               backupCount=5, encoding=None,
                                               delay=0)
handler.setLevel(LOGGING_LEVEL)
formatter = logging.Formatter(LOG_FORMAT)
handler.setFormatter(formatter)
logger.addHandler(handler)

log = logging.getLogger(__name__)

with open('matchlistfile.pickle', 'ab+') as f:
    try:
        matchlist = pickle.load(f)
    except EOFError:
        print('No matchlistfile.pickle file, new person objects will be '
              'created')
        matchlist = [[], []]

timestamp = str(datetime.now())[:-7]


def setup():
    publishers = get_publishers()
    journals = get_journals()
    return(publishers, journals)


def manual_entry():
    title = raw_input('Title: ')
    cr_result = {'title': [title]}
    pubtype = raw_input('Select a pub type, 1. Academic Article 2.'
                        ' Chapter 3. Dataset 4. Conference Paper 5. Abstract ')
    if pubtype == '1':
        cr_result["type"] = 'journal-article'
    elif pubtype == '2':
        cr_result["type"] = 'book-chapter'
    elif pubtype == '3':
        cr_result["type"] = 'dataset'
    elif pubtype == '4':
        cr_result["type"] = 'proceedings-article'
    elif pubtype == '5':
        cr_result["type"] = 'abstract'
    else:
        cr_result["type"] = None
    jtitle = raw_input('Journal title: ')
    cr_result["container-title"] = [jtitle]
    cr_result["issue"] = raw_input('Issue: ')
    cr_result["volume"] = raw_input('Volume: ')
    cr_result["page"] = raw_input('Page or page range: ')
    date = raw_input('Date, in the format YYYY,MM,DD ')
    if date:
        date = date.split(',')
        date_fix = []
        for date_part in date:
            date_part = int(date_part)
            date_fix.append(date_part)
        date = [date_fix]

        cr_result['issued'] = {'date-parts': date}
        # cr_result["issued"] = {u'date-parts': None}  # Skipping
        print(cr_result)

    authors = raw_input('Authors, e.g. Steinbeck, John; Poe, E. A ')
    authors = authors.split('; ')
    author_list = []
    for author in authors:
        family_name = author.split(', ')[0]
        given_name = author.split(', ')[1]
        author_list.append({u'given': given_name, u'family':
                            family_name})
    cr_result['author'] = author_list
    return cr_result


def gen_triples(cr_result, matchlist, publisher_list, journal_list, doi=None):
    pub_uri = uri_gen('pub', g)

    # Article info
    subjects = cr_result["subject"] if "subject" in cr_result else None
    if "title" in cr_result:
        if cr_result["title"][0]:
            title = cr_result["title"][0]
        elif cr_result["title"]:
            title = cr_result["title"].strip()

        else:
            title = None
    else:
        title = None

    # Publication type
    if cr_result["type"] == 'journal-article':
        pubtype = BIBO.AcademicArticle
    elif cr_result["type"] == 'book-chapter':
        pubtype = BIBO.Chapter
    elif cr_result["type"] == 'dataset':
        pubtype = VIVO.Dataset
    elif cr_result["type"] == 'proceedings-article':
        pubtype = VIVO.ConferencePaper
    elif cr_result["type"] == 'abstract':
        pubtype = VIVO.Abstract
    else:
        pubtype = URIRef(raw_input('Unknown publication type for {}.'
                                   ' Enter a valid URI for the type'
                                   .format(doi)))

    # Choose the longer (hopefully non-abbreviated) title
    journal = (max(cr_result["container-title"], key=len) if
               "container-title" in cr_result and
               cr_result["container-title"] else None)
    if journal:
        if journal in journal_list:
            journal_uri = journal_list[journal]

            print 'found existing '+journal
            g.add((D[pub_uri], VIVO.hasPublicationVenue,
                  URIRef(journal_uri)))

        else:
            # publisher_list = get_publishers()
            # raw_input(publisher_list)

            journal_uri = D[uri_gen('n', g)]
            journal_list[journal] = str(journal_uri)

            g.add((D[pub_uri], VIVO.hasPublicationVenue,
                  URIRef(journal_uri)))
            if pubtype == VIVO.ConferencePaper:
                g.add((URIRef(journal_uri), RDF.type, BIBO.Proceedings))
            elif pubtype == BIBO.Chapter:
                g.add((URIRef(journal_uri), RDF.type, BIBO.Book))
            else:
                g.add((URIRef(journal_uri), RDF.type, BIBO.Journal))
            g.add((URIRef(journal_uri), RDFS.label, Literal(journal)))

            if "publisher" in cr_result:
                publisher = cr_result["publisher"]
                if publisher in publisher_list:
                    publisher_uri = publisher_list[publisher]
                else:
                    publisher_uri = D[uri_gen('n', g)]
                    g.add(((URIRef(publisher_uri)), RDF.type, VIVO.Publisher))
                    g.add(((URIRef(publisher_uri)), RDFS.label,
                          Literal(publisher)))
                    publisher_list[publisher] = str(publisher_uri)
                    print('Created new publisher "' + publisher + '"')
                g.add(((URIRef(journal_uri)), VIVO.publisher,
                      URIRef(publisher_uri)))

            print 'Made new '+journal

    issue = cr_result["issue"] if "issue" in cr_result else None
    volume = cr_result["volume"] if "volume" in cr_result else None
    pages = (cr_result["page"] if "page" in cr_result and 'n/a' not in
             cr_result["page"] else None)

    # Authors
    authors = (parse_authors(cr_result) if "author" in cr_result
               else None)

    date = parse_publication_date(cr_result)

    # Publication date
    if date:
        (publication_year, publication_month, publication_day) = date
    else:
        (publication_year, publication_month, publication_day) = (None,
                                                                  None,
                                                                  None)

    date_uri = uri_gen('n', g)
    g.add((D[pub_uri], VIVO.dateTimeValue, D[date_uri]))
    add_date(D[date_uri], publication_year, g, publication_month,
             publication_day)

    # Add things to the graph
    if pubtype:
        g.add((D[pub_uri], RDF.type, pubtype))
    if doi:
        g.add((D[pub_uri], BIBO.doi, Literal(doi)))
    if issue:
        g.add((D[pub_uri], BIBO.issue, Literal(issue)))
    if volume:
        g.add((D[pub_uri], BIBO.volume, Literal(volume)))
    if title:
        g.add((D[pub_uri], RDFS.label, Literal(title)))

    # Loop through the list of authors, trying to check for existing
    # authors in the database
    if authors:
        for idx, (first_name, surname) in enumerate(authors):
            full_name = join_if_not_empty((first_name, surname))
            rank = idx+1
            if full_name in matchlist[0]:
                pos = matchlist[0].index(full_name)
                assign_authorship(matchlist[1][pos], g, pub_uri,
                                  full_name, matchlist, rank)
            else:
                roll = name_lookup(surname)
                matchlist = name_selecter(roll, full_name, g,
                                          first_name, surname, pub_uri,
                                          matchlist, rank)

    # subjects
    if subjects:
        for subject in subjects:
            # NEED TO FIND SUBJECT IN VIVO
            concept_uri = get_subject(subject, g)

            if concept_uri:
                # print 'found existing '+subject
                g.add((D[pub_uri], VIVO.hasSubjectArea,
                      URIRef(concept_uri)))
            elif subject in subjectlist[0]:
                # print 'already made a new one this round '+subject
                match = subjectlist[0].index(subject)
                subject_uri = subjectlist[1][match]
                g.add((D[pub_uri], VIVO.hasSubjectArea,
                      D[subject_uri]))
            else:
                # print 'made new '+subject
                subject_uri = uri_gen('sub', g)
                subjectlist[0].append(subject)
                subjectlist[1].append(subject_uri)
                g.add((D[pub_uri], VIVO.hasSubjectArea,
                      D[subject_uri]))
                g.add((D[subject_uri], RDF.type, SKOS.Concept))
                g.add((D[subject_uri], RDFS.label, Literal(subject)))

    if pages:
        pages = pages.split("-")
        startpage = pages[0]
        g.add((D[pub_uri], BIBO.pageStart, Literal(startpage)))
        if len(pages) > 1:
            endpage = pages[1]
            g.add((D[pub_uri], BIBO.pageEnd, Literal(endpage)))
        else:
            endpage = None


# Test doi below, do not add to VIVO
dois = ['10.1111/j.2041-6962.2012.00097.x', '10.18666/jpra-2016-v34-i2-6495 ']

# Instantiate a graph and namespace
g = Graph(namespace_manager=ns.ns_manager)


if len(dois) > 0 or args.manual is True:
    print('Setting up...')
    (publishers, journals) = setup()
    print('Publishers and journals retrieved from database')
else:
    print('No DOIs provided. Either edit grabCross.py or add --manual')
    quit()


if args.manual is True:
    dois = raw_input('Enter a comma-separated list of DOIs, or press return to'
                     ' enter one publication manually\n')
    if dois == '':
        while True:
            cr_result = manual_entry()
            if cr_result:
                gen_triples(cr_result, matchlist, publishers, journals)
            gogogo = raw_input('Okay, input another? ')
            if gogogo.lower() not in ['yes', 'y', 'oui oui']:
                break

    else:
        dois = [x.strip() for x in dois.split(',')]


for doi in dois:
    rel_uri = uri_lookup_doi(doi.lower())
    if rel_uri:
        print 'doi '+doi+' already loaded as ' + rel_uri

    else:
        cr_result = crossref_lookup(doi)  # grab metadata for the doi in json
        print doi
        if not cr_result:
            print('API error, likely a 404 from Crossref')
            res = raw_input('Do you want to add the pub info manually?')
            if res.lower() not in ['', 'no', 'n']:
                cr_result = manual_entry()

        if cr_result:
            # raw_input('we gotsa cr')
            gen_triples(cr_result, matchlist, publishers, journals, doi)
        else:
            print("Publication with DOI {} not added".format(doi))
    with open('matchlistfile.pickle', 'wb') as f:
        pickle.dump(matchlist, f)

if len(g) > 0:
    print g.serialize(format='turtle')
    try:
        with open("rdf/pubs-" + timestamp + "-in.ttl", "w") as f:
            f.write(g.serialize(format='turtle'))
            print('Wrote RDF to rdf/pubs-' + timestamp +
                  '-in.ttl in turtle format.')
    except IOError:
        # Handle the error.
        print("Failed to write RDF file. "
              "Does a directory named 'rdf' exist?")
        print("The following RDF was not saved: \n" +
              g.serialize(format='turtle'))
else:
    print('No triples to INSERT.')
