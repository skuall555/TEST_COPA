"""Create deployable copies only when two real Studio AI model IDs are supplied.
Does not create prompts, call a model, or modify the main release YAML.
"""
import argparse,uuid
from pathlib import Path
from restart_support import edit,setv
from restart_build import R,FILES

def bind(entry,field,purpose_model_id,priority_model_id):
    ids=[str(uuid.UUID(x))for x in (purpose_model_id,priority_model_id)]
    if ids[0]==ids[1]or any(x=='00000000-0000-0000-0000-000000000000'for x in ids):raise ValueError('Use two distinct, real text-prompt AI model IDs from this Studio environment')
    def transform(model_id,response_var,target_var,copy_id):
        def action(n):
            return [{'kind':'InvokeAIBuilderModelAction','id':n['id'],'input':{'binding':{'ContextText':n['userInput']}},'output':{'binding':{'predictionOutput':response_var}},'aIModelId':model_id},setv(copy_id,target_var,'='+response_var+'.text')]
        return action
    entry.write_text(edit(entry,{'answer_inferPurposeFromText':transform(ids[0],'Topic.目的判定応答','Topic.目的分野','setVariable_copyPurposePromptText')}))
    field.write_text(edit(field,{'answer_priority':transform(ids[1],'Topic.優先度判定応答','Topic.優先度判定結果','setVariable_copyPriorityPromptText')}))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--purpose-model-id',required=True)
    ap.add_argument('--priority-model-id',required=True)
    ap.add_argument('--output-dir',type=Path,required=True)
    a=ap.parse_args();out=a.output_dir.resolve()
    if out==R.resolve():raise ValueError('Choose a separate output directory; keep release YAML unchanged')
    out.mkdir(parents=True,exist_ok=True)
    for name in [FILES[0],FILES[1]]:(out/name).write_bytes((R/name).read_bytes())
    bind(out/FILES[0],out/FILES[1],a.purpose_model_id,a.priority_model_id)
    print('Created bound entry and field YAML in',out)
    print('No Studio import, prompt creation, connection test, model run or publication was performed')
if __name__=='__main__':main()
