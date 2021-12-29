from __future__ import annotations

import logging
import logging.config


def configure_logger(level, format, output_stream, error_stream):

    class StdoutFilter:

        def filter(self, record) -> bool:
            return record.levelno < logging.WARNING

    class StderrFilter:

        def filter(self, record) -> bool:
            return record.levelno >= logging.WARNING

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
            "": {
                "handlers": ["stdout", "stderr"],
                "level": level.upper(),
                "propagate": False
            }
        }
    }
    logging.config.dictConfig(logging_config)
