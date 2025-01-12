# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from ..model.hosting_id import HostingId, HostingType
from . import Normalizer, github, manifest, oshwa, thingiverse

_normalizers = {
    HostingType.APPROPEDIA: manifest.ManifestNormalizer(),
    HostingType.GIT_HUB: manifest.ManifestNormalizer(github.GitHubFileHandler()),
    HostingType.OSHWA: oshwa.OshwaNormalizer(),
    HostingType.THINGIVERSE: thingiverse.ThingiverseNormalizer(),
}


class NormalizerFactory:

    def get(self, hosting_id: HostingId) -> Normalizer:
        normalizer = _normalizers.get(hosting_id.type())
        if normalizer:
            return normalizer
        raise NotImplementedError(f"Missing `get()` impl for enum variant {hosting_id.type()}")
