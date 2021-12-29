class KrawlerException(Exception):
    pass


class ConfigException(KrawlerException):
    pass


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
