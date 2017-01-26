import requests, json, math

def search(api_key, doi_prefix, page=0):
    per_page = 25 # max per page
    params = {
        'query': 'DOI("%s/*")' % doi_prefix,
        #'field': 'citedby-count', # not too useful unless we combine it with other fields
        #'view': 'COMPLETE' # verboten
        'start': page, # a 400 is thrown when we page out
        'count': per_page,
    }
    headers = {
        'Accept': 'application/json',
        'X-ELS-APIKey': api_key,
    }
    # https://dev.elsevier.com/tecdoc_cited_by_in_scopus.html
    # http://api.elsevier.com/documentation/SCOPUSSearchAPI.wadl
    url = "http://api.elsevier.com/content/search/scopus"
    response = requests.get(url, params=params, headers=headers)
    # throw an exception if we get a non-2xx response
    # http://docs.python-requests.org/en/master/user/quickstart/#response-status-codes
    response.raise_for_status()

    # deserialize their json
    data = response.json()

    # generate some boring pagination helpers
    total_results = int(data['search-results']['opensearch:totalResults']) # ll: 3592
    total_pages = int(math.ceil(total_results / per_page)) # ll: 144
    
    next_page = page + 1 if page < total_pages else None
    prev_page = page - 1 if page > 0 else None

    remaining_pages = total_pages - (page + 1 if page == 0 else page) # urgh

    # this is only temporary
    fname = "/tmp/scopus-search-results-page-%s-of-%s.json" % (page, total_pages)
    json.dump(data, open(fname, 'w'), indent=4)
    
    return {
        'total-pages': total_pages,
        'remaining-pages': remaining_pages,
        'next-page': next_page,
        'prev-page': prev_page,
        'data': data['search-results'],
    }
