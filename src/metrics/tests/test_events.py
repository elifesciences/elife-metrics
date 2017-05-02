import json
import base
from mock import patch, Mock
from metrics import models, logic, utils
from django.test import override_settings

class One(base.TransactionBaseCase):
    def setUp(self):
        pass

    @override_settings(DEBUG=False) # bypass notify() shortcircuit
    def test_new_metric_sends_article_update(self):
        self.msid = 1234
        view_data = {
            'full': 0,
            'abstract': 0,
            'digest': 0,
            'pdf': 0,
            'doi': utils.msid2doi(self.msid),
            'source': models.GA,
            'period': models.DAY,
            'date': '2001-01-01'
        }
        expected_event = json.dumps({
            "type": "metrics",
            "contentType": "article",
            "id": self.msid,
            "metric": "views-downloads"
        })
        mock = Mock()
        with patch('metrics.events.event_bus_conn', return_value=mock):
            logic.insert_row(view_data)
            mock.publish.assert_called_once_with(Message=expected_event)

    @override_settings(DEBUG=False) # bypass notify() shortcircuit
    def test_new_citation_sends_article_update(self):
        self.msid = 1234
        citation_data = {
            'doi': utils.msid2doi(self.msid),
            'num': 1,
            'source': models.CROSSREF,
            'source_id': 'pants-party'
        }
        expected_event = json.dumps({
            "type": "metrics",
            "contentType": "article",
            "id": self.msid,
            "metric": "citations"
        })
        mock = Mock()
        with patch('metrics.events.event_bus_conn', return_value=mock):
            logic.insert_citation(citation_data)
            mock.publish.assert_called_once_with(Message=expected_event)
