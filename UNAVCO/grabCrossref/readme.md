# UNAVCO

##Project personnel 

Name  | Email | Title | Role
------------- | ------------- | ------------- | -------------
Benjamin Gross | mbgross@unavco.org | Content Specialist/Data Tech II | Ingest
Chuck Meertens | chuckm@unavco.org | Director of Geodetic Data Services | Data
Fran Boler | boler@unavco.org | Project Manager III | Data
Linda Rowan | rowan@unavco.org | External Affairs Director | Co-PI
Doug Ertz | ertz@unavco.org | Project Manager III | IT

##What's grabCrossref?

The grabCrossref will attempt to lookup publication information given a list of DOIs. It utilizes the Crossref api to grab publication metadata in JSON format. It parses the metadata and formats it into VIVO-friendly RDF. Along the way, the script tries to match objects with those that already exist in your VIVO installation using VIVO's query API. This implementation is very crude at this point, and I take no responsibility for any disasters that this code will bring upon your VIVO or your sanity. 

##Using the script

###Set DOIs to look up 
The list of DOIs to look up can be changed toward the top of grabCrossref.py. Look for dois = ['doi1','doi2', etc.]

###Set VIVO Query API credentials
Edit api_fx.py and add the username and password of an authorized VIVO user. The root VIVO account has permission by default, but make sure you don't have any security concerns about sending the username and password unencrypted over your network.
Also set your api url and namespace. For most installations, you will just have to change the domain at the front of the address.

###Run the script...
...and hope nothing explodes. 