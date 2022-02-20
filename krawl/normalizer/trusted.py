from __future__ import annotations

from krawl.normalizer import Normalizer
from krawl.project import Project


class TrustedNormalizer(Normalizer):

    def normalize(self, raw: dict) -> Project:
        Project.from_dict(raw)
