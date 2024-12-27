# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from enum import StrEnum


class SourcingProcedure(StrEnum):
    """See `okh:SourcingProcedure` individuals
    in file 'src/ont/okh-krawler.ttl' (in the Krawler repo),
    or respectively <http://w3id.org/oseg/ont/okh-krawler#>."""
    API = "Api"
    """The API of the platform hosting the project
    is crawled to create a manifest,
    which is then converted to (OKH) RDF triples"""
    MANIFEST = "Manifest"
    """The project supplies a manifest,
    which is then crawled and converted to (OKH) RDF triples"""
    GENERATED_MANIFEST = "GeneratedManifest"
    """The platform hosting the project generates a manifest,
    which is then crawled and converted to (OKH) RDF triples"""
    DIRECT = "Direct"
    """The project directly supplies (OKH) RDF triples,
    which are then crawled"""
