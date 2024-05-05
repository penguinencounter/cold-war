from collections import defaultdict
from glob import glob
from os import environ, listdir, makedirs
from os.path import exists, isdir
from pathlib import Path
from shutil import copy, copytree, rmtree
from typing import NamedTuple
from bs4 import BeautifulSoup, Tag
from jinja2 import Environment, FileSystemLoader, select_autoescape
from rich.console import Console

term = Console()
if environ.get('GITHUB_ACTIONS', None) == 'true':
    term = Console(force_terminal=True, force_interactive=False)
term.print("[bold green]Merging / generating HTML...[/bold green]")


outbound = Path("htmlgen")
makedirs(outbound, exist_ok=True)

inbound = Path("templates")
jenv = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape()
)

meta_attrs = ['data-is-nav-target']
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
    if name.startswith('_') or not name.endswith('.html'):
        term.print(rf'[blue]\[skip] {name}[/]')
        continue
    template = jenv.get_template(name)
    htmlstr = template.render()
    soup = BeautifulSoup(htmlstr, 'lxml')
    this_navitem = soup.select(f'[data-is-nav-target][href="{name}"]')
    if len(this_navitem) == 1:
        current_page = this_navitem[0]
        current_page.attrs['data-current'] = ''
        
        upwards = current_page
        # look upwards for more navitems
        while (upwards := upwards.parent).name != 'nav':
            if upwards.attrs.get('data-is-nav-target') is not None:
                term.print(rf'[bright_black]\[debg] found parent navitem: {upwards.attrs}[/]')
                upwards.attrs['data-current-inside'] = ''
    else:
        term.print(rf'[bright_yellow]\[warn] wrong number of navitem matched: {len(this_navitem)}[/]')
    
    stripped = strip_meta_attrs(soup)
    term.print(rf'[bright_green]\[ ok ] {name} done;[/] [bright_blue]stripped meta attrs: {", ".join(f"{k} x{v}" for k, v in stripped.items())}[/]')

    # dump the HTML
    with open(outbound / name, 'w') as f:
        f.write(str(soup))

term.print("[bold green]Bundling files...[/bold green]")

sources = [
    *glob('htmlgen/*.html'),
    'dist'
]
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