from __future__ import annotations

import logging
import logging.config

app_logger = logging.getLogger("krawl")


def configure_logger(level, format, output_stream, error_stream):

    class StdoutFilter:

        def filter(self, record) -> bool:
            #return record.levelno < logging.WARNING
            # NOTE According to <https://clig.dev/#the-basics>,
            #      all logging should go to stderr.
            return False

    class StderrFilter:

        def filter(self, record) -> bool:
            #return record.levelno >= logging.WARNING
            # NOTE According to <https://clig.dev/#the-basics>,
            #      all logging should go to stderr.
            return True

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "message_only": {
                "format": format
            },
        },
        "filters": {
            "stdout_filter": {
                "()": StdoutFilter
            },
            "stderr_filter": {
                "()": StderrFilter
            }
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "formatter": "message_only",
                "filters": ["stdout_filter"],
                "stream": output_stream
            },
            "stderr": {
                "class": "logging.StreamHandler",
                "formatter": "message_only",
                "filters": ["stderr_filter"],
                "stream": error_stream
            },
        },
        "loggers": {
            "krawl": {
                "level": level.upper(),
                "propagate": True
            }
        },
        "root": {
            "handlers": ["stdout", "stderr"],
            "level": "ERROR",
        },
    }
    logging.config.dictConfig(logging_config)


def get_child_logger(suffix):
    return app_logger.getChild(suffix)
