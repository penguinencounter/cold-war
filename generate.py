from io import BytesIO
import json
from collections import defaultdict
from functools import cache
from glob import glob
from math import gcd
from os import environ, listdir, makedirs
from os.path import exists, isdir
from pathlib import Path
from shutil import copy, copytree, rmtree
from string import ascii_lowercase
import string
from typing import NamedTuple

from bs4 import BeautifulSoup, Tag
from jinja2 import Environment, FileSystemLoader, select_autoescape
import requests
from rich.console import Console
from PIL import Image, UnidentifiedImageError

term = Console()
is_gha = environ.get("GITHUB_ACTIONS", None) == "true"
if is_gha:
    term = Console(force_terminal=True, force_interactive=False)
term.print("[bold green]Merging / generating HTML...[/bold green]")


outbound = Path("htmlgen")
makedirs(outbound, exist_ok=True)

inbound = Path("templates")
jenv = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape())
ua = "StaticBuildBot/0.0.0 (github:penguinencounter/cold-war. Tell penguinencounter2 at gmail if I'm being problematic.) python-requests/2.31.0"
if is_gha:
    ua += " (running on GitHub Actions)"
else:
    ua += " (running locally)"

sess = requests.Session()
sess.headers.update({
    'User-Agent': ua
})

enable_caching = not (is_gha or environ.get("NO_CACHE") is not None)

cachefile = Path(".image_cache")
fscache_data: dict[str, str] = {}
if enable_caching and cachefile.exists():
    with open(cachefile, "r", encoding="UTF-8") as f:
        fscache_data = json.load(f)


def template_func(fn: callable):
    jenv.globals[fn.__name__] = fn
    return fn


def trunc(string, length):
    if len(string) > length:
        return string[: length - 1] + "…"
    return string


def hexdump(byte: bytes, count: int = 16):
    sample = byte[:count]
    hexdump_asci = ""
    hexdump_raw = sample.hex()
    for char in sample:
        if (
            chr(char)
            in string.ascii_letters
            + string.digits
            + "!@#$%^&*()_+-=[]{},./<>?'\"\\| "
        ):
            hexdump_asci += chr(char)
        else:
            hexdump_asci += "."
    return f'{hexdump_raw} {hexdump_asci}'


@template_func
def get_image_aspect(url: str):
    if (result := fscache_data.get(url)) is not None:
        term.print(
            rf"[bright_blue]\[info] using cached {result} for {trunc(url, 48)}[/]"
        )
        return result
    term.print(rf'[bright_black]\[debg] requesting image: {trunc(url, 48)}')
    resp: requests.Response = sess.get(url, allow_redirects=True)
    if resp.status_code != 200:
        term.print(
            rf"[bright_red]\[err!] remote request failed: [bold]{resp.status_code})[/] at {trunc(url, 48)}[/] [blue]using fallback[/]"
            f"\n content preview: {resp.content.decode('utf-8')}"
        )
        # this kinda works?
        return "1/1"
    raw_data = BytesIO(resp.content)
    try:
        image_data = Image.open(raw_data)
        factor = gcd(image_data.width, image_data.height)
        dim = f'{image_data.width // factor}/{image_data.height // factor}'
        term.print(rf'[green]\[ ok ] {trunc(url, 48)} aspect ratio is {dim}')
        fscache_data[url] = dim
        return dim
    except UnidentifiedImageError:
        term.print(
            rf"[bright_red]\[err!] failed to read image at {trunc(url, 48)} | first raw bytes follow:[/]"
            f"\n  [red]{hexdump(resp.content, 16)}[/]"
        )
        return "1/1"


meta_attrs = ["data-is-nav-target"]


def strip_meta_attrs(tag: Tag):
    drop_count = defaultdict(int)
    sentinel = object()

    for attr in meta_attrs:
        if tag.attrs.get(attr, sentinel) is not sentinel:
            drop_count[attr] += 1
            del tag[attr]
    for child in tag.children:
        if isinstance(child, Tag):
            for k, v in strip_meta_attrs(child).items():
                drop_count[k] += v
    return drop_count


for name in listdir(inbound):
    if name.startswith("_") or not name.endswith(".html"):
        term.print(rf"[blue]\[skip] {name}[/]")
        continue
    template = jenv.get_template(name)
    htmlstr = template.render()
    soup = BeautifulSoup(htmlstr, "lxml")
    this_navitem = soup.select(f'[data-is-nav-target][href="{name}"]')
    if len(this_navitem) == 1:
        current_page = this_navitem[0]
        current_page.attrs["data-current"] = ""

        upwards = current_page
        # look upwards for more navitems
        while (upwards := upwards.parent).name != "nav":
            if upwards.attrs.get("data-is-nav-target") is not None:
                upwards.attrs["data-current-inside"] = ""
    else:
        term.print(
            rf"[bright_yellow]\[warn] wrong number of navitem matched: {len(this_navitem)}[/]"
        )

    stripped = strip_meta_attrs(soup)
    term.print(
        rf'[bright_green]\[ ok ] {name} done;[/] [bright_blue]stripped meta attrs: {", ".join(f"{k} x{v}" for k, v in stripped.items())}[/]'
    )

    # dump the HTML
    with open(outbound / name, "w") as f:
        f.write(str(soup))

if enable_caching:
    with open(cachefile, 'w') as f:
        json.dump(fscache_data, f)

term.print("[bold green]Bundling files...[/bold green]")

sources = [*glob("htmlgen/*.html"), "dist"]
destination = Path("deploy")
rmtree(destination, ignore_errors=True)
makedirs(destination, exist_ok=True)

files = 0
dirs = 0

for source in sources:
    if not exists(source):
        term.print(rf"[bright_yellow]\[warn] {source} does not exist, skipping[/]")
        continue
    if isdir(source):
        dirs += 1
        full_dest = destination / source
        copytree(source, full_dest)
    else:
        files += 1
        source_path = Path(source)
        full_dest = destination / source_path.name
        copy(source, full_dest)

term.print(rf"[bright_green]\[ ok ] {files} files and {dirs} directories bundled[/]")
