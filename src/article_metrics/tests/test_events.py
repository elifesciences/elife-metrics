import pytest
import json
from unittest.mock import patch, Mock
from article_metrics import models, logic
from django.test import override_settings

@override_settings(DEBUG=False) # bypass notify() shortcircuit
@pytest.mark.django_db(transaction=True)
def test_new_metric_sends_article_update():
    view_data = {
        'full': 0,
        'abstract': 0,
        'digest': 0,
        'pdf': 0,
        'doi': '10.7554/eLife.01234',
        'source': models.GA,
        'period': models.DAY,
        'date': '2001-01-01'
    }
    expected_event = json.dumps({
        "type": "metrics",
        "contentType": "article",
        "id": "01234",
        "metric": "views-downloads"
    })
    mock = Mock()
    with patch('article_metrics.events.event_bus_conn', return_value=mock):
        logic.insert_row(view_data)
        logic.recently_updated_article_notifications()
        mock.publish.assert_called_once_with(Message=expected_event)

@override_settings(DEBUG=False) # bypass notify() shortcircuit
@pytest.mark.django_db(transaction=True)
def test_new_citation_sends_article_update():
    citation_data = {
        'doi': '10.7554/eLife.01234',
        'num': 1,
        'source': models.CROSSREF,
        'source_id': 'pants-party'
    }
    expected_event = json.dumps({
        "type": "metrics",
        "contentType": "article",
        "id": "01234",
        "metric": "citations"
    })
    mock = Mock()
    with patch('article_metrics.events.event_bus_conn', return_value=mock):
        logic.insert_citation(citation_data)
        logic.recently_updated_article_notifications()
        mock.publish.assert_called_once_with(Message=expected_event)
