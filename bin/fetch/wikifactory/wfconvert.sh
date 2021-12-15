#!/bin/bash
set -e

find $KRAWLER_WORKDIR -name record.json -exec python -m krawl.wfconvert {} +
