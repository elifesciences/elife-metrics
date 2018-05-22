from copy import deepcopy

#
# history loading and parsing
#

'''
            {
                "ends": null,
                "starts": "2017-06-01",
                "prefix": "/collections"
            },
            {
                "ends": "2017-05-31", 
                "starts": null,
                "prefix": "/collections",
                "path_list": [
                    "chemical-biology",
                    "tropical-disease",
                    "paleontology",
                    "human-genetics",
                    "natural-history-model-organisms",
                    "reproducibility-project-cancer-biology",
                    "plain-language-summaries"
                ]
            }

            {
                "ends": "2017-05-31", 
                "pattern": "ga:pagePath=~^/elife-news/events$", 
                "starts": null
            }
'''

type_string = {'type': 'string'}
type_list_of_strings = {'type': 'list', 'schema': type_string}
type_nullable_date = {'type': 'date', 'nullable': True}

# all variations need a start and end date
frame0 = {
    'type': 'dict',
    'schema': {
        'starts': type_nullable_date,
        'ends': type_nullable_date,
    }
}

# good for current era (2.0) objects where we can derive a pattern from just a prefix
frame1 = deepcopy(frame0)
frame1['schema']['prefix'] = type_string

# prefix is followed by a list of paths
# good for fixed lists of things
frame2 = deepcopy(frame1)
frame2['schema']['path_list'] = type_list_of_strings

# explicit pattern to pass to GA
frame3 = deepcopy(frame0)
frame3['schema']['pattern'] = type_string

# multiple explicit patterns for GA
# query is OR'd before sending to GA
frame4 = deepcopy(frame0)
frame4['schema']['pattern'] = type_list_of_strings

type_list_of_frames = {'type': 'list', 'anyof': [frame1, frame2, frame3, frame4]}

type_object = {
    'type': 'dict',
    'schema': {
        'frames': type_list_of_frames,
        'examples': type_list_of_strings,
    }
}

# final definition of our history map
schema = {
    'type': 'dict',
    'schema': type_object
}
