from metrics import logic, models
import logging

LOG = logging.getLogger(__name__)

ORPHAN_LOG = logging.getLogger('orphans')

FRAME1_MAP = {
    '': models.LANDING_PAGE,
    'webinar-invitation-elife-peer-review-explained-randy-schekman': '0ec94dac',
    'secure-your-space-elife-peer-review-workshop-harvard-th-chan-school-public-health': '6a9313db',
    'still-time-attend-elifestem-cell-reports-peer-review-workshop-isscr-2017': '6a9313db',
    'apply-now-attend-elifestem-cell-reports-peer-review-workshop-isscr-2017': '6a9313db',
    'apply-now-attend-elife-peer-review-workshop-harvard-th-chan-school-public-health': '6a9313db',
    'still-time-apply-elifestem-cell-reports-peer-review-workshop-isscr-2017': '6a9313db'
}

def results_processor_frame_1(ptype, frame, rows):
    # we can use the generic processor for the elife-news/events landing page, we just need to trick the logic a little
    frame['prefix'] = '/elife-news'
    results1 = logic.generic_results_processor(ptype, frame, rows)

    # we can also use the generic processor for old /events ...
    frame['prefix'] = '/events'
    results2 = logic.generic_results_processor(ptype, frame, rows)

    # ... we just need to normalise their identifier by matching slug -> id.
    for row in results2:
        try:
            row['identifier'] = FRAME1_MAP[row['identifier']]
        except KeyError:
            ORPHAN_LOG.info(row['identifier'], extra={'row': row})
            row['identifier'] = None

    # remove any uncountable/orphan rows
    results2 = [row for row in results2 if row['identifier']]

    return results1 + results2
