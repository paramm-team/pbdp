import logging
from pathlib import Path

# This is the default logger
# A custom logger or any other logging logger can be used
# and pbdp will use that logger instead.


def create_logger(logger_name="pbdp_logger", logger_level=logging.INFO, log_file=None):
    """
    Configure a named logger with one PBDP-owned output handler.

    By default messages go to stderr without creating files or directories.
    Set log_file to a writable file path to append UTF-8 logs instead; its
    parent directory must already exist. File-opening errors are propagated.

    Repeated calls reuse the handler for the same destination and update the
    logger level. Changing destinations closes and replaces only the handler
    created here, leaving caller-added handlers intact. Propagation to ancestor
    loggers is disabled to avoid duplicate output through the root logger.
    """
    logger = logging.getLogger(logger_name)
    destination = (None if log_file is None
                   else str(Path(log_file).expanduser().resolve()))
    owned_handlers = [handler for handler in logger.handlers
                      if getattr(handler, "_pbdp_owned", False)]
    handler = next((handler for handler in owned_handlers
                    if handler._pbdp_destination == destination), None)
    if handler is None:
        if destination is None:
            handler = logging.StreamHandler()
        else:
            handler = logging.FileHandler(destination, encoding="utf-8")
        handler._pbdp_owned = True
        handler._pbdp_destination = destination

    for old_handler in owned_handlers:
        if old_handler is not handler:
            logger.removeHandler(old_handler)
            old_handler.close()

    formatter = logging.Formatter("%(asctime)s : %(levelname)s : %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logger_level)
    logger.propagate = False
    return logger
