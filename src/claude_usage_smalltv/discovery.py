"""Find SmallTV displays on the local /24 network."""

from __future__ import annotations

import ipaddress
import re
import socket
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import requests

SMALLTV_TITLE = re.compile(r"geekmagic|smalltv|smart weather clock", re.IGNORECASE)
TITLE_TAG = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class Host:
    ip: str
    title: str

    @property
    def looks_like_smalltv(self) -> bool:
        return bool(SMALLTV_TITLE.search(self.title))


def local_ipv4() -> str:
    # UDP "connect" only selects the outgoing interface; no packet is sent.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("192.0.2.1", 80))
        return s.getsockname()[0]


def port_open(ip: str, port: int = 80, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def page_title(ip: str, timeout: float = 8.0) -> str:
    try:
        match = TITLE_TAG.search(requests.get(f"http://{ip}/", timeout=timeout).text)
    except requests.RequestException:
        return ""
    return match.group(1).strip() if match else ""


def scan(subnet: str | None = None, timeout: float = 2.0, workers: int = 128) -> list[Host]:
    """Return every host with port 80 open, SmallTV-looking ones first.

    The ESP8266 sleeps between beacons and may miss a short probe; if your display is not
    listed, read its IP on the screen right after power-on.
    """
    me = local_ipv4()
    network = ipaddress.ip_network(subnet or f"{me}/24", strict=False)
    candidates = [str(h) for h in network.hosts() if str(h) != me]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        reachable = pool.map(lambda ip: port_open(ip, timeout=timeout), candidates)
        alive = [ip for ip, ok in zip(candidates, reachable, strict=True) if ok]
        titles = list(pool.map(page_title, alive))
    hosts = [Host(ip, title) for ip, title in zip(alive, titles, strict=True)]
    return sorted(hosts, key=lambda h: not h.looks_like_smalltv)
