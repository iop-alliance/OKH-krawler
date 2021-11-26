#!/bin/bash
# coding: utf-8
find $KRAWLER_WORKDIR -name normalized.toml -exec python  -m krawl.rdf {} +