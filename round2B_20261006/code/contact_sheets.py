from pathlib import Path
from PIL import Image,ImageDraw
import sys
build='build03' if '--build03' in sys.argv else 'build02'
root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006/manuscript')/('renders_'+build)
for kind in ['main','appendix']:
 files=sorted((root/kind).glob('page-*.png'))
 for start in range(0,len(files),12):
  canvas=Image.new('RGB',(1000,1120),'#bbbbbb');draw=ImageDraw.Draw(canvas)
  for j,f in enumerate(files[start:start+12]):
   im=Image.open(f);im.thumbnail((240,340));x=j%4*250;y=j//4*370
   canvas.paste(im,(x,y+24));draw.text((x+4,y+4),f.stem,fill='black')
  canvas.save(root/f'{kind}_contact_{start//12+1:02}.png')
 print(kind,len(files),flush=True)
