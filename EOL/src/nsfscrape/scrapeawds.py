#-*- coding: utf-8 -*- 

'''
    @author kmaull@ucar.edu
'''

import requests
import time
from lxml import etree
from html5lib import html5parser, treebuilders
import lxml
import pprint
import json
from xml.etree.ElementTree import ElementTree
import lxml.html.soupparser
import os

# --! local imports !--
import conf


'''
    Given an list of input IDs, return the award page HTML
    
    @param grant_id: the NSF grant ID 
    @return the page HTML as a string    
'''
def retrieve_awd_page (grant_id="0120736"):
    if grant_id:
        url = "http://www.nsf.gov/awardsearch/showAward?AWD_ID="+grant_id+"&HistoricalAwards=false"
        try :
            r = requests.get(url)
            if r.status_code == 200 :
                return r.text
            else:
                conf.logger.warn("awards data NOT successfully retrieved (HTTP response code: %s)", r.status_code)
                return None
        except:
            conf.logger.error("awards data NOT successfully retrieved : %s", fn, sys._getframe().f_code.co_name,sys.exc_info())
            return None
    else:
        return None
    
'''
    Given a grant id, and optional html input (@see retrieve_awd_page) parse and return a data structure (as dictionary, denoted "data" below)
    of the form :
    
        data['id'] = '<grant_id>'
        data['abstract'] = '<parsed_abstract>'
        data['publications'] = [<parsed_citation_1>,<parsed_citation_2>, ...,<parsed_citation_n>]
        
    The NSF page also includes a number of other items in a tabular form (PI, award amount, etc.) which are encoded in 
        
        data['<table_attribute_label'>] = '<table_value_string>'
        ...
    
    If htm_input_str is False (default), then the code will look for a file in conf.HTM_OUTPUT_DIR called "@grant_id.htm"
    which should have the HTML.  This might be useful if you want to grab all the files by ID from the NSF pages and then
    process them offline if there are problems (or you want to re-process if any new data needs to be parsed).
    
    NOTE: The NSF pages are very gnarly and there is a lot of invalid HTML!
    
    @param grant_id: the grant id for which you want to parse
    @param htm_input_str: the page as a string.  If False, then parse from conf.HTM_OUTPUT_DIR + <grant_id> + ".htm"
    @return the parsed page into a data structure 
'''
def parse_award_page_htm (grant_id="0120736", htm_input_str=False):
    if grant_id :    
        data = {}
        data['id'] = grant_id
        data['abstract'] = ''
        data['publications'], data['books'] = [], []
        
        # NOTE : SOUP PARSER IS THE ONLY THING FOUND TO CRUNCK THROUGH THE HTML, WHICH APPEARS TO HAVE A FEW PROBLEMS!
        if htm_input_str:
            tree = lxml.html.soupparser.fromstring( htm_input_str )
        else:
            tree = lxml.html.soupparser.parse( conf.HTM_OUTPUT_DIR + grant_id + ".htm" ).getroot()
        
        # the NSF award information is basically locked up in a table, let's get those k/v pairs, eh?
        for n in tree.xpath('//tr'):
            if len(n) == 2 :
                attribute = n[0].xpath('./strong/text()')
                value     = n[1].text   
                
                if attribute and value :
                    attribute = attribute[0].replace(":","").strip().replace(" ","_").lower().replace("(s)","")
                    data[attribute] = value.strip()
                    
        # all the stuff we're interested in is hidden in the p/greybold areas
        for t in tree.xpath('//p/strong[@class="greybold"]'):
            title  = t.xpath('./text()')[0].lower()
            output = t.xpath('..//text()')
    
            # abstract for the project
            if title.startswith("abstract"):
                abstract = ''
                for o in output:
                    if len(o.strip())>0 and not o.strip().lower().startswith('abstract'):
                        abstract = abstract.strip() + " " +  o.strip()
                data['abstract'] = abstract           
            # books section
            elif title.startswith('books'):            
                process_citation_fragment(output, 'books', data['books'])            
            # pubs section
            elif title.startswith("publication"):
                process_citation_fragment(output, 'publication', data['publications'])
                
        return  data
    else:
        return None

'''
    Given an alleged citation fragment, try to break it apart and add it to the citation list

    @param fragment: an alleged citation 
    @param citation_section_marker: in the NSF html there are books and publication sections, this marker helps 
                                    determine what we're looking and and to make sure it is not included as a citation
    @param citation_list: the list to append the citation to 
'''
def process_citation_fragment(fragment, citation_section_marker, citation_list):
    citation = ''
    for o in fragment:                                            
        if o[0] == ',' or (len(o) == 1 and o[0] == '\n') :
            # this is the end of the citation (maybe)
            if citation.find(',') > -1:
                # this may look ugly, but ... take a look at the source pages, uh, this is tame in comparison!          
                citation = (citation + o.strip()).replace(u'\u00a0',' ').replace('&nbsp'," ").replace('"',"").replace("'","")
                citation_list.append(citation)
            citation = ''
        elif not o.lower().startswith(citation_section_marker) :
            citation = citation + o.strip()

def batch_setup_env():    
    # make sure the environment is setup with the required directories if you want to use them
    required_paths = [conf.HTM_OUTPUT_DIR, conf.JSON_OUTPUT_DIR, conf.GRANTID_INPUT_DIR]
    
    for p in required_paths :
        if not os.path.isdir(p):
            os.makedirs(p)
    
def batch_retrieve(grant_id_list=["0120736","0454454"],be_nice=1.5,store_json=False,cache=True):    
    processed = []

    if cache :
        batch_setup_env()
    
    for id in grant_id_list :        
        page = retrieve_awd_page(id.strip()) 

        if cache:
            # retrieve and store the page        
            fn = conf.HTM_OUTPUT_DIR + id + ".htm"
            fo = open(fn,"wb")
            fo.write(page)
            fo.close
            conf.logger.info("awards file %s successfully retrieved and stored", fn)
            
            # notice this will process the file on disk
            processed.append( parse_award_page_htm (id) )
            
            # slow things down if folks get touchy about rapid requests
            time.sleep(be_nice)
        else :
            # parse this page as a string as retrieved
            processed.append( parse_award_page_htm (id, htm_input_str=page) )
        
    if store_json:
        fn = conf.JSON_OUTPUT_FILE 
        fo = open(fn,"wb")
        fo.write(json.dumps({"data" : processed}))
        fo.close
        conf.logger.info("JSON file %s successfully stored", fn)
        
    return processed
        
def main():    
    
    # Example using from conf file
    with open(conf.INPUT_GRANTID_FILE, "r") as f :
        grant_ids = f.read().splitlines()
        
    results = batch_retrieve(grant_ids, store_json=True)
        
if __name__ == "__main__" : main()        