
def query(from_date, to_date):
    return {'dateRanges': [{'startDate': from_date,
                            'endDate': to_date}],
            'dimensionFilter': {'filter': {'fieldName': 'pagePath',
                                           'stringFilter': {'matchType': 'BEGINS_WITH',
                                                            'value': '/article'}}},
            'dimensions': [{'name': 'date'}, {'name': 'pagePath'}],
            'metricAggregations': ['TOTAL'],
            'metrics': [{'name': 'screenPageViewsPerSession'}],
            'offset': '10000'}
