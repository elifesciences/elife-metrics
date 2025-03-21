import argparse

import pytest

from article_metrics.management.commands.import_metrics import Command


@pytest.fixture(name='command')
def _command() -> Command:
    command = Command()
    return command


class TestCommand:
    def test_should_not_require_any_arguments(self, command: Command):
        parser = argparse.ArgumentParser()
        command.add_arguments(parser=parser)
        parser.parse_args([])
