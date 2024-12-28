# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from ..model.hosting_id import HostingId, HostingType
from . import Normalizer, github, manifest, oshwa, thingiverse


class NormalizerFactory:

    def create(self, hosting_id: HostingId) -> Normalizer:
        match hosting_id.type():
            case HostingType.APPROPEDIA:
                return manifest.ManifestNormalizer()
            case HostingType.GIT_HUB:
                return manifest.ManifestNormalizer(github.GitHubFileHandler())
            case HostingType.OSHWA:
                return oshwa.OshwaNormalizer()
            case HostingType.THINGIVERSE:
                return thingiverse.ThingiverseNormalizer()
            case _:
                raise NotImplementedError(f"Missing `create()` impl for enum variant {hosting_id.type()}")
