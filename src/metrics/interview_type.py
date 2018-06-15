from article_metrics.utils import lmap
from .logic import generic_ga_filter

def query_processor_frame_1(ptype, frame):

    adhoc = lmap(lambda path: "ga:pagePath==%s" % path, [
        "/from-ancient-dna-to-decay-an-interview-with-jessica-metcalf",
        "/food-for-thought-an-interview-with-ana-domingos",
        "/helping-to-fight-tuberculosis-an-interview-with-david-dowdy"

        '/elife-news/chemistry-versus-cancer-an-interview-with-daniel-abankwa',
        '/elife-news/connecting-the-flight-controls-an-interview-with-tarjani-agrawal',
        '/elife-news/controlling-the-immune-response-an-interview-with-donna-macduff',
        '/elife-news/controlling-traffic-an-interview-with-ramanath-hegde',
        '/elife-news/decoding-behaviour-an-interview-with-fanny-cazettes',
        '/elife-news/developing-kidneys-an-interview-with-peter-hohenstein',
        '/elife-news/getting-under-the-skin-an-interview-with-elena-oancea',
        '/elife-news/helping-the-neighbours-an-interview-with-meredith-schuman',
        '/elife-news/imprinting-memories-an-interview-with-katja-kornysheva',
        '/elife-news/infection-statistics-and-public-health-an-interview-with-alicia-rosello',
        '/elife-news/looking-at-lipids-an-interview-with-jessica-hughes',
        '/elife-news/modelling-metabolism-an-interview-with-keren-yizhak',
        '/elife-news/of-plants-and-parasites-an-interview-with-yong-woo',
        '/elife-news/repeating-the-message-an-interview-with-yunsheng-cheng',
        '/elife-news/the-benefits-of-new-brain-cells-an-interview-with-antonia-marin-burgin',
        '/elife-news/the-regeneration-game-an-interview-with-brian-bradshaw',
        '/elife-news/understanding-the-evolution-of-defence-an-interview-with-maurijn-van-der-zee',
    ])

    interviews = [
        generic_ga_filter('/early-careers-interviews'),
        generic_ga_filter('/interviews')
    ]

    query = ",".join(interviews + adhoc)
    return query
