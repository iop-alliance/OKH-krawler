class KrawlerException(Exception):
    pass


class NormalizationException(KrawlerException):
    pass


class FetcherException(KrawlerException):
    pass


class StorageException(KrawlerException):
    pass
