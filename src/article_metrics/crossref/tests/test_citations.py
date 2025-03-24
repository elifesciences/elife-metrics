
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest

from article_metrics.crossref import citations
from article_metrics import utils
from article_metrics.crossref.citations import citations_for_all_articles


@pytest.fixture(name='models_mock', autouse=True)
def _models_mock() -> Iterator[MagicMock]:
    with patch.object(citations, 'models') as mock:
        yield mock


@pytest.fixture(name='count_for_qs_mock')
def _count_for_qs_mock() -> Iterator[MagicMock]:
    with patch.object(citations, 'count_for_qs') as mock:
        yield mock


class TestCitationsForAllArticles:
    def test_should_pass_all_articles_to_count_for_qs(
        self,
        models_mock: MagicMock,
        count_for_qs_mock: MagicMock
    ):
        citations_for_all_articles()
        count_for_qs_mock.assert_called_with(
            models_mock.Article.objects.all.return_value
        )

    def test_should_pass_a_requested_article_to_count_for_qs(
        self,
        models_mock: MagicMock,
        count_for_qs_mock: MagicMock
    ):
        citations_for_all_articles('12345')
        count_for_qs_mock.assert_called_with(
            models_mock.Article.objects.filter(doi=utils.msid2doi('12345'))
        )
