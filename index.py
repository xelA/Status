import json
import asyncio
import subprocess
import time

from typing import Union
from datetime import datetime
from postgreslite import PostgresLite
from quart import Quart, render_template

from utils import default

with open("./config.json", "r") as f:
    config = json.load(f)

app = Quart(__name__)
xelA = default.xelA()
discordstatus = default.DiscordStatus()

db = PostgresLite("./storage.db").connect()

git_log = subprocess.getoutput('git log -1 --pretty=format:"%h %s" --abbrev-commit').split(" ")
git_rev = git_log[0]
git_commit = " ".join(git_log[1:])

database_xela_cache: list[dict] = []


async def _task_refresh_db_cache():
    while True:
        _, updated = xelA._fetch()
        if updated:
            db.execute(
                "INSERT INTO ping (users, servers, user_installs, avg_us, ping_ws, ping_rest) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                xelA.users, xelA.servers, xelA.user_installs,
                xelA.avg_users_server, xelA.ping_ws, xelA.ping_rest
            )
            global database_xela_cache
            database_xela_cache = db.fetch("SELECT * FROM ping ORDER BY created_at DESC LIMIT 25")
        await asyncio.sleep(5)


@app.before_serving
async def startup():
    app.add_background_task(_task_refresh_db_cache)


def str_datetime(timestamp: str) -> datetime:
    return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")


def unix_timestamp(timestamp: Union[str, datetime]) -> int:
    if isinstance(timestamp, str):
        return time.mktime(str_datetime(timestamp).timetuple())
    elif isinstance(timestamp, datetime):
        return time.mktime(timestamp.timetuple())
    else:
        return timestamp


@app.route("/")
async def index():
    reverse_database_xela_cache = database_xela_cache[::-1]
    return await render_template(
        "index.html",
        bot=xelA,
        discordstatus=discordstatus.fetch(),
        domain=config.get("domain", f"http://localhost:{config['port']}"),
        git_rev=git_rev,
        git_commit=git_commit,
        top_stats={
            "WS / REST": f"{xelA.ping_ws:,} ms / {xelA.ping_rest:,} ms",
            "RAM": xelA.ram,
            "DB entries": f"{xelA.database:,}",
            "Server Installs": f"{xelA.servers:,}",
            "User Installs": f"{xelA.user_installs:,}",
            "Viewable users": f"{xelA.users:,}",
        },
        data=database_xela_cache,
        data_count=len(database_xela_cache),
        lists={
            "ws": [g["ping_ws"] for g in reverse_database_xela_cache],
            "rest": [g["ping_rest"] for g in reverse_database_xela_cache],
            "servers": [g["servers"] for g in reverse_database_xela_cache],
            "avg_us": [g["avg_us"] for g in reverse_database_xela_cache],
            "users": [g["users"] for g in reverse_database_xela_cache],
            "timestamps": [
                unix_timestamp(g["created_at"])
                for g in reverse_database_xela_cache
            ],
        }
    )


@app.route("/data.json")
async def index_json():
    json_output = {}

    for k, v in xelA.__dict__.items():
        json_output[k] = v

    json_output["history"] = []
    for g in database_xela_cache:
        try:
            del g["id"]
        except (ValueError, KeyError):
            pass  # idk how this fails, I fixed this from work with nano
        json_output["history"].append(g)

    return json_output


app.config["JSON_SORT_KEYS"] = False
app.run(port=config["port"], debug=config["debug"])
