"""Consistent core snapshot: DB first, then immutable images referenced by it."""
from datetime import datetime
from pathlib import Path
import shutil
import sqlite3

root=Path(__file__).resolve().parents[1]
folder=root/'backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
folder.mkdir(parents=True)
source=sqlite3.connect(root/'data/hub/hub.sqlite3',timeout=30)
target=sqlite3.connect(folder/'hub.sqlite3')
source.backup(target)
rows=target.execute('SELECT relative_path FROM images').fetchall()
target.close();source.close()
for (relative,) in rows:
    src=root/'data/hub/images'/relative
    dst=folder/'images'/relative
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dst)
shutil.copy2(root/'.env',folder/'.env')
shutil.copytree(root/'.credentials',folder/'.credentials')
print(f'Core backup ready: {folder.name}; {len(rows)} image files. Keep this folder private.')
