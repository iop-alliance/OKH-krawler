from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

from gql import Client as GQLClient
from gql import gql
from gql.transport.requests import RequestsHTTPTransport

from krawl.config import Config
from krawl.errors import FetcherError, NormalizerError
from krawl.fetcher import Fetcher
from krawl.log import get_child_logger
from krawl.normalizer.wikifactory import WikifactoryNormalizer
from krawl.project import Project, ProjectID
from krawl.repository import FetcherStateRepository

log = get_child_logger("wikifactory")

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
    projects and their metadata. For developing the query, one can use the
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
    CONFIG_SCHEMA = Fetcher._generate_config_schema(long_name="wikifactory", default_timeout=15, access_token=False)

    def __init__(self, state_repository: FetcherStateRepository, config: Config) -> None:
        self._state_repository = state_repository
        self._normalizer = WikifactoryNormalizer()

        # client for GraphQL requests
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

    def __fetch_one(self, raw_project: dict, last_visited: datetime) -> Project:
        id = ProjectID(self.NAME, raw_project["parentSlug"], raw_project["slug"])
        meta = {
            "meta": {
                "owner": id.owner,
                "repo": id.repo,
                "path": id.path,
                "fetcher": self.NAME,
                "last_visited": last_visited,
            }
        }

        # try normalizing it
        try:
            raw_project.update(meta)
            project = self._normalizer.normalize(raw_project)
        except NormalizerError as err:
            raise FetcherError(f"normalization failed, that should not happen: {err}") from err

        return project

    def fetch(self, id: ProjectID) -> Project:
        log.debug("fetching project %s", id)

        # download metadata
        params = {"space": id.owner, "slug": id.repo}
        try:
            result = self._client.execute(QUERY_PROJECT_BY_SLUG, variable_values=params)
        except Exception as e:
            raise FetcherError(f"failed to fetch project '{id}'") from e
        if not result:
            raise FetcherError(f"project '{id}' not found")

        last_visited = datetime.now(timezone.utc)

        raw_project = result["project"]["result"]
        project = self.__fetch_one(raw_project, last_visited)

        return project

    def fetch_all(self, start_over=True) -> Generator[Project]:
        has_next_page = True
        cursor = ""
        num_fetched = 0
        if start_over:
            self._state_repository.delete(self.NAME)
        else:
            state = self._state_repository.load(self.NAME)
            if state:
                cursor = state.get("cursor", "")
                num_fetched = state.get("num_fetched", 0)

        while has_next_page:
            log.debug("fetching projects %d to %d", num_fetched, num_fetched + self.BATCH_SIZE)

            # download metadata
            params = {"cursor": cursor, "batchSize": self.BATCH_SIZE}
            try:
                result = self._client.execute(QUERY_PROJECTS, variable_values=params)
            except Exception as e:
                raise FetcherError(f"failed to fetch projects from WikiFactory: {e}") from e

            # process results
            raw = result["projects"]["result"]
            page_info = raw["pageInfo"]
            cursor = page_info["endCursor"]
            has_next_page = page_info["hasNextPage"]
            num_fetched = num_fetched + len(raw["edges"])
            last_visited = datetime.now(timezone.utc)
            for edge in raw["edges"]:
                raw_project = edge["node"]
                project = self.__fetch_one(raw_project, last_visited)
                log.debug("yield project %s", project.id)
                yield project

            # save current progress
            self._state_repository.store(self.NAME, {
                "cursor": cursor,
                "num_fetched": num_fetched,
            })

        self._state_repository.delete(self.NAME)
        log.debug("fetched %d projects from Wikifactory", num_fetched)
