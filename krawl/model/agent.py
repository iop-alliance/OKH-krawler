# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AgentRef:
    """A Person or Organization as an RDF reference."""

    iri: str
    """RDF IRI to the agent individual, for example:

    - `myorg:janeDoe`
    - `myhouse:joeDoe`"""
    type: str
    """RDF/OWL IRI to the `rdf:type` of the agent, for example:

    - `dcterms:Agent`
    - `foaf:Person`
    - `schema:Organization`
    - `schema:Person`"""


@dataclass(slots=True)
class Agent:
    """A Person or Organization."""

    name: str
    email: str | None = None
    url: str | None = None

    def is_valid(self) -> bool:
        return bool(self.name)


@dataclass(slots=True)
class Person(Agent):
    pass


@dataclass(slots=True)
class Organization(Agent):
    pass
