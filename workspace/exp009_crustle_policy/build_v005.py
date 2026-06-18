"""Build v005: dedicated Crustle control policy + Crustle deck."""
import json, os, shutil, tarfile
HERE=os.path.dirname(os.path.abspath(__file__)); REPO=os.path.abspath(os.path.join(HERE,'..','..'))
CG=os.path.join(REPO,'data','sim_sample','cg'); BUILD=os.path.join(HERE,'build')
CRUSTLE=json.load(open(os.path.join(HERE,'crustle_deck.json')))
os.makedirs(BUILD,exist_ok=True)
# main.py = crustle_policy.py verbatim (already defines crash-safe agent() + reads deck.csv)
shutil.copy(os.path.join(HERE,'crustle_policy.py'), os.path.join(BUILD,'main.py'))
assert len(CRUSTLE)==60
open(os.path.join(BUILD,'deck.csv'),'w').write("\n".join(map(str,CRUSTLE))+"\n")
dst=os.path.join(BUILD,'cg')
if os.path.exists(dst): shutil.rmtree(dst)
shutil.copytree(CG,dst,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pyo'))
tarp=os.path.join(BUILD,'submission.tar.gz')
with tarfile.open(tarp,'w:gz') as tar:
    tar.add(os.path.join(BUILD,'main.py'),arcname='main.py')
    tar.add(os.path.join(BUILD,'deck.csv'),arcname='deck.csv')
    for root,_d,files in os.walk(dst):
        for fn in files:
            if fn.endswith(('.pyc','.pyo')): continue
            full=os.path.join(root,fn); tar.add(full,arcname=os.path.join('cg',os.path.relpath(full,dst)))
names=tarfile.open(tarp).getnames()
assert {'main.py','deck.csv','cg/api.py','cg/libcg.so'}<=set(names)
print('built',tarp,'| top:',sorted(n for n in names if '/' not in n),'files',len(names))
