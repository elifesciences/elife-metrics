def query_processor_frame_1(ptype, frame):
    # the defaults won't get us far for historical '/inside-elife' results, we need to craft a clever query
    # matches all top-level slug-like pages and all /elife-news/*
    query = "ga:pagePath=~^/[a-z0-9-]+$,ga:pagePath==/elife-news,ga:pagePath=~^/elife-news/.*"
    return query
