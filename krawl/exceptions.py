from __future__ import annotations


class KrawlerException(Exception):
    pass


class ConfigException(KrawlerException):

    def __init__(self, msg: str, reasons: list[str]) -> None:
        super().__init__(msg)
        self.reasons = reasons


class NormalizationException(KrawlerException):
    pass


class FetchingException(KrawlerException):
    pass


class NotAManifest(FetchingException):
    pass


class NotFound(FetchingException):
    pass


class RepositoryException(KrawlerException):
    pass
