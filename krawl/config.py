import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# General
N_THREADS = 4
WORKDIR = Path(os.environ.get("KRAWLER_WORKDIR"))

USER_AGENT = "OKH-LOSH-Crawler github.com/OPEN-NEXT/OKH-LOSH"

# Wikibase
URL = os.environ.get("KRAWLER_WB_HOST", "https://losh.ose-germany.de")
USER = os.environ.get("KRAWLER_WB_USER")
# in WB displayed as "Client application key"
WB_CLIENT_ID = os.environ.get("KRAWLER_WB_CLIENT_ID")
# in WB displayed as "Client application secret"
WB_CLIENT_SECRET = os.environ.get("KRAWLER_WB_CLIENT_SECRET")
WB_TOKEN_URL = os.environ.get("KRAWLER_WB_TOKEN_URL")

PASSWORD = os.environ.get("KRAWLER_WB_PASSWORD")
CONSUMER_KEY = os.environ.get("KRAWLER_WB_CONSUMER_KEY")
CONSUMER_SECRET = os.environ.get("KRAWLER_WB_CONSUMER_SECRET")
ACCESS_TOKEN = os.environ.get("KRAWLER_WB_ACCESS_TOKEN")
ACCESS_SECRET = os.environ.get("KRAWLER_WB_ACCESS_SECRET")

RECONCILEPROPID = os.environ.get("KRAWLER_WB_RECONCILEPROPID", "P1344")

# GitHub
GITHUB_KEY = os.environ.get("KRAWLER_GITHUB_KEY")

# WikiFactory
MAX_WF_PAGES = int(os.environ.get("KRAWLER_MAX_WF_PAGES", "999999"))
