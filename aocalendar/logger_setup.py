import logging


CONSOLE_HANDLER_NAME = 'Console'
FILE_HANDLER_NAME = 'File'
LOG_FILENAME = 'aoclog'

def setup(logger, output='INFO', file_logging=False, log_filename=LOG_FILENAME, path=None):
    handler_names = [x.get_name() for x in logger.handlers]
    if CONSOLE_HANDLER_NAME not in handler_names:
        from sys import stdout
        console_handler = logging.StreamHandler(stdout)
        console_handler.setLevel(output.upper())
        console_handler.setFormatter(logging.Formatter("{levelname} - {message}", style='{'))
        console_handler.set_name(CONSOLE_HANDLER_NAME)
        logger.addHandler(console_handler)
    if file_logging and FILE_HANDLER_NAME not in handler_names:
        import os.path as op
        if path is None: path = ''
        file_handler = logging.FileHandler(op.join(path, log_filename), mode='a')
        file_handler.setLevel(file_logging.upper())
        file_handler.setFormatter(logging.Formatter("{asctime} - {levelname} - {message}", style='{'))
        file_handler.set_name(FILE_HANDLER_NAME)
        logger.addHandler(file_handler)
