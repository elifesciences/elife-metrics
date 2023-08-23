from article_metrics import models, utils
import json
from django.conf import settings
import boto3

import logging

LOG = logging.getLogger(__name__)

def sns_topic_arn(**overrides):
    "returns an arn path to an AWS event bus. this is used to connect and send/receive events"
    vals = {}
    vals.update(settings.EVENT_BUS)
    vals.update(overrides)
    # ll: arn:aws:sns:us-east-1:112634557572:bus-articles--ci
    arn = "arn:aws:sns:{region}:{subscriber}:{name}--{env}".format(**vals)
    LOG.debug("using topic arn: %s", arn)
    return arn

#
#
#

def event_bus_conn(**overrides):
    sns = boto3.resource('sns')
    return sns.Topic(sns_topic_arn(**overrides))

def notify(obj, **kwargs):
    "notify the event bus that this Citation or Metric has changes"
    if settings.DEBUG:
        LOG.debug("application is in DEBUG mode, nobody will be notified.")
        return
    try:
        msg = {
            "type": "metrics",
            "contentType": "article",
            "id": utils.pad_msid(utils.doi2msid(obj.article.doi)),
            "metric": "citations" if isinstance(obj, models.Citation) else "views-downloads"
        }
        msg_json = json.dumps(msg)
        LOG.info("writing message to event bus", extra={'bus-message': msg_json})
        conn = kwargs.pop('conn', None)
        if not conn:
            conn_overrides = kwargs.pop('conn_overrides', {})
            conn = event_bus_conn(**conn_overrides)
        conn.publish(Message=msg_json)

    except ValueError as err:
        # probably serializing value
        LOG.error("failed to serialize event bus payload %s", err, extra={'bus-message': msg_json})

    except Exception as err:
        LOG.error("unhandled error attempting to notify event bus of article change: %s", err)
