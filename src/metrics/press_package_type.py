from .logic import apply_query_to_list, generic_ga_filter

def query_processor_frame_1(ptype, frame, query_list):
    query = generic_ga_filter("/elife-news")
    return apply_query_to_list(query, query_list)
