import requests

from datetime import datetime, timedelta


class DiscordStatus:
    def __init__(self, _cache_minutes: int = 2):
        self._data = {}
        self._last_fetch = None
        self._cache_minutes = _cache_minutes

    def fetch(self) -> dict:
        if (
            self._last_fetch and
            datetime.utcnow() - self._last_fetch < timedelta(minutes=self._cache_minutes)
        ):
            return self._data

        self._data = requests.get("https://discordstatus.com/api/v2/status.json").json()
        self._last_fetch = datetime.utcnow()
        return self._data


class xelA:
    def __init__(self, _cache_seconds: int = 60):
        self._data = {}
        self._last_fetch = None
        self._cache_seconds = _cache_seconds

    def __str__(self) -> str:
        return f"{self.username}#{self.discriminator}"

    def __int__(self) -> int:
        return int(self.id)

    @property
    def me(self) -> dict:
        return self._data.get("@me", {})

    @property
    def last_reboot(self) -> int:
        return self._data.get("last_reboot", 0)

    @property
    def ram(self) -> int:
        return self._data.get("ram", 0)

    @property
    def database(self) -> int:
        return self._data.get("database", 0)

    @property
    def servers(self) -> int:
        return self._data.get("servers", 0)

    @property
    def user_installs(self) -> int:
        return self._data.get("user_installs", 0)

    @property
    def users(self) -> int:
        return self._data.get("users", 0)

    @property
    def avg_users_server(self) -> int:
        return self._data.get("avg_users_server", 0)

    @property
    def ping(self) -> dict:
        return self._data.get("ping", {})

    @property
    def ping_ws(self) -> int:
        return self.ping.get("ws", 0)

    @property
    def ping_rest(self) -> int:
        return self.ping.get("rest", 0)

    @property
    def id(self) -> int:
        return self.me.get("id", 1337)

    @property
    def avatar(self) -> str:
        return self.me.get("avatar", "")

    @property
    def discriminator(self) -> str:
        return self.me.get("discriminator", "0000")

    @property
    def username(self) -> str:
        return self.me.get("username", "NotFound")

    @property
    def avatar_url(self) -> str:
        return "https://cdn.discordapp.com/avatars/{id}/{avatar}.{format}?size={size}".format(
            id=self.id, avatar=self.avatar, format="png", size=512
        )

    def _fetch(self) -> tuple[dict, bool]:
        """ Fetch data from the bot API (False = cache, True = fetch) """
        if (
            self._last_fetch and
            datetime.utcnow() - self._last_fetch < timedelta(seconds=self._cache_seconds)
        ):
            return (self._data, False)

        try:
            r = requests.get("http://localhost:13377/bot/stats")
            self._data = r.json()
        except Exception:
            # Just force a cache update regardless
            new_fake_data = self._data.copy()
            new_fake_data["ping"] = {"type": "ms", "ws": 0, "rest": 0}
            self._data = new_fake_data
            del new_fake_data

        self._last_fetch = datetime.utcnow()
        return (self._data, True)
