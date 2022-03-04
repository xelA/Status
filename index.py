import json
import asyncio
import time

from datetime import datetime
from quart import Quart, render_template
from utils import default, sqlite

with open("./config.json", "r") as f:
    config = json.load(f)

app = Quart(__name__)
xelA = default.xelA()
db = sqlite.Database()
db.create_tables()

global database_xela_cache
database_xela_cache = []


async def background_task():
    """ Delete old ticket entries for privacy reasons """
    while True:
        data, updated = xelA._fetch()
        if updated:
            db.execute(
                "INSERT INTO ping (users, servers, avg_us, ping_ws, ping_rest) VALUES (?, ?, ?, ?, ?)",
                (
                    xelA.users, xelA.servers, xelA.avg_users_server,
                    xelA.ping.get("ws", 0), xelA.ping.get("rest", 0)
                )
            )
            global database_xela_cache
            database_xela_cache = db.fetch("SELECT * FROM ping ORDER BY created_at DESC LIMIT 10")
        await asyncio.sleep(5)


@app.before_serving
async def startup():
    app.background_task = asyncio.ensure_future(background_task())


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
        "index.html", bot=xelA,
        domain=config.get("domain", f"http://localhost:{config['port']}"),
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


@app.route("/json")
async def index_json():
    json_output = {}
    json_output["history"] = []

    for k, v in xelA.__dict__.items():
        json_output[k] = v

    for g in database_xela_cache:
        try:
            del g["id"]
        except (ValueError, KeyError):
            pass  # idk how this fails, I fixed this from work with nano
        json_output["history"].append(g)

    return json_output


app.run(port=config["port"], debug=config["debug"])
