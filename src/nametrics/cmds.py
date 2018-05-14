# django's management.command feature is troublesome to mock
# it also encourages code to grow way out in the sticks
# this module brings it all back locally

from . import logic, models
from metrics import utils
import logging
LOG = logging.getLogger(__name__)

def ingest_command(type_list):
    try:
        supported_types = [t for t in type_list if t in models.PAGE_TYPES]
        utils.lmap(logic.update_ptype, supported_types)
    except BaseException as err:
        LOG.exception(str(err))
