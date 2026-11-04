"""Generate an agent-called SharePoint adapter only from verified tenant mappings.
The JSON is a workflow definition for a real exported agent flow, not an importable solution ZIP.
"""
from pathlib import Path
import argparse,json,uuid,re,urllib.parse
from build_topics import MEASURES,ROOT
INPUTS=['operation','case_id','owner_key','event_key','record_type','legacy_text','current_snapshot','facts_history','source_channel']
OUTPUTS=['status','case_id','item_id','teams_text','previous_status','previous_snapshot','case_facts','error_code']
def S(x):return "'"+str(x).replace("'","''")+"'"
def F(name,*args):return name+'('+','.join(args)+')'
def B(name):return ('outputs'if name in {'Previous_snapshot','Action_labels','Final_teams_text','Snapshot_rows'}else'body')+'('+S(name)+')'
def T(key):return "triggerBody()?['"+key+"']"
def G(obj,key):return obj+"?['"+key+"']"
def E(x):return '@'+(F('string',x)if x.startswith("'")else x)

def validate_config(c,fields):
 for k in ['site_url','list_id','flow_id','connection_reference_logical_name']:
  if not isinstance(c.get(k),str)or not c[k].strip():raise ValueError('Missing verified deployment value: '+k)
 u=urllib.parse.urlsplit(c['site_url'])
 if u.scheme!='https'or not u.hostname or not u.hostname.endswith('.sharepoint.com')or u.username or u.password or u.query or u.fragment:raise ValueError('Use the actual HTTPS SharePoint site URL without tokens or credentials')
 for k in ['list_id','flow_id']:uuid.UUID(c[k])
 if c.get('storage_mode')!='append_history_verified':raise ValueError('Verify the existing append/upsert semantics first; this adapter requires compatible append history')
 if c.get('identity_binding_verified')is not True or c.get('powerapps_repair_filter_verified')is not True:raise ValueError('Identity binding and Power Apps repair exclusion must be verified before generating a deployment')
 m=c.get('field_map',{});catalog={x['InternalName']:x for x in fields}
 expected={'case_id':{'Text'},'event_key':{'Text'},'owner_key':{'Text'},'record_type':{'Text','Choice'},'legacy_text':{'Note'},'repair_text':{'Note'},'current_snapshot':{'Note'},'facts_history':{'Note'},'teams_text':{'Note'}}
 if len(set(m.values()))!=len(expected):raise ValueError('Use distinct confirmed fields for all mappings; legacy and repair text must not share a parser column')
 for role,types in expected.items():
  name=m.get(role)
  if not name or name not in catalog:raise ValueError('Missing actual field metadata: '+role)
  meta=catalog[name]
  if meta.get('TypeAsString')not in types or meta.get('ReadOnlyField'):raise ValueError('Wrong or read-only field type: '+role)
  if meta.get('TypeAsString')=='Note'and meta.get('RichText',False):raise ValueError('Plain multi-line text required to preserve separators: '+role)
 if not catalog[m['event_key']].get('EnforceUniqueValues')or not catalog[m['event_key']].get('Indexed'):raise ValueError('Event key must be indexed and enforce unique values')
 for role in ['case_id','owner_key','record_type']:
  if not catalog[m[role]].get('Indexed'):raise ValueError('Index the filtered lookup field: '+role)
 if catalog[m['case_id']].get('EnforceUniqueValues'):raise ValueError('CaseId is unique: preserve the existing upsert flow; do not use this append adapter')
 values=c.get('record_type_values',{})
 if any(not isinstance(values.get(k),str)or not values[k]for k in ['field_advice','repair_guidance'])or values['field_advice']==values['repair_guidance']:raise ValueError('Confirm distinct existing/additive record-type values')
 typ=catalog[m['record_type']]
 if typ.get('TypeAsString')=='Choice'and any(v not in typ.get('Choices',[])for v in values.values()):raise ValueError('Record-type choice is absent from actual SharePoint choices')
 mapped=set(m.values())|set(c.get('static_fields',{}))
 for n in c.get('static_fields',{}):
  if n not in catalog or catalog[n].get('ReadOnlyField'):raise ValueError('Invalid static field '+n)
 for meta in fields:
  if meta.get('Required')and not meta.get('ReadOnlyField')and meta['InternalName']not in mapped and meta['InternalName']not in {'ContentType','ContentTypeId','Attachments'}:raise ValueError('Unmapped required field: '+meta['InternalName'])
 return c

