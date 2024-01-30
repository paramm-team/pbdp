import logging
from pathlib import Path


def create_logger():
    """
    Create a logger to log the messages.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s : %(levelname)s : %(message)s")
    # resolve the path to the log file
    log_folder = Path(__file__).parent.absolute() / "../logs/"
    log_folder = log_folder.resolve()
    log_folder.mkdir(exist_ok=True)
    logpath = str(log_folder) + "/pbdp.log"
    file_handler = logging.FileHandler(logpath)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
