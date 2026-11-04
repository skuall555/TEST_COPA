"""Patch a COPY of a real unpacked solution; preserve workflow identity/metadata."""
import argparse,copy,json,shutil
from pathlib import Path

def patch_export(root,workflow,generated,flow_id,out):
 root=Path(root).resolve();workflow=Path(workflow).resolve();out=Path(out).resolve()
 relative=workflow.relative_to(root)
 if out.exists()or out==root or root in out.parents:raise ValueError('Choose a new output directory outside the input solution')
 if flow_id.lower()not in workflow.stem.lower():raise ValueError('Workflow filename must contain the verified flow GUID')
 original=json.loads(workflow.read_text());props=original.get('properties',{})
 triggers=props.get('definition',{}).get('triggers',{})
 if not any(t.get('type')=='Request'and t.get('kind')=='Skills'for t in triggers.values()):raise ValueError('Export a real agent-called flow first (Request / Skills)')
 if not generated.get('properties',{}).get('definition'):raise ValueError('Missing generated definition')
 result=copy.deepcopy(original);result['properties']['definition']=generated['properties']['definition']
 result['properties']['connectionReferences']={**props.get('connectionReferences',{}),**generated['properties']['connectionReferences']}
 shutil.copytree(root,out);(out/relative).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 return out/relative

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--unpacked-dir',type=Path,required=True);a.add_argument('--workflow',type=Path,required=True);a.add_argument('--generated',type=Path,required=True);a.add_argument('--config',type=Path,required=True);a.add_argument('--output-dir',type=Path,required=True);x=a.parse_args()
 print(patch_export(x.unpacked_dir,x.workflow,json.loads(x.generated.read_text()),json.loads(x.config.read_text())['flow_id'],x.output_dir))
