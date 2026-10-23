using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text.Json;
using Microsoft.PowerFx;
using Microsoft.PowerFx.Types;
record Node(string id,string target,string expr,string kind);
class Jump : Exception { public string Target;public Jump(string target){Target=target;} }
class Program {
 static ParserOptions Options()=>new ParserOptions{MaxExpressionLength=1000000};
 static void Main(string[] args){
  var engine=new RecalcEngine();var root=JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;
  var nodes=JsonSerializer.Deserialize<Node[]>((root.ValueKind==JsonValueKind.Array?root:root.GetProperty("expressions")).GetRawText())!;
  var types=new Dictionary<string,FormulaType>{{"Topic.初回入力",FormulaType.String},{"Topic.追加情報履歴",FormulaType.String},{"Topic.優先度判定結果",FormulaType.String},{"Topic.優先度追加回答",FormulaType.String}};
  RecordType Parameters(){
   var record=RecordType.Empty();
   foreach(var group in types.GroupBy(x=>x.Key.Split('.')[0])){
    var sub=RecordType.Empty();foreach(var v in group)sub=sub.Add(v.Key.Split('.')[1],v.Value);
    record=record.Add(group.Key,sub);
   }
   return record;
  }
  for(int pass=0;pass<15;pass++){
   int added=0;foreach(var n in nodes.Where(x=>x.target!="")){
    if(types.ContainsKey(n.target))continue;var c=engine.Check(n.expr,Parameters(),Options());
    if(c.IsSuccess){types.Add(n.target,c.ReturnType);added++;}
   }
   if(added==0)break;
  }
  var report=new List<object>();
  foreach(var n in nodes){
   var c=engine.Check(n.expr,Parameters(),Options());
   FormulaType expected=n.kind=="Condition"?FormulaType.Boolean:types.GetValueOrDefault(n.target);
   bool match=c.IsSuccess&&c.ReturnType.Equals(expected);
   report.Add(new{id=n.id,target=n.target,success=match,type=c.ReturnType?.ToString(),expected=expected?.ToString(),errors=c.Errors.Select(x=>x.ToString()).ToArray()});
  }
  var runs=new List<object>();
  if(root.ValueKind==JsonValueKind.Object&&root.TryGetProperty("cases",out var cases)){
   foreach(var test in cases.EnumerateArray()){
    string name=test.GetProperty("name").GetString()!;
    var values=new Dictionary<string,FormulaValue>{{"Topic.初回入力",FormulaValue.New(test.GetProperty("report").GetString()!)},{"Topic.追加情報履歴",FormulaValue.New("")}};
    int calls=0;var responses=test.GetProperty("repair").EnumerateArray().ToArray();
    RecordValue Inputs(){
     return FormulaValue.NewRecordFromFields(values.GroupBy(x=>x.Key.Split('.')[0]).Select(g=>new NamedValue(g.Key,FormulaValue.NewRecordFromFields(g.Select(x=>new NamedValue(x.Key.Split('.')[1],x.Value)).ToArray()))).ToArray());
    }
    FormulaValue Eval(string s){
     var value=engine.Eval(s.StartsWith("=")?s.Substring(1):s,Inputs(),Options());
     if(value is ErrorValue err)throw new Exception("Power Fx evaluation failed: "+err.ToString());
     return value;
    }
    void Actions(JsonElement actions){
     foreach(var n in actions.EnumerateArray()){
      switch(n.GetProperty("kind").GetString()){
       case "SetVariable":values[n.GetProperty("variable").GetString()!]=Eval(n.GetProperty("value").GetString()!);break;
       case "ConditionGroup":
        bool selected=false;
        foreach(var branch in n.GetProperty("conditions").EnumerateArray()){
         if(Convert.ToBoolean(Eval(branch.GetProperty("condition").GetString()!).ToObject())){Actions(branch.GetProperty("actions"));selected=true;break;}
        }
        if(!selected&&n.TryGetProperty("elseActions",out var otherwise))Actions(otherwise);break;
       case "AnswerQuestionWithAI":
        if(n.GetProperty("autoSend").GetBoolean())throw new Exception("Unexpected auto-send");
        values[n.GetProperty("variable").GetString()!]=FormulaValue.New(calls<responses.Length&&responses[calls].ValueKind!=JsonValueKind.Null?responses[calls].GetString()!:"");calls++;break;
       case "GotoAction":throw new Jump(n.GetProperty("actionId").GetString()!);
       default:throw new Exception("Unsupported test action");
      }
     }
    }
    try{
     Actions(root.GetProperty("seeds"));
     values["Topic.優先度判定結果"]=test.GetProperty("raw").ValueKind==JsonValueKind.Null?FormulaValue.NewBlank(FormulaType.String):FormulaValue.New(test.GetProperty("raw").GetString()!);
     var pipeline=root.GetProperty("pipeline").EnumerateArray().ToArray();int start=0,turn=0;
     while(true){
      if(turn++>2)throw new Exception("Unbounded repair");
      try{Actions(JsonSerializer.SerializeToElement(pipeline.Skip(start).ToArray()));break;}
      catch(Jump j){start=Array.FindIndex(pipeline,x=>x.GetProperty("id").GetString()==j.Target);if(start<0)throw;}
     }
     foreach(var check in test.GetProperty("expect").EnumerateArray()){
      var value=values[check.GetProperty("variable").GetString()!].ToObject();string text=value?.ToString()??"";
      if(check.TryGetProperty("contains",out var contains)&&!text.Contains(contains.GetString()!))throw new Exception("Expected text missing: "+contains);
      if(check.TryGetProperty("notContains",out var excluded)&&text.Contains(excluded.GetString()!))throw new Exception("Excluded text found: "+excluded);
      if(check.TryGetProperty("equals",out var equals)&&JsonSerializer.Serialize(value)!=equals.GetRawText())throw new Exception("Value mismatch: "+check);
     }
     if(calls!=test.GetProperty("repairCalls").GetInt32())throw new Exception("Repair call count mismatch");
     runs.Add(new{name,success=true,repairCalls=calls});
    }catch(Exception ex){runs.Add(new{name,success=false,error=ex.Message,repairCalls=calls});}
   }
  }
  Console.WriteLine(JsonSerializer.Serialize(new{engine=typeof(RecalcEngine).Assembly.FullName,package="Microsoft.PowerFx.Interpreter 1.8.1",scope="Standalone SDK; not Copilot Studio's host or model",inferred=types.ToDictionary(x=>x.Key,x=>x.Value.ToString()),results=report,execution=runs},new JsonSerializerOptions{WriteIndented=true}));
 }
}
