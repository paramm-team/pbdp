import logging
from pathlib import Path

# This is the default logger
# A custom logger or any other logging logger can be used
# and pbdp will use that logger instead.


def create_logger(logger_name="pbdp_logger", logger_level=logging.INFO):
    """
    Create a logger to log the messages.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(logger_level)
    formatter = logging.Formatter("%(asctime)s : %(levelname)s : %(message)s")
    # resolve the path to the log file
    log_folder = Path(__file__).parent.absolute() / "../logs/"
    log_folder = log_folder.resolve()
    log_folder.mkdir(exist_ok=True)
    logpath = str(log_folder) + "/pbdp.log"
    file_handler = logging.FileHandler(logpath)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info("Logger created")
    return logger
