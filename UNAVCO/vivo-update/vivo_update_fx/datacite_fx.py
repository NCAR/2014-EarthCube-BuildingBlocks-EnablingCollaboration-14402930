import requests

def datacite_lookup(doi):
    tries = 0
    payload = {'wt': 'json', 'indent': 'true', 'q': doi}
    dc_api_url = 'http://search.datacite.org/api'

    while True:
        r = requests.post(dc_api_url, params=payload)

        tries += 1
        if r.status_code == 404:
            print('doi not found on cross ref')
            # Not a crossref DOI.
            return None
        if r:
            return r.json()["response"]["docs"][0]
        if r.status_code == 502 and tries < 6:
            print('Server error, waiting 10 seconds before retry...')
            sleep(10)
        else:
            raise Exception("Request to fetch DOI %s returned %s" % (doi,
                            r.status_code))