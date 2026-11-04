"""Generate review artifacts. Never promotes local tests to tenant acceptance."""
import csv,datetime,difflib,hashlib,json,re,shutil,sys
from pathlib import Path
import yaml
from yaml_edit import nodes
from build_topics import ROOT,FILES

def main():
 v=ROOT/'validation';v.mkdir(exist_ok=True)
 md=['# 修正後YAML全文\n\n接続前の互換版です。実値確認後に接続版を生成する場合は導入手順を参照してください。\n']
 for name in FILES:
  before=(ROOT/'source'/name).read_text();after=(ROOT/'topics'/name).read_text()
  (v/(name+'.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='source/'+name,tofile='topics/'+name)))
  md+=['\n## '+name+'\n\n```yaml\n'+after.rstrip()+'\n```\n']
 (ROOT/'docs/YAML全文.md').write_text(''.join(md))
 for folder,suffix in [('source','before'),('topics','after')]:
  idx={n['id']:n for n in nodes(yaml.safe_load((ROOT/folder/FILES[1]).read_text()))if'id'in n and'kind'in n}
  (v/('legacy_renderer_'+suffix+'.txt')).write_text(idx['setVariable_itemRender']['value']+'\n')
 required={'T01','T02','T04','T08','T09','T10','T12','T13','T14','T16'}
 rows=[]
 source=(ROOT/'source/改修指示_20261104.md').read_text()
 for line in source.splitlines():
  cells=[x.strip()for x in line.strip().strip('|').split('|')]
  if cells and re.fullmatch(r'T\d{2}',cells[0]):
   rows.append({'id':cells[0],'required':str(cells[0]in required).lower(),'scenario':cells[1],'expected':cells[2],'status':'NOT_RUN','reason':'Teams/SharePoint/Power Apps実テナント接続・実行証拠なし','evidence':''})
 assert len(rows)==19
 with(v/'acceptance.csv').open('w',newline='',encoding='utf-8-sig')as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 perf=[]
 for version in ['before','after']:
  for scenario in ['text_initial','text_update','one_photo','two_photos','repair_question','repair_then_photo']:
   for trial in range(1,4):perf.append(dict(version=version,scenario=scenario,trial=trial,posted_utc='',final_reply_utc='',sharepoint_utc='',apps_visible_utc='',reply_ms='',save_ms='',apps_ms='',status='NOT_MEASURED',note='実スマホTeams計測未実施'))
 with(v/'performance.csv').open('w',newline='',encoding='utf-8-sig')as f:
  w=csv.DictWriter(f,fieldnames=list(perf[0]));w.writeheader();w.writerows(perf)
 summary={'generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base_commit':'4fa63fbcfc1ccf39d063276d9999a5ffb3166132','tenant_acceptance':'NOT_RUN','performance':'NOT_MEASURED','native_scope':'Microsoft.PowerFx.Interpreter 1.8.1 standalone; no Studio host, model or tenant execution','wdl_scope':'Generated workflow evaluated with a test-only expression runner and mocked SharePoint connector','native':{}}
 for name in ['native_results.json','native_bound_results.json']:
  data=json.loads((v/name).read_text());summary['native'][name]={g:{'total':len(data[g]),'passed':sum(bool(x['success'])for x in data[g])}for g in ['checks','renders','images']}
 log=(v/'unittest.log').read_text();match=re.search(r'Ran (\d+) tests',log);summary['unittest']={'count':int(match[1])if match else None,'success':log.rstrip().endswith('OK')}
 if not summary['unittest']['success']or any(x['passed']!=x['total']for result in summary['native'].values()for x in result.values()):raise ValueError('Local validation is not passing')
 summary['sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted((ROOT/'topics').glob('*'))}
 (v/'local_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print('Wrote diff, complete YAML, 19 NOT_RUN acceptance cases, 36 NOT_MEASURED measurements, and local validation summary')
if __name__=='__main__':main()
