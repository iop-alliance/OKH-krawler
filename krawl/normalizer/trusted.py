from __future__ import annotations

import logging

from krawl.normalizer import Normalizer
from krawl.project import Project

log = logging.getLogger("trusted-normalizer")


class TrustedNormalizer(Normalizer):

    def normalize(self, raw: dict) -> Project:
        Project.from_dict(raw)
