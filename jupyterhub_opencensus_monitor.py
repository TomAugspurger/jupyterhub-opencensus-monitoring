"""
Opencensus monitor for JupyterHub as a JupyterHub service.
"""
import asyncio
import logging
import os
from collections import Counter, defaultdict

import httpx
from opencensus.ext.azure import metrics_exporter
import opencensus.stats.aggregation
import opencensus.stats.view
import opencensus.stats.stats
import opencensus.stats.measure
import opencensus.tags.tag_map


logger = logging.getLogger(__name__)


__version__ = "0.1.0"
INTERVAL = 60  # seconds

# ---- Metrics configuration ----
# We collect / record by counts by profile, so create one TagMap per profile.
server_tag_maps = defaultdict(opencensus.tags.tag_map.TagMap)

server_count_measure = opencensus.stats.measure.MeasureInt(
    "Active servers", "Number of currently active servers", unit="servers"
)
server_count_view = opencensus.stats.view.View(
    "Active servers",
    "Number of currently active servers",
    ["profile"],
    server_count_measure,
    opencensus.stats.aggregation.LastValueAggregation(),
)

measurement_maps = defaultdict(
    opencensus.stats.stats.stats.stats_recorder.new_measurement_map
)
opencensus.stats.stats.stats.view_manager.register_view(server_count_view)
exporter = metrics_exporter.new_metrics_exporter()

# ---- Metric helpers ----


def count_notebook_servers(data: list):
    """
    Count the number of notebook servers by profile.
    """
    server_count = Counter()

    for user in data:
        for _, server in user["servers"].items():
            profile = server["user_options"]["profile"]
            tag_map = server_tag_maps[profile]
            tag_map.insert("profile", profile)
            server_count[profile] += 1

    return server_count


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
            server_count = count_notebook_servers(data)
            for profile, count in server_count.items():
                measurement_map = measurement_maps[profile]
                tag_map = server_tag_maps[profile]
                measurement_map.measure_int_put(server_count_measure, count)
                measurement_map.record(tag_map)

            logger.debug("Sleeping for %d", INTERVAL)
            await asyncio.sleep(INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
