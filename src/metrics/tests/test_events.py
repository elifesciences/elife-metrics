import json
import base
from mock import patch, Mock
from django.test import override_settings

class One(base.TransactionBaseCase):
    def setUp(self):
        pass

    @override_settings(DEBUG=False) # bypass notify() shortcircuit
    def test_new_citation_sends_article_update(self):
        self.msid = 1234
        cases = {
            # msid, citations, downloads, views
            self.msid: (1, 0, 0), # 1 citation
        }
        expected_event = json.dumps({
            "type": "metrics",
            "contentType": "article",
            "id": self.msid,
            "metric": "citations"
        })
        mock = Mock()
        with patch('metrics.events.event_bus_conn', return_value=mock):
            base.insert_metrics(cases)
            mock.publish.assert_called_once_with(Message=expected_event)
