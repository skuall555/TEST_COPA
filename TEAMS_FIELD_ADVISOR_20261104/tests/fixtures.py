"""Synthetic test configuration only. Never used to generate deployment artifacts."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from build_topics import MEASURES

def config():
 names={k:'TEST_ONLY_'+k for k in ['case_id','event_key','owner_key','record_type','legacy_text','repair_text','current_snapshot','facts_history','teams_text']}
 c={'site_url':'https://test-only.sharepoint.com/sites/fixture','list_id':'11111111-1111-1111-1111-111111111111','flow_id':'22222222-2222-2222-2222-222222222222','connection_reference_logical_name':'TEST_ONLY_connection','storage_mode':'append_history_verified','identity_binding_verified':True,'powerapps_repair_filter_verified':True,'field_map':names,'record_type_values':{'field_advice':'TEST_ONLY_FIELD','repair_guidance':'TEST_ONLY_REPAIR'},'static_fields':{}}
 fields=[{'InternalName':name,'TypeAsString':'Note'if k in ['legacy_text','repair_text','current_snapshot','facts_history','teams_text']else'Text','ReadOnlyField':False,'RichText':False,'Indexed':k in ['case_id','event_key','owner_key','record_type'],'EnforceUniqueValues':k=='event_key','Required':False}for k,name in names.items()]
 return c,fields

def snap(changes=None,states=None,optional=False):
 changes=changes or {};states=states or {}
 return '\n'.join(code+'|'+changes.get(code,'高'if code in ['P01','P07','P09']else'低'if code in ['P11','P12']else'中')+'|'+states.get(code,'要確認')for code,_ in MEASURES[:14 if optional else 13])
LEGACY='【確認できた事実】\n└台所で臭気あり\n\n【初動措置　優先度：高】\n└メーターガス栓閉止：要確認　根拠：室内臭気\n\n【初動措置　優先度：中】\n└周辺住戸・建物調査：要確認\n\n【初動措置　優先度：低】\n└消防・警察への要請：要確認\n\n【高優先度の完了状況】\n└未完了あり\n\n【ネクストアクション】\n└必要な高措置を進める\n\n【確認したいこと】\n未確認の条件を教えてください。'
def request(event='e1',case='case-A',owner='owner-A',kind='field_advice',snapshot=None,text=LEGACY,operation='save'):
 return {'operation':operation,'case_id':case,'owner_key':owner,'event_key':event,'record_type':kind,'legacy_text':text,'current_snapshot':snap()if snapshot is None else snapshot,'facts_history':'台所で臭気あり。メーター閉止の報告。','source_channel':'msteams'}
