"""Create a source distribution ZIP, not a Microsoft solution export."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ALLOWED={'source','topics','tools','tests','docs','contracts','validation','flows','powerapps'}
TOP={'README.md','requirements-dev.txt','.gitignore','VERSION.json'}
def package(output):
 output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
 files=[]
 for p in sorted(ROOT.rglob('*')):
  r=p.relative_to(ROOT)
  if p.is_file()and p.name!='manifest.sha256'and'__pycache__'not in r.parts and p.suffix not in {'.pyc','.zip'}and(r.parts[0]in ALLOWED or str(r)in TOP):
   if p.is_symlink():raise ValueError('Do not package symlinks: '+str(r))
   files.append(p)
 manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(ROOT))+'\n'for p in files)
 (ROOT/'manifest.sha256').write_text(manifest);files.append(ROOT/'manifest.sha256')
 with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  for p in files:z.write(p,str(Path(ROOT.name)/p.relative_to(ROOT)))
 with zipfile.ZipFile(output)as z:
  assert z.testzip()is None
  for line in manifest.splitlines():
   digest,name=line.split('  ',1);assert hashlib.sha256(z.read(ROOT.name+'/'+name)).hexdigest()==digest
 print(json.dumps({'zip':str(output),'files':len(files),'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'kind':'source_bundle_not_solution','crc_and_manifest':'PASS'},ensure_ascii=False))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--output',type=Path,required=True);x=a.parse_args();package(x.output)
