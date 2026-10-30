"""Generate branding and synthetic OCR fixtures without publishing screen captures."""
from pathlib import Path
import argparse
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]


def font(size):
    for name in ('C:/Windows/Fonts/times.ttf','C:/Windows/Fonts/segoeui.ttf','DejaVuSans.ttf'):
        try:return ImageFont.truetype(name,size)
        except OSError:pass
    return ImageFont.load_default()


def generate(root=ROOT,force=False):
    root=Path(root);assets=root/'desktop/assets';fixtures=root/'tests/fixtures'
    assets.mkdir(parents=True,exist_ok=True);fixtures.mkdir(parents=True,exist_ok=True)
    icon=Image.new('RGBA',(256,256),(12,9,20,255));draw=ImageDraw.Draw(icon)
    draw.polygon([(128,24),(229,128),(128,232),(27,128)],fill='#9560df')
    draw.polygon([(128,65),(189,128),(128,190),(67,128)],fill='#e9d5ff')
    draw.polygon([(128,99),(156,128),(128,157),(100,128)],fill='#331950')
    for name in ('bdo-lite.png','bdo-lite.ico'):
        path=assets/name
        if force or not path.exists():icon.save(path)
    normal=Image.new('RGB',(600,120),'#262829');draw=ImageDraw.Draw(normal)
    draw.rectangle((0,38,599,101),fill='#365a24');draw.text((18,53),'Elixir of Demihuman Hunt x 4',font=font(29),fill='white',stroke_width=1,stroke_fill='#182414')
    stack=Image.new('RGB',(660,174),'#272b2c');draw=ImageDraw.Draw(stack)
    draw.rectangle((0,20,659,86),fill='#244b68');draw.rectangle((0,96,659,162),fill='#365a24')
    draw.text((18,37),'Elixir of Fierce Demihuman Hunt x 1',font=font(27),fill='white',stroke_width=1,stroke_fill='#101c27')
    draw.text((18,113),'Elixir of Demihuman Hunt x 4',font=font(27),fill='white',stroke_width=1,stroke_fill='#182414')
    for image,name in ((normal,'item-drop-log.png'),(stack,'user-popup.png')):
        path=fixtures/name
        if force or not path.exists():image.save(path)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--force',action='store_true');parser.add_argument('--root',type=Path,default=ROOT)
    args=parser.parse_args();generate(args.root,args.force)
