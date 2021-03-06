#!/usr/bin/python
# -*- coding: utf-8 -*- 


import csv, requests, json, getopt, sys, pprint

def usage():
    print """Create a csv file with crosscite keywords appended to the last column. 
Usage : kwupdate [-i <infile> | -d doi] -o <outfile> -c <doi_column_location>
    """
    
def main(argv):
    infname, outfname, doi_col = None, None, None 
    
    try:                                
        opts, args = getopt.getopt(argv, "hi:o:d:c:", ["help", "doi=", "infile=","outfile=","column="]) 
    except getopt.GetoptError:           
        usage()                          
        sys.exit(2)  

    for opt, arg in opts:                
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-i", "--infile"): 
            infname = arg   
        elif opt in ("-d", "--doi"): 
            doi = arg
        elif opt in ("-o", "--outfile"): 
            outfname = arg   
        elif opt in ("-c", "--column"): 
            doi_col = int(arg)-1   
            
    if infname and outfname and doi_col :
        
        with open(infname, "rU") as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            reader.next()
            
            with open(outfname, "wb") as outfile:
                writer = csv.writer(outfile, dialect=csv.excel)
                for i,row in enumerate(reader):
                    doi = row[doi_col]
                    
                    if doi :
                        r = requests.get('http://dx.doi.org/'+doi,headers={'Accept': 'application/vnd.citationstyles.csl+json'})
                        
                        print doi
                        if r.status_code == 200 :
                            try:
                                robj = json.loads(r.text)
                                
                                if robj.has_key('subject'):
                                    row.append( ";".join(robj['subject']) )
                                else:
                                    row.append( '' )
                                    
                                writer.writerow(row)
                            except:
                                print "\tThere was a problem (check JSON output) with the doi %s." % doi
                                pass                                
                    else:
                        print "No DOI in column."
    elif doi :
        print doi
        r = requests.get('http://dx.doi.org/'+doi,headers={'Accept': 'application/vnd.citationstyles.csl+json'})
        if r.status_code == 200 :
            try:
                pprint.PrettyPrinter(indent=4).pprint(json.loads(r.text.encode("utf-8")))
            except:
                print "\tThere was a problem (check JSON output) with the doi %s." % doi
                pass
        
    else:
        usage()
        sys.exit()
        
if __name__ == "__main__":
   main(sys.argv[1:])