import requests

from io import BytesIO
from PIL import Image, ImageFont, ImageDraw
from datetime import datetime, timedelta


class xelA:
    def __init__(self, _cache_seconds: int = 60):
        self._data = {}
        self._last_fetch = None
        self._cache_seconds = _cache_seconds

    def __str__(self):
        return f"{self.username}#{self.discriminator}"

    def __int__(self):
        return int(self.id)

    @property
    def me(self):
        return self._data.get("@me", {})

    @property
    def last_reboot(self):
        return self._data.get("last_reboot", 0)

    @property
    def ram(self):
        return self._data.get("ram", 0)

    @property
    def database(self):
        return self._data.get("database", 0)

    @property
    def servers(self):
        return self._data.get("servers", 0)

    @property
    def users(self):
        return self._data.get("users", 0)

    @property
    def avg_users_server(self):
        return self._data.get("avg_users_server", 0)

    @property
    def ping(self):
        return self._data.get("ping", {})

    @property
    def ping_ws(self):
        return self.ping.get("ws", 0)

    @property
    def ping_rest(self):
        return self.ping.get("rest", 0)

    @property
    def id(self):
        return self.me.get("id", 1337)

    @property
    def avatar(self):
        return self.me.get("avatar", "")

    @property
    def discriminator(self):
        return self.me.get("discriminator", "0000")

    @property
    def username(self):
        return self.me.get("username", "NotFound")

    @property
    def avatar_url(self):
        return "https://cdn.discordapp.com/avatars/{id}/{avatar}.{format}?size={size}".format(
            id=self.id, avatar=self.avatar, format="png", size=512
        )

    def _fetch(self):
        """ Fetch data from the bot API (False = cache, True = fetch) """
        if self._last_fetch and datetime.utcnow() - self._last_fetch < timedelta(seconds=self._cache_seconds):
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


def font_loader(font: str, size: int):
    return ImageFont.truetype(font, size)


def stats_image(stats: xelA):
    base = Image.new("RGBA", (800, 418), (24, 24, 24, 255))
    font_name = "./static/fonts/snowstorm.ttf"
    _primary = (255, 255, 255)
    _secondary = (150, 150, 150)
    _title = font_loader(font_name, 60)
    _desc = font_loader(font_name, 48)

    _stats_list = [
        ("Users", f"{stats.users:,}"),
        ("Servers", f"{stats.servers:,}"),
        ("avg. users/servers", f"{stats.avg_users_server:,}"),
    ]

    d = ImageDraw.Draw(base)
    for i, values in enumerate(_stats_list):
        title, desc = values
        jump = i * 140
        d.text((20, 20 + jump), title, font=_title, fill=_primary)
        d.text((60, 80 + jump), desc, font=_desc, fill=_secondary)

    bio = BytesIO()
    base.save(bio, "PNG")
    bio.seek(0)
    return bio
