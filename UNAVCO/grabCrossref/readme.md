## What's grabCrossref?

The grabCrossref will attempt to lookup publication information given a list of DOIs. It utilizes the Crossref api to grab publication metadata in JSON format. It parses the metadata and formats it into VIVO-friendly RDF. Along the way, the script tries to match objects with those that already exist in your VIVO installation using VIVO's query API. This implementation is very crude at this point, and I take no responsibility for any disasters that this code will bring upon your VIVO or your sanity. 

Code snippets were used from Justin Littman's orcid2vivo script: https://github.com/gwu-libraries/orcid2vivo

## Using the script

### Set up Namespace
Edit namespace.py and change 'D' from http://connect.unavco.org to your local VIVO namespace.

### Set DOIs to look up 
There are two options for running this script. 
1. Manually, by starting the script like: python grabCrossref.py --manual
2. Edit grabCrossref.py and look for the list of DOIs in the format: dois = ['doi1','doi2', etc.]

### Set VIVO Query API credentials
Rename api_settings.example.json to api_settings.json and change the username and password to an authorized VIVO user. The root VIVO account has permission by default, but make sure you don't have any security concerns about sending the username and password unencrypted over your network.
Also set your api url and namespace. For most installations, you will just have to change the domain at the front of the address.

### Run the script...
python grabCrossref.py ...and hope nothing explodes.

## Reference material
https://wiki.duraspace.org/display/VIVO/The+SPARQL+Query+API

https://github.com/CrossRef/rest-api-doc/blob/master/rest_api.md 
http://search.crossref.org/help/api

http://rdflib.readthedocs.org/en/latest/
