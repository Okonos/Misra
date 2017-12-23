import logging


BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[0;%dm"
BOLD_SEQ = "\033[1m"

COLORS = {
    'WARNING': YELLOW,
    'INFO': BLUE,
    'DEBUG': MAGENTA,
    'CRITICAL': RED,
    'ERROR': RED
}


class ColorFormatter(logging.Formatter):
    def __init__(self, *args, use_color=True, **kwargs):
        logging.Formatter.__init__(self, *args, **kwargs)
        self.use_color = use_color

    def format(self, record):
        levelname = record.levelname
        if self.use_color and levelname in COLORS:
            levelname_color = COLOR_SEQ % (30 + COLORS[levelname]) + \
                levelname + RESET_SEQ
            record.levelname = levelname_color
        return logging.Formatter.format(self, record)


if __name__ == '__main__':
    logger = logging.getLogger(__file__)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = ColorFormatter(
        '%(asctime)s:%(msecs)d - %(levelname)s - %(message)s',
        datefmt='%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info("info test")
    logger.warning("warning")
    logger.critical("CRIT")
