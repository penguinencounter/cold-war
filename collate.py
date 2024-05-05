from glob import glob
from pathlib import Path
from shutil import copytree, copy, rmtree
from os.path import exists, isdir
from os import environ, makedirs
from rich.console import Console

term = Console()
if environ.get('GITHUB_ACTIONS', None) == 'true':
    term = Console(force_terminal=True, force_interactive=False)
term.print("[bold green]Bundling files...[/bold green]")


sources = [
    *glob('htmlgen/*.html'),
    'dist',
    'bois'
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

