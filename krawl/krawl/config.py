from pathlib import Path
import os

N_THREADS = 4
WORKDIR = Path(os.environ.get("KRAWLER_WORKDIR"))
URL = os.environ.get("KRAWLER_WB_HOST", "https://losh.ose-germany.de")
USER = os.environ.get("KRAWLER_WB_USER")
PASSWORD = os.environ.get("KRAWLER_WB_PASSWORD")
CONSUMER_KEY = os.environ.get("KRAWLER_WB_CONSUMER_KEY")
CONSUMER_SECRET = os.environ.get("KRAWLER_WB_CONSUMER_SECRET")
ACCESS_TOKEN = os.environ.get("KRAWLER_WB_ACCESS_TOKEN")
ACCESS_SECRET = os.environ.get("KRAWLER_WB_ACCESS_SECRET")
RECONCILEPROPID = os.environ.get("KRAWLER_WB_RECONCILEPROPID")
GITHUB_KEY = os.environ.get("KRAWLER_GITHUB_KEY")