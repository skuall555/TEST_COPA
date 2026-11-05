using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text.Json;
using Microsoft.PowerFx;
using Microsoft.PowerFx.Types;
class Program {
 static void Main(string[] args){
  var input=JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;
  var engine=new RecalcEngine(new PowerFxConfig());var options=new ParserOptions{NumberIsFloat=true,MaxExpressionLength=1000000};
  var groups=new Dictionary<string,string[]>();var scope=RecordType.Empty();
  foreach(var group in input.GetProperty("variables").EnumerateObject()){
   groups[group.Name]=group.Value.EnumerateArray().Select(x=>x.GetString()!).ToArray();var rt=RecordType.Empty();
   foreach(var name in groups[group.Name])rt=rt.Add(name,FormulaType.String);scope=scope.Add(group.Name,rt);
  }
  var sys=RecordType.Empty().Add("Activity",RecordType.Empty().Add("ChannelId",FormulaType.String)).Add("Conversation",RecordType.Empty().Add("Id",FormulaType.String)).Add("User",RecordType.Empty().Add("Id",FormulaType.String));scope=scope.Add("System",sys);
  var checks=new List<object>();
  foreach(var step in input.GetProperty("steps").EnumerateArray()){
   var result=engine.Check(step.GetProperty("expression").GetString()!,scope,options);checks.Add(new{id=step.GetProperty("id").GetString(),success=result.IsSuccess&&result.ReturnType.Equals(FormulaType.String),errors=result.Errors.Select(x=>x.ToString()).ToArray()});
  }
  var runs=new List<object>();
  foreach(var c in input.GetProperty("cases").EnumerateArray()){
   var state=groups.ToDictionary(x=>x.Key,x=>x.Value.ToDictionary(name=>name,name=>(FormulaValue)FormulaValue.New("")));
   foreach(var group in c.GetProperty("state").EnumerateObject())foreach(var val in group.Value.EnumerateObject())state[group.Name][val.Name]=FormulaValue.New(val.Value.GetString()!);
   string SystemString(string k)=>c.GetProperty("system").GetProperty(k).GetString()!;
   var sv=FormulaValue.NewRecordFromFields(new NamedValue("Activity",FormulaValue.NewRecordFromFields(new NamedValue("ChannelId",FormulaValue.New(SystemString("channel"))))),new NamedValue("Conversation",FormulaValue.NewRecordFromFields(new NamedValue("Id",FormulaValue.New(SystemString("conversation"))))),new NamedValue("User",FormulaValue.NewRecordFromFields(new NamedValue("Id",FormulaValue.New(SystemString("user"))))));
   RecordValue Context()=>FormulaValue.NewRecordFromFields(state.Select(x=>new NamedValue(x.Key,FormulaValue.NewRecordFromFields(x.Value.Select(v=>new NamedValue(v.Key,v.Value))))).Append(new NamedValue("System",sv)));
   var errors=new List<string>();
   foreach(var step in input.GetProperty("steps").EnumerateArray()){
    var parts=step.GetProperty("variable").GetString()!.Split('.',2);
    try{state[parts[0]][parts[1]]=engine.Eval(step.GetProperty("expression").GetString()!,Context(),options);}catch(Exception e){errors.Add(e.Message);}
   }
   string output="";
   try{output=(engine.Eval(input.GetProperty("display").GetString()!,Context(),options)as StringValue)?.Value??"ERROR";}catch(Exception e){errors.Add(e.Message);}
   bool success=errors.Count==0&&c.GetProperty("contains").EnumerateArray().All(x=>output.Contains(x.GetString()!))&&c.GetProperty("notContains").EnumerateArray().All(x=>!output.Contains(x.GetString()!));
   if(c.TryGetProperty("equals",out var expected))success&=output==expected.GetString();
   if(c.GetProperty("system").GetProperty("channel").GetString()=="msteams")success&=output.IndexOf("【②")<output.IndexOf("【③")&&output.IndexOf("【③")<output.IndexOf("【④");
   runs.Add(new{name=c.GetProperty("name").GetString(),success,output,errors,legacy=(state["Topic"]["優先度判定結果"]as StringValue)?.Value});
  }
  Console.WriteLine(JsonSerializer.Serialize(new{package="Microsoft.PowerFx.Interpreter 1.8.1",scope="Native expression checks and execution only; no Copilot Studio/Teams/SharePoint tenant",checks,runs},new JsonSerializerOptions{WriteIndented=true}));
 }
}
