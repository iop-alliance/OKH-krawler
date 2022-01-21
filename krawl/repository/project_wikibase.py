from __future__ import annotations

import logging
from collections.abc import Generator

from rdflib.graph import Graph

import krawl.wikibase.core
from krawl.config import Config
from krawl.project import Project
from krawl.repository import ProjectRepository
from krawl.serializer.rdf_serializer import RDFProjectSerializer
from krawl.wikibase.api import API

log = logging.getLogger("project-repository-wikibase")


class ProjectRepositoryWikibase(ProjectRepository):

    NAME = "wikibase"
    CONFIG_SCHEMA = {
        "type": "dict",
        "default": {},
        "meta": {
            "long_name": "wikibase",
        },
        "schema": {
            "url": {
                "type": "string",
                "required": True,
                "nullable": False,
                "meta": {
                    "long_name": "url",
                    "description": "Base URL of the Mediawiki"
                }
            },
            "token_url": {
                "type": "string",
                "required": True,
                "nullable": False,
                "meta": {
                    "long_name": "token-url",
                    "description": "URL to receive OAuth v2 tokens from"
                }
            },
            "client_id": {
                "type": "string",
                "required": True,
                "nullable": False,
                "meta": {
                    "long_name": "client-id",
                    "description": "The ID of the OAuth v2 client"
                }
            },
            "client_secret": {
                "type": "string",
                "required": True,
                "nullable": False,
                "meta": {
                    "long_name": "client-secret",
                    "description": "The secret of the OAuth v2 client"
                }
            },
            "reconcile_property": {
                "type": "string",
                "required": True,
                "nullable": False,
                "meta": {
                    "long_name": "reconcile-property",
                    "description": "Idk, figure it out yourself"
                }
            },
        },
    }

    def __init__(self, wikibase_config: Config):
        self._config = wikibase_config
        self._rdf_serializer = RDFProjectSerializer()

    def load(self, id) -> Project:
        raise NotImplementedError()

    def load_all(self, id) -> Generator[Project, None, None]:
        raise NotImplementedError()

    def store(self, project: Project) -> None:
        log.debug("uploading '%s' to Wikibase", project.id)
        serialized = self._rdf_serializer.serialize((project))

        # TODO: the whole Wikibase part must be rewritten too
        api = API(
            url=self._config.url,
            reconcilepropid=self._config.reconcile_property,
            client_id=self._config.client_id,
            client_secret=self._config.client_secret,
            token_url=self._config.token_url,
        )
        graph = Graph()
        graph.parse(data=serialized, format="ttl")
        items, modules = krawl.wikibase.core.makeentitylists(graph)
        items = [krawl.wikibase.core.makeentity(self._config.reconcile_property, i, graph) for i in items]
        itemids = api.push_many(items)
        module = krawl.wikibase.core.makeentity(self._config.reconcile_property, modules[0], graph, itemids)
        return api.push(module)

    def contains(self, id: str) -> bool:
        raise NotImplementedError()

    def search(self,
               platform: str | None = None,
               owner: str | None = None,
               name: str | None = None) -> Generator[Project, None, None]:
        raise NotImplementedError()

    def delete(self, id: str) -> None:
        raise NotImplementedError()
