from __future__ import annotations

import logging
from collections.abc import Generator
from datetime import datetime, timezone

from gql import Client as GQLClient
from gql import gql
from gql.transport.requests import RequestsHTTPTransport

import krawl.config as config
from krawl.exceptions import FetcherException
from krawl.fetcher import Fetcher
from krawl.normalizer.wikifactory import WikifactoryNormalizer
from krawl.project import Project
from krawl.storage import FetcherStateStorage

log = logging.getLogger("wikifactory-fetcher")

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

    PLATFORM = "wikifactory.com"

    def __init__(self, state_storage: FetcherStateStorage, batch_size=None, retries=3, timeout=None) -> None:
        self._state_storage = state_storage
        self._batch_size = batch_size or 50
        self._transport = RequestsHTTPTransport(
            url="https://wikifactory.com/api/graphql",
            headers={"User-Agent": config.USER_AGENT},
            verify=True,
            retries=retries,
            timeout=timeout or 10,
        )
        self._client = GQLClient(
            transport=self._transport,
            fetch_schema_from_transport=False,
        )
        self._normalizer = WikifactoryNormalizer()

    def fetch(self, id: str) -> Project:
        log.debug("fetching project %s", id)
        owner, name = self._parse_id(id)
        params = {"space": owner, "slug": name}
        try:
            result = self._client.execute(QUERY_PROJECT_BY_SLUG, variable_values=params)
        except Exception as e:
            raise FetcherException(f"failed to fetch project '{id}'") from e
        if not result:
            raise FetcherException(f"project '{id}' not found")
        # enrich result
        result = result["project"]["result"]
        result["fetcher"] = self.PLATFORM
        result["lastVisited"] = datetime.now(timezone.utc)
        return self._normalizer.normalize(result)

    def fetch_all(self, start_over=True) -> Generator[Project, None, None]:
        has_next_page = True
        cursor = ""
        num_fetched_projects = 0
        if start_over:
            self._state_storage.delete(self.PLATFORM)
        else:
            state = self._state_storage.load(self.PLATFORM)
            if state:
                cursor = state.get("cursor", "")
                num_fetched_projects = state.get("num_fetched_projects", 0)

        while has_next_page:
            log.debug("WikiFactory: fetching projects %d to %d", num_fetched_projects,
                      num_fetched_projects + self._batch_size)

            params = {"cursor": cursor, "batchSize": self._batch_size}
            try:
                result = self._client.execute(QUERY_PROJECTS, variable_values=params)
            except Exception as e:
                raise FetcherException(f"failed to fetch projects from WikiFactory: {e}") from e

            raw = result["projects"]["result"]
            pageinfo = raw["pageInfo"]
            cursor = pageinfo["endCursor"]
            has_next_page = pageinfo["hasNextPage"]
            num_fetched_projects = num_fetched_projects + len(raw["edges"])
            last_visited = datetime.now(timezone.utc)
            for edge in raw["edges"]:
                raw_project = edge["node"]
                raw_project["fetcher"] = self.PLATFORM
                raw_project["lastVisited"] = last_visited
                project = self._normalizer.normalize(raw_project)
                log.debug("yield project %s", project.id)
                yield project

            # save current progress
            self._state_storage.store(self.PLATFORM, {
                "cursor": cursor,
                "num_fetched_projects": num_fetched_projects,
            })

        log.debug("Successfully fetched %d projects from Wikifactory", num_fetched_projects)
