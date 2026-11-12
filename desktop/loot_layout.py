"""Find a saved BDO Item Log position without reading game memory."""
import math
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET

_layout_cache = None


def documents_folders():
    folders = []
    if os.name == 'nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as key:
                folders.append(Path(os.path.expandvars(winreg.QueryValueEx(key, 'Personal')[0])))
        except OSError:
            pass
    folders.extend((Path.home() / 'Documents', Path.home() / 'OneDrive' / 'Documents'))
    return list(dict.fromkeys(folders))


def saved_item_log(text, bounds, index=159, window_index=None):
    """Return a candidate desktop rectangle for a matching saved resolution."""
    _, left, top, right, bottom = bounds
    width, height = right - left, bottom - top
    resolution = re.search(r'<Resolution\b[^>]{0,500}/>', text)
    scale_tag = re.search(r'<UiScale\b[^>]{0,500}/>', text)
    tags = re.findall(r'<UIData\b[^>]{0,1000}>', text)
    if not resolution or not scale_tag:
        raise ValueError('Saved game resolution or UI scale is unavailable')
    try:
        size = ET.fromstring(resolution.group()).attrib
        scale = float(ET.fromstring(scale_tag.group()).attrib['Value'])
        rows = [ET.fromstring(tag if tag.endswith('/>') else tag[:-1] + '/>').attrib for tag in tags]
        rows = [row for row in rows if row.get('Index') == str(index) and 'PosX' in row and 'PosY' in row]
        if window_index is not None:
            rows = [row for row in rows if row.get('WindowIndex') == str(window_index)]
        if len(rows) != 1:
            raise ValueError('Saved Item Log position is missing or ambiguous')
        row = rows[0]
        if row.get('IsShow', '').lower() != 'true':
            raise ValueError('Item Log is hidden in the saved BDO layout')
        if int(size['Width']) != width or int(size['Height']) != height:
            raise ValueError('Saved BDO resolution differs from the current game window')
        if not math.isfinite(scale) or not .5 <= scale <= 2:
            raise ValueError('Saved UI scale is invalid')
        x, y = int(row['PosX']), int(row['PosY'])
        anchor = row.get('PendingType')
        if anchor not in ('LeftTop', 'LeftBottom', 'RightTop', 'RightBottom'):
            raise ValueError('Saved UI position has an unsupported anchor')
        if anchor.startswith('Right'):
            x = width - x
        if anchor.endswith('Bottom'):
            y = height - y
        if index in (9, 21, 32):
            nominal_width, nominal_height = int(row['SizeX']), int(row['SizeY'])
        else:
            nominal_width, nominal_height = (350, 300) if index == 159 else (420, 84)
    except (ET.ParseError, KeyError, OverflowError) as exc:
        raise ValueError('Saved Item Log layout is invalid') from exc
    if not 0 <= x < width or not 0 <= y < height:
        raise ValueError('Saved Item Log is outside the game window')
    size_scale = 1 if index in (9, 21, 32) else scale
    box_width = min(round(nominal_width * size_scale), width - x)
    box_height = min(round(nominal_height * size_scale), height - y)
    if box_width < 100 or box_height < (60 if index == 159 else 35):
        raise ValueError('Saved Item Log is too close to the game window edge')
    return left + x, top + y, box_width, box_height


def saved_text_feed(text, bounds):
    """Choose a unique visible, separate chat window with personal items enabled."""
    if '<!DOCTYPE' in text.upper():
        raise ValueError('Saved BDO layout contains an unsupported document type')
    try:
        root = ET.fromstring('<root>' + text + '</root>')
    except ET.ParseError as exc:
        raise ValueError('Saved BDO chat layout is invalid') from exc
    matches = []
    for row in root.findall('.//UIData[@Index="32"]'):
        if row.get('IsShow') != 'true' or row.get('IsUsing') != 'true' or row.get('IsCombinedToMainPanel') != 'false':
            continue
        system = any(item.get('key') == 'System' and item.get('value') == 'true' for item in row.findall('ChatType'))
        personal = any(item.get('key') == 'ChatSystemType_PrivateItem' and item.get('value') == 'true'
                       for item in row.findall('ChatSystemType'))
        if system and personal and row.get('WindowIndex') is not None:
            matches.append(row.get('WindowIndex'))
    if len(matches) != 1:
        return None
    return saved_item_log(text, bounds, 32, matches[0])


def find_saved_layout(bounds, documents=None):
    global _layout_cache
    if not bounds or len(bounds) != 5 or bounds[3] <= bounds[1] or bounds[4] <= bounds[2]:
        raise ValueError('Show one BDO game window before finding the Item Log')
    folders = documents if documents is not None else documents_folders()
    candidates = []
    for documents_folder in folders:
        root = Path(documents_folder) / 'Black Desert' / 'UserCache'
        if root.is_dir():
            candidates.extend(path for path in root.glob('*/gamevariable.xml') if path.is_file())
    candidates = sorted(set(candidates), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        raise ValueError('No saved BDO layout found. Save the layout in Edit UI first')
    # The newest account layout is selected, never an older character's layout.
    path = candidates[0]
    metadata = path.stat()
    if metadata.st_size > 4_000_000:
        raise ValueError('Saved BDO layout is too large to read')
    key = (path, metadata.st_mtime_ns, metadata.st_size, tuple(bounds))
    if _layout_cache and _layout_cache[0] == key:
        return dict(_layout_cache[1])
    try:
        text = path.read_text(encoding='utf-8-sig')
    except (OSError, UnicodeError) as exc:
        raise ValueError('Unable to read the saved BDO layout') from exc
    after = path.stat()
    if (after.st_mtime_ns, after.st_size) != (metadata.st_mtime_ns, metadata.st_size):
        raise ValueError('BDO is saving the layout. Try again shortly')
    result = {}
    for name, index in (('item_log', 159), ('rare_log', 161), ('quest_widget', 21), ('minimap', 9)):
        try:
            result[name] = saved_item_log(text, bounds, index)
        except ValueError:
            result[name] = None
    try:
        result['text_feed'] = saved_text_feed(text, bounds)
    except ValueError:
        result['text_feed'] = None
    _layout_cache = (key, dict(result))
    return result


def find_saved_item_log(bounds, documents=None):
    layout = find_saved_layout(bounds, documents)
    normal = layout['item_log']
    if normal is None:
        raise ValueError('Saved Item Log position is unavailable or incompatible with the game window')
    return normal, layout['rare_log']
