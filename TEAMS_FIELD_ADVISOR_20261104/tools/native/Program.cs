using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text.Json;
using Microsoft.PowerFx;
using Microsoft.PowerFx.Types;
class Program {
 static void Main(string[] args){
  var root=JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;
  var config=new PowerFxConfig();var engine=new RecalcEngine(config);var options=new ParserOptions{MaxExpressionLength=1000000,NumberIsFloat=true};
  var scope=RecordType.Empty();var types=new Dictionary<string,RecordType>();var defaults=new Dictionary<string,Dictionary<string,FormulaValue>>();
  foreach(var group in root.GetProperty("variables").EnumerateObject()){
   var type=RecordType.Empty();var values=new Dictionary<string,FormulaValue>();
   foreach(var v in group.Value.EnumerateObject()){
    var name=v.Name;var kind=v.Value.GetString();FormulaType ft=kind=="Number"?FormulaType.Number:kind=="Boolean"?FormulaType.Boolean:kind=="RecordText"?RecordType.Empty().Add("text",FormulaType.String):FormulaType.String;
    type=type.Add(name,ft);values[name]=kind=="Number"?FormulaValue.New(0d):kind=="Boolean"?FormulaValue.New(false):kind=="RecordText"?FormulaValue.NewRecordFromFields(new NamedValue("text",FormulaValue.New(""))):FormulaValue.New("");
   }
   types[group.Name]=type;defaults[group.Name]=values;scope=scope.Add(group.Name,type);
  }
  var attachmentType=RecordType.Empty().Add("Name",FormulaType.String).Add("ContentType",FormulaType.String).Add("Content",FormulaType.String);
  var activityType=RecordType.Empty().Add("Id",FormulaType.String).Add("Text",FormulaType.String).Add("ChannelId",FormulaType.String).Add("Attachments",attachmentType.ToTable());
  var systemType=RecordType.Empty().Add("Activity",activityType).Add("Conversation",RecordType.Empty().Add("Id",FormulaType.String)).Add("User",RecordType.Empty().Add("Id",FormulaType.String));scope=scope.Add("System",systemType);
  RecordValue SystemValue(JsonElement? attachments=null){
   var rows=attachments.HasValue?attachments.Value.EnumerateArray().Select(x=>FormulaValue.NewRecordFromFields(new NamedValue("Name",FormulaValue.New(x.GetProperty("name").GetString()!)),new NamedValue("ContentType",FormulaValue.New(x.GetProperty("mime").GetString()!)),new NamedValue("Content",FormulaValue.New(x.GetProperty("content").GetString()!)))).ToArray():Array.Empty<RecordValue>();
   return FormulaValue.NewRecordFromFields(new NamedValue("Activity",FormulaValue.NewRecordFromFields(new NamedValue("Id",FormulaValue.New("message-1")),new NamedValue("Text",FormulaValue.New("台所でガス臭い")),new NamedValue("ChannelId",FormulaValue.New("msteams")),new NamedValue("Attachments",FormulaValue.NewTable(attachmentType,rows)))),new NamedValue("Conversation",FormulaValue.NewRecordFromFields(new NamedValue("Id",FormulaValue.New("conversation-1")))),new NamedValue("User",FormulaValue.NewRecordFromFields(new NamedValue("Id",FormulaValue.New("user-1")))));
  }
  var checks=new List<object>();
  foreach(var x in root.GetProperty("expressions").EnumerateArray()){
   var check=engine.Check(x.GetProperty("expression").GetString()!,scope,options);var want=x.GetProperty("expected").GetString();var ft=want=="Number"?FormulaType.Number:want=="Boolean"?FormulaType.Boolean:FormulaType.String;
   checks.Add(new{id=x.GetProperty("id").GetString(),success=check.IsSuccess&&check.ReturnType.Equals(ft),type=check.ReturnType?.ToString(),errors=check.Errors.Select(e=>e.ToString()).ToArray()});
  }
  var renders=new List<object>();
  foreach(var c in root.GetProperty("renderCases").EnumerateArray()){
   var state=defaults.ToDictionary(x=>x.Key,x=>new Dictionary<string,FormulaValue>(x.Value));
   foreach(var group in c.GetProperty("state").EnumerateObject())foreach(var v in group.Value.EnumerateObject())state[group.Name][v.Name]=v.Value.ValueKind==JsonValueKind.Number?FormulaValue.New(v.Value.GetDouble()):FormulaValue.New(v.Value.GetString()!);
   RecordValue Context()=>FormulaValue.NewRecordFromFields(state.Select(x=>new NamedValue(x.Key,FormulaValue.NewRecordFromFields(x.Value.Select(v=>new NamedValue(v.Key,v.Value))))).Append(new NamedValue("System",SystemValue())));
   foreach(var step in root.GetProperty("renderSteps").EnumerateArray()){
    var varName=step.GetProperty("variable").GetString()!.Split('.',2);
    try {state[varName[0]][varName[1]]=engine.Eval(step.GetProperty("expression").GetString()!,Context(),options);}
    catch(Exception ex){state[varName[0]][varName[1]]=FormulaValue.New("EVALUATION_ERROR: "+ex.Message);}
   }
   string Text(string k)=>state["Topic"][k] is StringValue s?s.Value:"ERROR";
   var output=Text("Teams現場回答");var success=c.GetProperty("includes").EnumerateArray().All(x=>output.Contains(x.GetString()!))&&c.GetProperty("excludes").EnumerateArray().All(x=>!output.Contains(x.GetString()!));
   success&=output.IndexOf("【②")<output.IndexOf("【③")&&output.IndexOf("【③")<output.IndexOf("【④");
   renders.Add(new{name=c.GetProperty("name").GetString(),success,comparison=Text("前回比較状態"),snapshot=Text("今回現場スナップショット"),output});
  }
  var images=new List<object>();
  foreach(var c in root.GetProperty("imageCases").EnumerateArray()){
   var ctx=FormulaValue.NewRecordFromFields(new NamedValue("System",SystemValue(c.GetProperty("attachments"))));
   var limit=engine.Eval("Min(CountRows(System.Activity.Attachments), 5)",ctx,options)as NumberValue;var collected=new List<string>();var rejected=0;
   for(int index=1;index<=(int)(limit?.Value??0);index++){
    var vals=defaults.ToDictionary(x=>x.Key,x=>new Dictionary<string,FormulaValue>(x.Value));vals["Topic"]["画像添付番号"]=FormulaValue.New((double)index);
    RecordValue C()=>FormulaValue.NewRecordFromFields(vals.Select(x=>new NamedValue(x.Key,FormulaValue.NewRecordFromFields(x.Value.Select(v=>new NamedValue(v.Key,v.Value))))).Append(new NamedValue("System",SystemValue(c.GetProperty("attachments")))));
    foreach(var key in new[]{"setVariable_attachmentName","setVariable_attachmentContentType","setVariable_attachmentSupported"}){
     var step=root.GetProperty("imageExpressions").GetProperty(key);vals["Topic"][step.GetProperty("variable").GetString()![6..]]=engine.Eval(step.GetProperty("expression").GetString()!,C(),options);
    }
    if(vals["Topic"]["画像形式対応"]is BooleanValue valid&&valid.Value){var content=engine.Eval(root.GetProperty("imageExpressions").GetProperty("imageInput").GetString()!,C(),options)as StringValue;collected.Add(content?.Value??"ERROR");}else rejected++;
   }
   bool success=collected.SequenceEqual(c.GetProperty("expectedInputs").EnumerateArray().Select(x=>x.GetString()!))&&rejected==c.GetProperty("rejected").GetInt32();
   images.Add(new{name=c.GetProperty("name").GetString(),success,inputs=collected,rejected,scope="Attachment selection only; image model not executed"});
  }
  Console.WriteLine(JsonSerializer.Serialize(new{package="Microsoft.PowerFx.Interpreter 1.8.1",scope="Standalone SDK; no tenant/Studio/model/Power Apps execution",checks,renders,images},new JsonSerializerOptions{WriteIndented=true}));
 }
}
