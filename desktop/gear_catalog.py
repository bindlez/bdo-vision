"""Small verified nonmarket equipment supplement, read from the local index."""
from pathlib import Path
import sqlite3
from item_catalog import DiskItemDatabase

# These are item identities, not estimated tradable prices or AP/DP data.
# Kharazad's 0..10 progression is documented by Pearl Abyss:
# https://blackdesert.pearlabyss.com/Asia/en-US/News/Notice/Detail?_boardNo=6504
EXTRAS=(('Kharazad Ring',1),('Kharazad Necklace',2),('Kharazad Earring',3),('Kharazad Belt',4))


def equipment_extras(profile):
    path=Path(profile)/'item-catalog.sqlite3'
    if not path.exists():return []
    try:database=DiskItemDatabase(path)
    except (OSError,ValueError,sqlite3.Error):return []
    result=[]
    for name,sub in EXTRAS:
        matches=database.candidates(name)
        if len(matches)!=1 or matches[0]['name']!=name:continue
        result.append({**matches[0],'mainCategory':20,'subCategory':sub,'marketListed':False,'maxEnhance':10})
    return result
