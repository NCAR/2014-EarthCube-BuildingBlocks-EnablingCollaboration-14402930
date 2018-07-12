import requests

# Input: Query?
def data_api_lookup(doi):
    tries = 0
    page = 1
    base_url = 'http://ws-beta.int.unavco.org:9090/external-aja/gps-archive/doi/detail'
    data = []

    while True:
        url = "{}/{}".format(base_url, doi)

        r = requests.get(url)
        if r.status_code == 404:
            print('404 error from Dataset API')
            return None
        if r:
            rsp = r.json()
            return rsp
        if r.status_code == 200:
            continue
        elif r.status_code != 200:
            tries += 1
        elif r.status_code == 502 and tries < 6:
            print('Server error, waiting 10 seconds before retry...')
            sleep(10)
        else:
            raise Exception("Request to fetch %s returned %s" % (data_center,
                            r.status_code))
