from glob import glob
from pathlib import Path
from shutil import copytree, copy, rmtree
from os.path import exists, isdir
from os import makedirs


sources = [
    *glob('htmlgen/*.html'),
    'dist'
]
destination = Path("deploy")
rmtree(destination, ignore_errors=True)
makedirs(destination, exist_ok=True)

for source in sources:
    if not exists(source):
        print(f"[warn] {source} does not exist")
        continue
    if isdir(source):
        full_dest = destination / source
        copytree(source, full_dest)
    else:
        source_path = Path(source)
        full_dest = destination / source_path.name
        copy(source, full_dest)
