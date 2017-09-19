# Connect UNAVCO Update Scripts
This folder contains a collection of scripts to aid in updating Connect UNAVCO, either by utilizing publically available APIs or scraping webpages.

## Setup
You should be able to install the necessary dependencies with:
```
python setup.py install
```

Also, modify the variables at the top of api_settings.json.example and rename to api_settings.json.

## Scripts
- citations.py
- conceptcloud.py
- grabDatacite.py
- grants.py
- members.py
- orcid.py
- staff.py
- stations.py 

--- 
 
## citations.py
Grab citation counts from CrossRef for DOIs in Connect UNAVCO.

## conceptcloud.py
Update the word cloud on the Connect UNAVCO homepage using the latest expertise and research area counts.

## grabDatacite.py
Query datacite API for DOIs with UNAVCO's prefix (10.7283\*) and attempt to match to people with profiles in Connect UNAVCO.

## grants.py
Query NSF API for grants administered by or involving UNAVCO.

## orcid.py
Grab position and educational history from public ORCID profiles for those with ORCID IDs.

## staff.py
Scrape the UNAVCO staff page to get staff position and contact information. Note, you must be connected to UNAVCO's internal network.

## stations.py
Query the UNAVCO station info API to track new and retiring GPS stations.

## members.py
Parse UNAVCO's membership XML file and create RDF to reflect updates. Optionally, it uploads the RDF directly into VIVO using the Update API.
- - - -
Run with python members.py

-or-

Set up a cron job and run the script automatically with the --api and -a flags set.

### Options
```
usage: members.py [-h] [--api] [-a] [-f {xml,n3,turtle,nt,pretty-xml,trix}]

optional arguments:
-h, --help            show this help message and exit
--api                 Send the newly created triples to VIVO using the
                      update API. Note, there is no undo button! You have
                      been warned!
-a, --auto            Run in auto mode. Unknown organizations and people
                      will automatically be created instead of asking the
                      user for input.
-f {xml,n3,turtle,nt,pretty-xml,trix}, --format {xml,n3,turtle,nt,pretty-xml,trix}
```

---
Known issues and caveats:

*	Checks for existing URIs in VIVO, but possibility of generated uri collision
*	Does not attempt to match member reps to existing people in the database
