"""
Opencensun monitor for JupyterHub as a JupyterHub service. 
"""
import asyncio
import datetime
import logging
import os
from collections import defaultdict

import httpx
from opencensus.ext.azure import metrics_exporter
from opencensus.stats import aggregation as aggregation_module
from opencensus.stats import measure as measure_module
from opencensus.stats import stats as stats_module
from opencensus.stats import view as view_module
from opencensus.tags import tag_map as tag_map_module


logger = logging.getLogger(__name__)


__version__ = "0.1.0"
INTERVAL = 15
APPLICATIONINSIGHTS_CONNECTION_STRING = ""

# ---- Metrics configuration ----
tmaps = defaultdict(tag_map_module.TagMap)

server_count_measure = measure_module.MeasureInt(
    "Active servers", "Number of currently active servers", unit="servers"
)
mmap = stats_module.stats.stats_recorder.new_measurement_map()



def count_notebook_servers(data: list):
    server_count = defaultdict(lambda: 0)
    for user in data:
        for _, server in user["servers"].items():
            profile = server["user_options"]["profile"]
            tag_map = tmaps[profile]
            tag_map.insert("profile", profile)
            server_count += 1


async def main():

    JUPYTERHUB_API_TOKEN = os.environ["JUPYTERHUB_API_TOKEN"]
    JUPYTERHUB_API_URL = os.environ["JUPYTERHUB_API_URL"]

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"token {JUPYTERHUB_API_TOKEN}"}

        logger.debug("checking hub API")
        response = await client.get(f"{JUPYTERHUB_API_URL}/")
        logger.info(
            "Monitoring url: %s, version: %s",
            JUPYTERHUB_API_URL,
            response.json()["version"],
        )

        while True:
            response = await client.get(
                f"{JUPYTERHUB_API_URL}/users?state=active", headers=headers
            )
            data = response.json()
            print(data)
            await asyncio.sleep(INTERVAL)


if __name__ == "__main__":
    import coloredlogs

    coloredlogs.install()
    asyncio.run(main())
