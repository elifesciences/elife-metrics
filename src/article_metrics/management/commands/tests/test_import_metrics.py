import argparse
import pytest

# from article_metrics import models
from article_metrics.management.commands.import_metrics import GA_DAILY, Command
from article_metrics.management.commands.import_metrics import get_sources
from article_metrics.management.commands.import_metrics import ALL_SOURCES_KEYS


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
        args = parser.parse_args(['--source', GA_DAILY])
        assert args.source == GA_DAILY

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
        args = parser.parse_args(['--source', GA_DAILY])

        assert set(get_sources(vars(args)).keys()) == {GA_DAILY}

    # def test_should_only_return_selected_article(self, command: Command):
    #     parser = argparse.ArgumentParser()
    #     command.add_arguments(parser=parser)
    #     args = parser.parse_args(['--source', models.CROSSREF, '--article-id', '12345'])

    #     sources = get_sources(vars(args))
    #     assert set(sources.keys()) == {models.CROSSREF}
    #     assert sources[models.CROSSREF][1] == '12345'

    def test_should_reject_article_id_without_source_being_selected(self, command: Command):
        parser = argparse.ArgumentParser()
        command.add_arguments(parser=parser)
        args = parser.parse_args(['--article-id', '12345'])

        with pytest.raises(AssertionError):
            get_sources(vars(args))

    def test_should_reject_article_id_with_source_other_than_crossref(self, command: Command):
        parser = argparse.ArgumentParser()
        command.add_arguments(parser=parser)
        args = parser.parse_args(['--source', GA_DAILY, '--article-id', '12345'])

        with pytest.raises(AssertionError):
            get_sources(vars(args))
