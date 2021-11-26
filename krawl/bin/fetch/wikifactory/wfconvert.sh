#!/bin/bash
# coding: utf-8
find $KRAWLER_WORKDIR -name record.json -exec python -m krawl.wfconvert {} +