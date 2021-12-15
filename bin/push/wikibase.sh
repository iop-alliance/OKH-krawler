#!/bin/bash
set -e

find $KRAWLER_WORKDIR -name rdf.ttl -exec python -m krawl.wikibase.core {} +
