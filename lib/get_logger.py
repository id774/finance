from logging import getLogger, Formatter, StreamHandler, INFO

def get_logger(modname):
    logger = getLogger(modname)
    handler = StreamHandler()
    handler.setLevel(INFO)
    handler.setFormatter(Formatter(fmt='%(asctime)s %(levelname)s -- %(message)s'))
    logger.setLevel(INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return logger
