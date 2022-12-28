import json
import asyncio
import subprocess
import time
import aiohttp

from datetime import datetime
from quart import Quart, render_template, send_file
from utils import default, sqlite

with open("./config.json", "r") as f:
    config = json.load(f)

app = Quart(__name__)
xelA = default.xelA()
discordstatus = default.DiscordStatus()
db = sqlite.Database()
db.create_tables()

git_log = subprocess.getoutput('git log -1 --pretty=format:"%h %s" --abbrev-commit').split(" ")
git_rev = git_log[0]
git_commit = " ".join(git_log[1:])

database_xela_cache = []
commands_cache = []


async def _task_refresh_db_cache():
    while True:
        data, updated = xelA._fetch()
        if updated:
            db.execute(
                "INSERT INTO ping (users, servers, avg_us, ping_ws, ping_rest) VALUES (?, ?, ?, ?, ?)",
                (
                    xelA.users, xelA.servers, xelA.avg_users_server,
                    xelA.ping_ws, xelA.ping_rest
                )
            )
            global database_xela_cache
            database_xela_cache = db.fetch("SELECT * FROM ping ORDER BY created_at DESC LIMIT 10")
        await asyncio.sleep(5)


async def _task_refresh_cmd_cache():
    while True:
        global commands_cache

        async with aiohttp.ClientSession() as session:
            async with session.get("http://127.0.0.1:13377/commands/stats") as r:
                commands_cache = await r.json()

        await asyncio.sleep(30)


@app.before_serving
async def startup():
    app.add_background_task(_task_refresh_db_cache)
    app.add_background_task(_task_refresh_cmd_cache)


def str_datetime(timestamp: str):
    return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")


def unix_timestamp(timestamp):
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
        "index.html", bot=xelA, discordstatus=discordstatus.fetch(),
        domain=config.get("domain", f"http://localhost:{config['port']}"),
        git_rev=git_rev, git_commit=git_commit,
        commands=[
            {"name": g["name"], "count": g["count"], "used": g["last_used_at"]}
            for g in commands_cache[:15]
        ],
        top_stats={
            "WebSocket": f"{xelA.ping_ws:,} ms",
            "REST": f"{xelA.ping_rest:,} ms",
            "Users": f"{xelA.users:,}",
            "Servers": f"{xelA.servers:,}",
            "RAM": xelA.ram,
            "DB entries": f"{xelA.database:,}"
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


@app.route("/stats.png")
async def index_png():
    return await send_file(
        default.stats_image(xelA),
        mimetype="image/png"
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

    json_output["commands"] = commands_cache

    return json_output


app.config["JSON_SORT_KEYS"] = False
app.run(port=config["port"], debug=config["debug"])
