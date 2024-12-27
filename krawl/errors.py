# SPDX-FileCopyrightText: 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2023 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations


class KrawlerError(Exception):
    pass


class ConfigError(KrawlerError):

    def __init__(self, msg: str, reasons: list[str]) -> None:
        super().__init__(msg)
        self.reasons = reasons


class NormalizerError(KrawlerError):
    pass


class FetcherError(KrawlerError):
    pass


class DeserializerError(KrawlerError):
    pass


class NotOverriddenError(KrawlerError, NotImplementedError):
    pass


class ParserError(KrawlerError):
    pass


class SerializerError(KrawlerError):
    pass


class NotFound(FetcherError):
    pass


class RepositoryError(KrawlerError):
    pass


class ConversionError(KrawlerError):
    pass
