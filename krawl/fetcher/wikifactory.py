from __future__ import annotations

import logging
from collections.abc import Generator
from datetime import datetime, timezone

from gql import Client as GQLClient
from gql import gql
from gql.transport.requests import RequestsHTTPTransport

from krawl.config import Config
from krawl.exceptions import FetchingException
from krawl.fetcher import Fetcher
from krawl.normalizer.wikifactory import WikifactoryNormalizer
from krawl.project import Project, ProjectID
from krawl.repository import FetcherStateRepository

log = logging.getLogger("wikifactory-fetcher")

#pylint: disable=consider-using-f-string
PROJECT_FIELDS = """
name
description
dateCreated
lastUpdated
followersCount
starCount
forkCount
creator {
    profile {
        fullName
        username
        email
        locale
    }
}
image {
    filename
    mimeType
    url
    permalink
    dateCreated
    lastUpdated
    license
    creator {
        profile {
            fullName
            username
            email
            locale
        }
    }
}
license {
    abreviation  # spelled wrong, but it is in the schema
}
contribution {
    version
    title
    lastUpdated
    files {
        dirname
        file {
            filename
            mimeType
            url
            permalink
            dateCreated
            lastUpdated
            license
            creator {
                profile {
                    fullName
                    username
                    email
                    locale
                }
            }
        }
    }
}
contributionCount
contributors {
    edges {
        node {
            fullName
            username
            email
        }
    }
}
forkedFrom {
    project {
        parentSlug
        slug
    }
}
slug
parentSlug
parentContent {
    type  # used to determine, if owner is an organization
    title # nice name of organization
}
"""
QUERY_PROJECTS = gql("""
query projects($batchSize: Int, $cursor: String) {
    projects(first: $batchSize, after: $cursor) {
        result {
            pageInfo {
                hasNextPage
                startCursor
                endCursor
            }
            edges {
                node {
                    %s
                }
            }
        }
    }
}
""" % PROJECT_FIELDS)
QUERY_PROJECT_BY_ID = gql("""
query project($id: String) {
    project(id: $id) {
        result {
            %s
        }
    }
}
""" % PROJECT_FIELDS)
QUERY_PROJECT_BY_SLUG = gql("""
query project($space: String, $slug: String) {
    project(space: $space, slug: $slug) {
        result {
            %s
        }
    }
}
""" % PROJECT_FIELDS)
#pylint: enable=consider-using-f-string


class WikifactoryFetcher(Fetcher):
    """Fetcher for projects on Wikifactory.com.

    Wikifactory offers a GraphQL API, that is used by the fetcher to get all
    projects and their metadata. For developing the query one can use the
    in-browser tool available at https://wikifactory.com/api/graphql. To debug
    the query, simply post it into the tool along with the following variables:

        {
            "batchSize": 2,
            "cursor": ""
        }

    To get all available fields the following query might be handy:

        {
            __schema {
                types {
                    name
                    fields {
                        name
                        isDeprecated
                        type {
                            name
                        }
                    }
                }
            }
        }

    """

    NAME = "wikifactory.com"
    BATCH_SIZE = 30
    CONFIG_SCHEMA = {
        "type": "dict",
        "default": {},
        "meta": {
            "long_name": "wikifactory",
        },
        "schema": {
            "timeout": {
                "type": "integer",
                "default": 15,
                "min": 1,
                "meta": {
                    "long_name": "timeout",
                    "description": "Max seconds to wait for a not responding service"
                }
            },
            "retries": {
                "type": "integer",
                "default": 3,
                "min": 0,
                "meta": {
                    "long_name": "retries",
                    "description": "Number of retries of requests in cases of network errors"
                }
            },
        },
    }

    def __init__(self, state_repository: FetcherStateRepository, config: Config) -> None:
        self._state_repository = state_repository
        self._normalizer = WikifactoryNormalizer()

        # client for GRAPHQL requests
        self._transport = RequestsHTTPTransport(
            url="https://wikifactory.com/api/graphql",
            headers={"User-Agent": config.user_agent},
            verify=True,
            retries=config.retries,
            timeout=config.timeout,
        )
        self._client = GQLClient(
            transport=self._transport,
            fetch_schema_from_transport=False,
        )

    def fetch(self, id: ProjectID) -> Project:
        log.debug("fetching project %s", id)
        params = {"space": id.owner, "slug": id.repo}
        try:
            result = self._client.execute(QUERY_PROJECT_BY_SLUG, variable_values=params)
        except Exception as e:
            raise FetchingException(f"failed to fetch project '{id}'") from e
        if not result:
            raise FetchingException(f"project '{id}' not found")
        # enrich result
        result = result["project"]["result"]
        result["fetcher"] = self.NAME
        result["lastVisited"] = datetime.now(timezone.utc)
        return self._normalizer.normalize(result)

    def fetch_all(self, start_over=True) -> Generator[Project, None, None]:
        has_next_page = True
        cursor = ""
        num_fetched_projects = 0
        if start_over:
            self._state_repository.delete(self.NAME)
        else:
            state = self._state_repository.load(self.NAME)
            if state:
                cursor = state.get("cursor", "")
                num_fetched_projects = state.get("num_fetched_projects", 0)

        while has_next_page:
            log.debug("fetching projects %d to %d", num_fetched_projects, num_fetched_projects + self.BATCH_SIZE)

            params = {"cursor": cursor, "batchSize": self.BATCH_SIZE}
            try:
                result = self._client.execute(QUERY_PROJECTS, variable_values=params)
            except Exception as e:
                raise FetchingException(f"failed to fetch projects from WikiFactory: {e}") from e

            raw = result["projects"]["result"]
            pageinfo = raw["pageInfo"]
            cursor = pageinfo["endCursor"]
            has_next_page = pageinfo["hasNextPage"]
            num_fetched_projects = num_fetched_projects + len(raw["edges"])
            last_visited = datetime.now(timezone.utc)
            for edge in raw["edges"]:
                raw_project = edge["node"]
                raw_project["fetcher"] = self.NAME
                raw_project["lastVisited"] = last_visited
                project = self._normalizer.normalize(raw_project)
                log.debug("yield project %s", project.id)
                yield project

            # save current progress
            self._state_repository.store(self.NAME, {
                "cursor": cursor,
                "num_fetched_projects": num_fetched_projects,
            })

        self._state_repository.delete(self.NAME)
        log.debug("fetched %d projects from Wikifactory", num_fetched_projects)
