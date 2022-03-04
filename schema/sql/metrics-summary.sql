select
    -- strips doi prefix, converts result to integer to avoid leading zeros
    --cast(substr(ma.doi, 15) as bigint) as msid,
    ma.doi as id,
    mm.views,
    mm.downloads,
    coalesce(mc.scopus, 0) as scopus,
    coalesce(mc.pubmed, 0) as pubmed,
    coalesce(mc.crossref, 0) as crossref

from 
    metrics_article ma,
    
    (select 
        mm.article_id, 
        sum(mm.full + mm.abstract + mm.digest) as views,
        sum(mm.pdf) as downloads
    from 
        metrics_metric mm 
    where
        mm.source = 'ga'
        and mm.period = 'day'
    group by 
        mm.article_id
    order by
        mm.article_id) as mm

-- why the outer join?
-- this query wouldn't otherwise return results for articles with no citations.
-- what is 'lateral' and that 1=1 ?
-- 'lateral' lets the below subquery reference items above it. 
-- we need this to create the pivot table with a hook (article_id) to join it on.
-- - https://www.postgresql.org/docs/current/queries-table-expressions.html#QUERIES-LATERAL
-- the 1=1 is because we need an outer join and psql says we can't reference 'ma' (despite being 'lateral').
left join lateral
    (select
        mc.article_id,
        sum(num) filter (where source = 'scopus') as scopus,
        sum(num) filter (where source = 'pubmed') as pubmed,
        sum(num) filter (where source = 'crossref') as crossref
    from
        metrics_citation as mc
    where
        mc.article_id = ma.id
    group by
        mc.article_id
    order by
        mc.article_id) as mc ON 1=1
      
where
    ma.id = mm.article_id

order by 
    ma.id %s

;
