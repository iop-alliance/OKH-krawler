#!/bin/bash
set -e

python -m krawl.wf
# find $KRAWLER_WORKDIR -name record.json -exec python -m krawl.wfconvert {} +
