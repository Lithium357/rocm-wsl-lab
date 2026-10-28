"""Read-only ELF/metadata audit. Never imports packages or loads runtime DSOs."""
from pathlib import Path
from email.parser import Parser
import csv
import json
import re
import subprocess
import sys

if len(sys.argv)!=2:
    raise SystemExit('usage: python3 -I package_manifest.py /path/to/venv')
venv=Path(sys.argv[1]).expanduser().resolve()
sites=sorted((venv/'lib').glob('python*/site-packages'))
assert len(sites)==1
site=sites[0]
core=site/'_rocm_sdk_core'
roots=[(core,'$CORE'),(venv,'$VENV'),(Path('/opt/rocm'),'$OPT_ROCM'),(Path.home(),'$HOME')]
def clean(s):
    for path,label in roots:
        s=s.replace(str(path),label)
    return s

packages=[]
for directory in sorted(site.glob('*.dist-info')):
    path=directory/'METADATA'
    if not path.exists(): continue
    # Only public package names/versions; no direct_url, installer or provenance data.
    meta=Parser().parsestr(path.read_text(errors='replace'),headersonly=True)
    name=meta.get('Name','')
    if name.lower().startswith(('rocm','torch','pytorch')):
        record=directory/'RECORD'
        rocdxg=[]
        if record.exists():
            with record.open(newline='') as stream:
                rocdxg=[row[0] for row in csv.reader(stream) if row and Path(row[0]).name.startswith('librocdxg.so')]
        packages.append({'name':name,'version':meta.get('Version',''),'rocdxg_record_paths':rocdxg})

targets=[]
for base in [core/'lib',Path('/opt/rocm/lib')]:
    for pattern in ['librocdxg.so*','libhsa-runtime64.so*','librocprofiler-sdk.so*','libamdhip64.so*']:
        targets.extend(sorted(base.glob(pattern)))
for base in [core/'bin',venv/'bin']:
    for name in ['rocprofv3','rocprofv3-avail']:
        path=base/name
        if path.exists(): targets.append(path)
entries=[]
for path in dict.fromkeys(targets):
    with path.open('rb') as stream: magic=stream.read(4)
    entry={'path':clean(str(path)),'symlink':path.is_symlink(),'resolved_path':clean(str(path.resolve())),
           'elf':magic==b'\x7fELF'}
    if entry['elf']:
        proc=subprocess.run(['readelf','-d',str(path)],check=True,capture_output=True,text=True,timeout=10)
        tags={}
        for line in proc.stdout.splitlines():
            match=re.search(r'\((SONAME|NEEDED|RPATH|RUNPATH)\).*?\[(.*?)\]',line)
            if match: tags.setdefault(match[1],[]).append(clean(match[2]))
        entry['dynamic']=tags
        if path.name.startswith('librocdxg.so'):
            symbols=subprocess.run(['readelf','--dyn-syms','--wide',str(path)],check=True,capture_output=True,text=True,timeout=10)
            exported=set()
            for line in symbols.stdout.splitlines():
                parts=line.split()
                if len(parts)>=8 and parts[6]!='UND': exported.add(parts[7].split('@')[0])
            entry['topology_export_presence']={name:name in exported for name in [
                'hsaKmtOpenKFD','hsaKmtAcquireSystemProperties','hsaKmtGetNodeProperties',
                'hsaKmtReleaseSystemProperties','hsaKmtCloseKFD','DxgAbiCheck']}
    entries.append(entry)
summary={'scope':'read-only metadata and readelf; no runtime import, dlopen, profiler execution or GPU access',
         'python_for_audit':sys.version.split()[0],'packages':packages,'files':entries,
         'limitations':'ELF tags are static evidence only; dlopen names and runtime selection cannot be inferred from DT_NEEDED alone'}
root=Path(__file__).resolve().parent
(root/'package-resolution-manifest.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
