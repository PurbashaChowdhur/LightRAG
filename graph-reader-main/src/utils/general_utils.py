import logging

def setup_logger(log_file:str, logger_name:str) -> logging.Logger:
    """
    Setup and return a logger.
    """
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(logger_name)