using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text.Json;
using Microsoft.PowerFx;
using Microsoft.PowerFx.Types;
class Jump:Exception{public string Target;public Jump(string target){Target=target;}}
class Program{
 static void Main(string[]args){
  var input=JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;var engine=new RecalcEngine(new PowerFxConfig());var options=new ParserOptions{NumberIsFloat=true,MaxExpressionLength=1000000};
  var names=input.GetProperty("variables").EnumerateArray().Select(x=>x.GetString()!).ToArray();var type=RecordType.Empty();
  foreach(var name in names)type=type.Add(name,name=="優先度様式再試行回数"?FormulaType.Number:FormulaType.String);
  var scope=RecordType.Empty().Add("Topic",type);var result=new List<object>();var routes=new List<object>();
  Dictionary<string,FormulaValue> NewState()=>names.ToDictionary(n=>n,n=>n=="優先度様式再試行回数"?(FormulaValue)FormulaValue.New(0d):FormulaValue.New(""));
  foreach(var c in input.GetProperty("routes").EnumerateArray()){
   var values=NewState();values["目的分野"]=FormulaValue.New(c.GetProperty("purpose").GetString()!);values["初回入力"]=FormulaValue.New(c.GetProperty("text").GetString()!);var context=FormulaValue.NewRecordFromFields(new NamedValue("Topic",FormulaValue.NewRecordFromFields(values.Select(v=>new NamedValue(v.Key,v.Value)))));
   var check=engine.Check(input.GetProperty("routeGuard").GetString()!,scope,options);bool actual=(engine.Eval(input.GetProperty("routeGuard").GetString()!,context,options)as BooleanValue)?.Value??false;
   routes.Add(new{name=c.GetProperty("name").GetString(),success=check.IsSuccess&&actual==c.GetProperty("expected").GetBoolean(),actual});
  }
  foreach(var c in input.GetProperty("cases").EnumerateArray()){
   var values=NewState();var outputs=c.GetProperty("outputs").EnumerateArray().Select(x=>x.GetString()!).ToArray();var nodes=input.GetProperty("program").EnumerateArray().ToArray();var addresses=nodes.Select((n,i)=>(n.GetProperty("id").GetString()!,i)).ToDictionary(x=>x.Item1,x=>x.i);var calls=0;var errors=new List<string>();var steps=0;
   RecordValue Context()=>FormulaValue.NewRecordFromFields(new NamedValue("Topic",FormulaValue.NewRecordFromFields(values.Select(v=>new NamedValue(v.Key,v.Value)))));
   FormulaValue Eval(string expr)=>engine.Eval(expr.StartsWith("=")?expr[1..]:expr,Context(),options);
   void Run(JsonElement n){
    if(++steps>1200)throw new Exception("Execution bound exceeded");var kind=n.GetProperty("kind").GetString();
    if(kind=="SetVariable"){var key=n.GetProperty("variable").GetString()![6..];values[key]=Eval(n.GetProperty("value").GetString()!);}
    else if(kind=="AnswerQuestionWithAI"){values["優先度判定結果"]=FormulaValue.New(outputs[Math.Min(calls,outputs.Length-1)]);calls++;}
    else if(kind=="GotoAction")throw new Jump(n.GetProperty("actionId").GetString()!);
    else if(kind=="ConditionGroup"){
     bool matched=false;
     foreach(var cond in n.GetProperty("conditions").EnumerateArray())if((Eval(cond.GetProperty("condition").GetString()!)as BooleanValue)?.Value==true){matched=true;foreach(var action in cond.GetProperty("actions").EnumerateArray())Run(action);break;}
     if(!matched&&n.TryGetProperty("elseActions",out var otherwise))foreach(var action in otherwise.EnumerateArray())Run(action);
    }else throw new Exception("Unsupported test node "+kind);
   }
   var pc=0;
   while(pc<nodes.Length){try{Run(nodes[pc]);pc++;}catch(Jump j){if(!addresses.TryGetValue(j.Target,out pc)){errors.Add("Unknown target "+j.Target);break;}}catch(Exception e){errors.Add(e.Message);break;}}
   bool accepted=false;try{accepted=(Eval(input.GetProperty("saveGuard").GetString()!)as BooleanValue)?.Value??false;}catch(Exception e){errors.Add(e.Message);}
   bool success=errors.Count==0&&calls==c.GetProperty("expectedCalls").GetInt32()&&accepted==c.GetProperty("expectedAccept").GetBoolean();
   result.Add(new{name=c.GetProperty("name").GetString(),success,modelCalls=calls,wouldInvokeSave=accepted,validation=(values["優先度表示検証"]as StringValue)?.Value,retry=(values["優先度様式再試行回数"]as NumberValue)?.Value,steps,errors});
  }
  Console.WriteLine(JsonSerializer.Serialize(new{scope="Actual Power Fx parser and YAML retry control flow with scripted model outputs; no tenant/model/SharePoint execution",package="Microsoft.PowerFx.Interpreter 1.8.1",routes,cases=result},new JsonSerializerOptions{WriteIndented=true}));
 }
}
