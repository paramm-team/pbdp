"""Logger setup should be safe for installed packages and repeatable."""
from io import StringIO
import logging
from uuid import uuid4

import pytest

from pbdp import create_logger
import pbdp.pbdp_logger as logger_module


@pytest.fixture
def logger():
    instance = logging.getLogger('pbdp.test.' + uuid4().hex)
    yield instance
    for handler in instance.handlers[:]:
        instance.removeHandler(handler)
        handler.close()


def test_default_logger_does_not_write_to_installation(
    tmp_path, monkeypatch, capsys, logger
):
    package = tmp_path / 'site-packages' / 'pbdp'
    package.mkdir(parents=True)
    module_file = package / 'pbdp_logger.py'
    module_file.write_text('installed package marker', encoding='utf-8')
    monkeypatch.setattr(logger_module, '__file__', str(module_file))
    before = set(tmp_path.rglob('*'))

    configured = create_logger(logger.name)
    configured.info('measurement imported')

    assert configured is logger
    assert set(tmp_path.rglob('*')) == before
    assert module_file.read_text(encoding='utf-8') == 'installed package marker'
    assert capsys.readouterr().err.count('measurement imported') == 1
    assert not any(isinstance(handler, logging.FileHandler)
                   for handler in logger.handlers)


def test_repeated_calls_reuse_stream_handler_and_update_level(capsys, logger):
    create_logger(logger.name, logging.INFO)
    original_handler = logger.handlers[0]
    create_logger(logger.name, logging.INFO)
    assert create_logger(logger.name, logging.DEBUG) is logger
    logger.debug('one debug message')

    assert logger.handlers == [original_handler]
    assert logger.level == logging.DEBUG
    assert logger.propagate is False
    assert capsys.readouterr().err.count('one debug message') == 1


def test_explicit_file_is_appended_once_without_duplicate_handlers(tmp_path, logger):
    output = tmp_path / 'experiment.log'
    output.write_text('earlier entry\n', encoding='utf-8')
    create_logger(logger.name, logging.INFO, output)
    original_handler = logger.handlers[0]
    create_logger(logger.name, log_file=str(output))
    logger.info('temperature 23 °C')

    assert logger.handlers == [original_handler]
    saved = output.read_text(encoding='utf-8')
    assert saved.startswith('earlier entry\n')
    assert saved.count('temperature 23 °C') == 1


def test_destination_change_closes_owned_file_and_preserves_caller_handler(
    tmp_path, capsys, logger
):
    caller_stream = StringIO()
    caller_handler = logging.StreamHandler(caller_stream)
    logger.addHandler(caller_handler)
    output = tmp_path / 'experiment.log'
    create_logger(logger.name, log_file=output)
    file_handler = next(handler for handler in logger.handlers
                        if isinstance(handler, logging.FileHandler))
    logger.info('file message')

    create_logger(logger.name)
    create_logger(logger.name)
    logger.info('stream message')

    assert file_handler.stream is None
    assert file_handler not in logger.handlers
    assert caller_handler in logger.handlers
    assert len(logger.handlers) == 2
    assert output.read_text(encoding='utf-8').count('file message') == 1
    assert 'stream message' not in output.read_text(encoding='utf-8')
    assert caller_stream.getvalue().count('stream message') == 1
    assert capsys.readouterr().err.count('stream message') == 1


def test_invalid_explicit_path_does_not_create_directories_or_replace_handler(
    tmp_path, logger
):
    create_logger(logger.name)
    original_handler = logger.handlers[0]
    output = tmp_path / 'missing' / 'experiment.log'

    with pytest.raises(FileNotFoundError):
        create_logger(logger.name, log_file=output)

    assert not output.parent.exists()
    assert logger.handlers == [original_handler]
