from glob import glob
from pathlib import Path
from shutil import copytree, copy
from os.path import exists, isdir
from os import makedirs


sources = [
    *glob('*.html'),
    'dist'
]
destination = Path("deploy")
makedirs(destination, exist_ok=True)

for source in sources:
    if not exists(source):
        print(f"[warn] {source} does not exist")
        continue
    full_dest = destination / source
    if isdir(source):
        copytree(source, full_dest)
    else:
        copy(source, full_dest)
