"""Extract user-provided static design reference; never executes its scripts."""
from pathlib import Path
import stat
import zipfile
ROOT=Path(__file__).resolve().parents[1]
source=Path(r'C:/Users/ASUS/Downloads/portfolio-x-main (1).zip')
destination=(ROOT/'.cache/portfolio-reference').resolve()
with zipfile.ZipFile(source) as archive:
    if sum(i.file_size for i in archive.infolist())>5_000_000:raise ValueError('Unexpected archive size.')
    for item in archive.infolist():
        target=(destination/item.filename).resolve()
        if not target.is_relative_to(destination) or stat.S_ISLNK(item.external_attr>>16):raise ValueError('Unsafe archive entry.')
    archive.extractall(destination)
for name in ('LICENSE','README.md','index.html','styles.css','field.css','main.js'):
    text=(destination/'portfolio-x-main'/name).read_text(encoding='utf-8')
    print(f'FILE {name}\n{text[:14000]}\n')
