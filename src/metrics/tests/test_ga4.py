from datetime import datetime
from metrics import ga4

def test_build_ga4_query__queries_for_frame():
    expected = {
        "dimensions": [{"name": "pagePathPlusQueryString"}],
        "metrics": [{"name": "sessions"}],
        "dateRanges": [{"startDate": "2023-01-01",
                        "endDate": "2023-01-31"}],
        "dimensionFilter": {
            "filter": {
                "fieldName": "pagePathPlusQueryString",
                "stringFilter": {
                    "matchType": "BEGINS_WITH",
                    "value": "/inside-elife"}}},
        "limit": "10000"}

    start_dt = datetime(year=2023, month=1, day=1)
    end_dt = datetime(year=2023, month=1, day=31)

    frame = {'prefix': '/inside-elife'}

    actual = ga4.build_ga4_query__queries_for_frame(None, frame, start_dt, end_dt)
    assert actual == expected
