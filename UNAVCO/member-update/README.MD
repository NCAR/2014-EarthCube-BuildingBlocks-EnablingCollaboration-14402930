# UNAVCO Membership Update Script
This script parses UNAVCO's membership XML file and creates RDF to reflect updates. Optionally, it uploads the RDF directly into VIVO using the Update API.
- - - -

## How to
Modify the variables at the top of api_fx.py.
$ python members.py

-or-

Set up a cron job and run the script automatically with the --api and -a flags set.

##Options
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