def compose(value,after=None):return {'type':'Compose','inputs':value,'runAfter':after or {}}
def select(source,expression,after):return {'type':'Select','inputs':{'from':E(source),'select':E(expression)},'runAfter':after}
def query(source,predicate,after):return {'type':'Query','inputs':{'from':E(source),'where':E(predicate)},'runAfter':after}
def respond(status,case=None,item=None,teams=None,previous_status=None,snapshot=None,facts=None,error=None):
 body={'status':S(status),'case_id':case or T('case_id'),'item_id':item or "''",'teams_text':teams or "''",'previous_status':previous_status or "'unavailable'",'previous_snapshot':snapshot or "''",'case_facts':facts or "''",'error_code':S(error or '')}
 return {'type':'Response','kind':'Skills','inputs':{'statusCode':200,'body':{k:E(v)for k,v in body.items()},'schema':{'type':'object','properties':{k:{'type':'string','title':k,'x-ms-content-hint':'TEXT','x-ms-dynamically-added':True}for k in OUTPUTS}}},'runAfter':{}}

def generate(c,fields):
 validate_config(c,fields);m=c['field_map'];rv=c['record_type_values']
 def escape(x):return F('replace',x,S("'"),S("''"))
 scoped=F('concat',S(m['case_id']+" eq '"),escape(T('case_id')),S("' and "+m['owner_key']+" eq '"),escape(T('owner_key')),S("'"))
 def sp(op,parameters,after=None):return {'type':'OpenApiConnection','inputs':{'host':{'apiId':'/providers/Microsoft.PowerApps/apis/shared_sharepointonline','operationId':op,'connectionName':'shared_sharepointonline'},'parameters':{'dataset':c['site_url'],'table':c['list_id'],**parameters},'retryPolicy':{'type':'fixed','count':1,'interval':'PT2S'}},'runAfter':after or {}}
 def getlatest(filter_expr):return sp('GetItems',{'$filter':E(filter_expr),'$orderby':'ID desc','$top':1})
 def firstrow(action):return F('first',G(B(action),'value'))
 def cell(action,role):return F('coalesce',G(firstrow(action),m[role]),"''")
 def exists(action):return F('greater',F('length',G(B(action),'value')),'0')
 latestfilter=F('concat',scoped,S(" and "+m['record_type']+" eq '"+rv['field_advice'].replace("'","''")+"'"))
 # Pure data operations compare stable item IDs; no LLM and no per-item connector calls.
 current_id=F('first',F('split','item()',S('|')))
 current_p=F('first',F('skip',F('split','item()',S('|')),'1'))
 current_s=F('last',F('split','item()',S('|')))
 previous=F('first',F('split',F('last',F('split',F('concat',S('\n'),B('Previous_snapshot')),F('concat',S('\n'),current_id,S('|')))),S('\n')))
 prior_exists=F('contains',F('concat',S('\n'),B('Previous_snapshot')),F('concat',S('\n'),current_id,S('|')))
 old_p=F('first',F('split',previous,S('|')));old_s=F('last',F('split',previous,S('|')))
 label=F('coalesce',G(B('Action_labels'),'DUMMY'),current_id) # dynamic dictionary accessor below
 label=F('coalesce',B('Action_labels')+'?['+current_id+']',current_id)
 changes=F('if',F('not',prior_exists),F('concat',S('・'),label,S('：新規項目（'),current_p,S('／'),current_s,S('）')),F('if',F('not',F('equals',old_p,current_p)),F('concat',S('・'),label,S('：'),old_p,S(' → '),current_p),F('if',F('not',F('equals',old_s,current_s)),F('concat',S('・'),label,S('：状態 '),old_s,S(' → '),current_s,S('（優先度は同じ）')),"''")))
 removed=F('if',F('not',F('contains',F('concat',S('\n'),T('current_snapshot')),F('concat',S('\n'),current_id,S('|')))),F('concat',S('・'),label,S('：今回は未判定（解消とは判定しません）')),"''")
 def section(head,nexthead):return F('trim',F('first',F('split',F('last',F('split',T('legacy_text'),S(head))),S(nexthead))))
 high=section('【初動措置　優先度：高】','【初動措置　優先度：中】');medium=section('【初動措置　優先度：中】','【初動措置　優先度：低】');low=section('【初動措置　優先度：低】','【高優先度の完了状況】')
 checks=F('trim',F('last',F('split',T('legacy_text'),S('【確認したいこと】'))));nxt=section('【ネクストアクション】','【確認したいこと】')
 def human(x):return F('replace',F('replace',x,S('└なし'),S('・該当なし')),S('└'),S('・'))
 merged=F('concat',F('join',B('Nonempty_changes'),S('\n')),S('\n'),F('join',B('Nonempty_removed'),S('\n')))
 previous_valid=F('and',F('not',F('empty',B('Previous_snapshot'))),F('equals',F('length',B('Invalid_previous_rows')),'0'),F('equals',F('length',F('union',B('Previous_ids'),B('Previous_ids'))),F('length',B('Previous_ids'))),*[F('contains',F('concat',S('\n'),B('Previous_snapshot')),S('\n'+code+'|'))for code,_ in MEASURES[:13]])
 delta=F('if',exists('Get_latest_field'),F('concat',S('\n\n【① 前回報告からの変更点】\n'),F('if',previous_valid,F('if',F('empty',F('trim',merged)),S('前回から優先度の変更なし'),F('trim',merged)),S('前回比較は現在できません。保存された前回判定データが不足または不正です。'))),"''")
 teams=F('concat',S('📍 現場アドバイス'),delta,S('\n\n【② 初動措置の優先度】\n🔴 高\n'),human(high),S('\n🟠 中\n'),human(medium),S('\n🟢 低\n'),human(low),S('\n\n【③ 確認したいこと】\n'),checks,S('\n\n【④ ネクストアクション】\n'),human(nxt))
 field_actions={'Get_latest_field':getlatest(latestfilter),'Previous_snapshot':compose(E(cell('Get_latest_field','current_snapshot')),{'Get_latest_field':['Succeeded']}),'Action_labels':compose(dict(MEASURES),{'Previous_snapshot':['Succeeded']}),'Changes':select(F('split',T('current_snapshot'),S('\n')),changes,{'Action_labels':['Succeeded']}),'Nonempty_changes':query(B('Changes'),F('not',F('empty','item()')),{'Changes':['Succeeded']}),'Removed':select(F('if',F('empty',B('Previous_snapshot')),'json(\'[]\')',F('split',B('Previous_snapshot'),S('\n'))),removed,{'Nonempty_changes':['Succeeded']}),'Nonempty_removed':query(B('Removed'),F('not',F('empty','item()')),{'Removed':['Succeeded']}),'Final_teams_text':compose(E(teams),{'Nonempty_removed':['Succeeded']})}
 def create_parameters(repair=False):
  values={m['case_id']:T('case_id'),m['owner_key']:T('owner_key'),m['event_key']:T('event_key'),m['record_type']:S(rv['repair_guidance'if repair else'field_advice']),m['teams_text']:T('legacy_text')if repair else B('Final_teams_text')}
  if repair:values[m['repair_text']]=T('legacy_text')
  else:values.update({m['legacy_text']:T('legacy_text'),m['current_snapshot']:T('current_snapshot'),m['facts_history']:T('facts_history')})
  return {'item/'+k:E(v)for k,v in values.items()}|{'item/'+k:v for k,v in c.get('static_fields',{}).items()}
 field_actions['Create_field_record']=sp('PostItem',create_parameters(),{'Final_teams_text':['Succeeded']})
 field_actions['Reply_field']=respond('saved',item=F('string',G(B('Create_field_record'),'ID')),teams=B('Final_teams_text'),previous_status=F('if',exists('Get_latest_field'),F('if',previous_valid,S('found'),S('unavailable')),S('none')),snapshot=B('Previous_snapshot'))
 field_actions['Reply_field']['runAfter']={'Create_field_record':['Succeeded']}
 repair_actions={'Create_repair_record':sp('PostItem',create_parameters(True)),'Reply_repair':respond('saved',item=F('string',G(B('Create_repair_record'),'ID')),teams=T('legacy_text'))};repair_actions['Reply_repair']['runAfter']={'Create_repair_record':['Succeeded']}
 # Reject malformed or duplicate item IDs before writing legacy text or snapshots.
 row_parts=F('split','item()',S('|'))
 valid_row=F('if',F('equals',F('length',row_parts),'3'),F('and',F('contains',F('createArray',*[S(code)for code,_ in MEASURES]),F('first',row_parts)),F('contains',F('createArray',S('高'),S('中'),S('低')),F('first',F('skip',row_parts,'1'))),F('contains',F('createArray',S('対応済み'),S('未実施'),S('要確認')),F('last',row_parts))),'false')
 field_actions['Invalid_previous_rows']=query(F('if',F('empty',B('Previous_snapshot')),"json('[]')",F('split',B('Previous_snapshot'),S('\n'))),F('not',valid_row),{'Previous_snapshot':['Succeeded']})
 field_actions['Previous_ids']=select(F('if',F('empty',B('Previous_snapshot')),"json('[]')",F('split',B('Previous_snapshot'),S('\n'))),F('first',row_parts),{'Invalid_previous_rows':['Succeeded']})
 field_actions['Action_labels']['runAfter']={'Previous_ids':['Succeeded']}
 headers=['確認できた事実','初動措置　優先度：高','初動措置　優先度：中','初動措置　優先度：低','高優先度の完了状況','ネクストアクション','確認したいこと']
 validity=F('and',F('equals',F('length',B('Invalid_rows')),'0'),F('equals',F('length',F('union',B('Snapshot_ids'),B('Snapshot_ids'))),F('length',B('Snapshot_ids'))),*[F('contains',F('concat',S('\n'),T('current_snapshot')),S('\n'+code+'|'))for code,_ in MEASURES[:13]],*[F('equals',F('length',F('split',T('legacy_text'),S('【'+h+'】'))),'2')for h in headers])
 field_actions={'Snapshot_rows':compose(E(F('split',T('current_snapshot'),S('\n')))),'Invalid_rows':query(B('Snapshot_rows'),F('not',valid_row),{'Snapshot_rows':['Succeeded']}),'Snapshot_ids':select(B('Snapshot_rows'),F('first',row_parts),{'Invalid_rows':['Succeeded']}),'If_snapshot_valid':{'type':'If','expression':E(validity),'actions':field_actions,'else':{'actions':{'Reply_invalid_snapshot':respond('failed',error='INVALID_SNAPSHOT_OR_LEGACY_FORMAT')}},'runAfter':{'Snapshot_ids':['Succeeded']}}}
 duplicate_actions={'Reply_duplicate':respond('duplicate',case=cell('Get_duplicate','case_id'),item=F('string',G(firstrow('Get_duplicate'),'ID')),teams=cell('Get_duplicate','teams_text'))}
 save_actions={'Get_duplicate':getlatest(F('concat',S(m['event_key']+" eq '"),escape(T('event_key')),S("' and "+m['owner_key']+" eq '"),escape(T('owner_key')),S("'"))),'If_duplicate':{'type':'If','expression':E(exists('Get_duplicate')),'actions':duplicate_actions,'else':{'actions':{'If_field':{'type':'If','expression':E(F('equals',T('record_type'),S('field_advice'))),'actions':field_actions,'else':{'actions':repair_actions},'runAfter':{}}}},'runAfter':{'Get_duplicate':['Succeeded']}}}
 load_actions={'Get_case':getlatest(scoped),'Get_loaded_field':getlatest(latestfilter)};load_actions['Get_loaded_field']['runAfter']={'Get_case':['Succeeded']}
 load_actions['If_case_found']={'type':'If','expression':E(exists('Get_case')),'actions':{'Reply_loaded':respond('loaded',previous_status=F('if',exists('Get_loaded_field'),S('found'),S('none')),snapshot=cell('Get_loaded_field','current_snapshot'),facts=cell('Get_loaded_field','facts_history'))},'else':{'actions':{'Reply_not_found':respond('failed',error='CASE_NOT_FOUND_OR_NOT_AUTHORIZED')}},'runAfter':{'Get_loaded_field':['Succeeded']}}
 valid=F('and',F('not',F('empty',T('case_id'))),F('not',F('empty',T('owner_key'))),F('contains',F('createArray',S('load'),S('save')),T('operation')),F('or',F('equals',T('operation'),S('load')),F('and',F('not',F('empty',T('event_key'))),F('not',F('empty',T('legacy_text'))),F('contains',F('createArray',S('field_advice'),S('repair_guidance')),T('record_type')))))
 route={'type':'If','expression':E(F('equals',T('operation'),S('load'))),'actions':load_actions,'else':{'actions':save_actions},'runAfter':{}}
 try_actions={'Validate_input':{'type':'If','expression':E(valid),'actions':{'Route_operation':route},'else':{'actions':{'Reply_invalid':respond('failed',error='INVALID_REQUEST')}},'runAfter':{}}}
 catch=respond('failed',error='SHAREPOINT_OR_FLOW_FAILED');catch['runAfter']={'Try':['Failed','TimedOut']}
 definition={'$schema':'https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#','contentVersion':'1.0.0.0','parameters':{'$authentication':{'type':'SecureObject','defaultValue':{}},'$connections':{'type':'Object','defaultValue':{}}},'triggers':{'manual':{'type':'Request','kind':'Skills','inputs':{'schema':{'type':'object','properties':{k:{'type':'string','title':k,'description':k,'x-ms-content-hint':'TEXT','x-ms-dynamically-added':True}for k in INPUTS},'required':INPUTS}},'runtimeConfiguration':{'concurrency':{'runs':1}}}},'actions':{'Try':{'type':'Scope','actions':try_actions,'runAfter':{}},'Reply_failure':catch},'outputs':{}}
 return {'schemaVersion':'1.0.0.0','properties':{'connectionReferences':{'shared_sharepointonline':{'api':{'name':'shared_sharepointonline'},'connection':{'connectionReferenceLogicalName':c['connection_reference_logical_name']},'runtimeSource':'embedded'}},'definition':definition,'templateName':None}}

def main():
 a=argparse.ArgumentParser();a.add_argument('--config',type=Path,required=True);a.add_argument('--fields',type=Path,required=True);a.add_argument('--output',type=Path,required=True);args=a.parse_args()
 c=json.loads(args.config.read_text());fields=json.loads(args.fields.read_text());fields=fields.get('value',fields)if isinstance(fields,dict)else fields
 out=generate(c,fields);args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print('Generated workflow JSON from verified mappings. Not imported or executed:',args.output)
if __name__=='__main__':main()
