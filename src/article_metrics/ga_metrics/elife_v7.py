
def path_counts_query(table_id, from_date, to_date):

    explanation = (
        # captures all articles
        "^/articles/[0-9]+"
        # including executable articles
        "(/executable)?"
        # opens optional section for matching url parameters
        "("
        # literal '?' matches the beginning of the url parameters
        # but because they're so mangled we also need to optionally match '&'
        "(\\?|&){1}"
        # non-greedy match of any other url parameter(s) between the start of the section and the ones we're looking for.
        ".*?"
        # match any of the patterns below at least once.
        "(twclid|utm_campaign|utm_source=content_alert)+"
        # non-greedy match of any other url parameter(s) between the end of our match and the end of the url
        ".*?"
        # optional section for matching url parameters should be matched zero or one times
        ")?"
        # matches the end of the url.
        # if we don't stop the matching here it goes on to match anything.
        "$"
    )
    ga_filter = "^/articles/[0-9]+(/executable)?((\\?|&){1}.*?(twclid|utm_campaign|utm_source=content_alert)+.*?)?$"
    assert ga_filter == explanation, "explanation of filter differs from the actual filter."

    return {"dimensions": [{"name": "pagePath"}],
            "metrics": [{"name": "sessions"}],
            "dateRanges": [{"startDate": from_date, "endDate": to_date}],
            "dimensionFilter": {
                "filter": {
                    "fieldName": "pagePath",
                    "stringFilter": {
                        "matchType": "FULL_REGEXP",
                        "value": ga_filter}}},
            "limit": "10000"}


def event_counts_query(table_id, from_date, to_date):
    return {}

def event_counts(row_list):
    pass

def path_counts(path_count_pairs):
    pass
