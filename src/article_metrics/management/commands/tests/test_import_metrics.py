import argparse
from unittest.mock import MagicMock, patch
from typing import Iterator

import pytest

from article_metrics import models
from article_metrics.management.commands import import_metrics
from article_metrics.management.commands.import_metrics import Command
from src.article_metrics.management.commands.import_metrics import get_sources
from src.article_metrics.management.commands.import_metrics import ALL_SOURCES_KEYS


@pytest.fixture(name='command')
def _command() -> Command:
    command = Command()
    return command

class TestCommand:
    def test_should_not_require_any_arguments(self, command: Command):
        parser = argparse.ArgumentParser()
        command.add_arguments(parser=parser)
        parser.parse_args([])

    def test_should_be_able_to_pass_in_a_source(self, command: Command):
        parser = argparse.ArgumentParser()
        command.add_arguments(parser=parser)
        args = parser.parse_args(['--source', models.CROSSREF])
        assert args.source == models.CROSSREF

    def test_should_reject_invalid_source(self, command: Command):
        parser = argparse.ArgumentParser()
        command.add_arguments(parser=parser)
        with pytest.raises(SystemExit):
            parser.parse_args(['--source', 'invalid'])

    def test_be_able_to_pass_in_an_article(self, command: Command):
        parser = argparse.ArgumentParser()
        command.add_arguments(parser=parser)
        args = parser.parse_args(['--article-id', '12345'])
        assert args.article_id == '12345'

class TestGetSources:
    def test_should_return_all_sources(self, command: Command):
        parser = argparse.ArgumentParser()
        command.add_arguments(parser=parser)
        args = parser.parse_args([])

        assert set(get_sources(vars(args)).keys()) == set(ALL_SOURCES_KEYS)

    def test_should_only_return_selected_source(self, command: Command):
        parser = argparse.ArgumentParser()
        command.add_arguments(parser=parser)
        args = parser.parse_args(['--source', models.CROSSREF])

        assert set(get_sources(vars(args)).keys()) == {models.CROSSREF}

    def test_should_only_return_selected_article(self, command: Command):
        parser = argparse.ArgumentParser()
        command.add_arguments(parser=parser)
        args = parser.parse_args(['--source', models.CROSSREF, '--article-id', '12345'])

        sources = get_sources(vars(args))
        assert set(sources.keys()) == {models.CROSSREF}
        assert sources[models.CROSSREF][1] == '12345'
