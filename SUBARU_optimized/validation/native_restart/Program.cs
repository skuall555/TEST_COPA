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
  var config=new PowerFxConfig();config.EnableRegExFunctions();
  var engine=new RecalcEngine(config);var options=new ParserOptions{MaxExpressionLength=1000000,NumberIsFloat=true};
  var topic=RecordType.Empty();
  foreach(var name in new[]{"初回入力","追加情報履歴","目的回答","目的分野","目的選択入力","対象フォルダ","実行バージョン","優先度ガイド取得結果","優先度判定プロンプト","第1段プロンプト","第2段プロンプト"})topic=topic.Add(name,FormulaType.String);
  topic=topic.Add("目的再試行回数",FormulaType.Number);
  foreach(var name in new[]{"優先度表示原文","優先度表示組立","優先度表示検証","優先度表示区分","優先度判定結果"})topic=topic.Add(name,FormulaType.String);
  topic=topic.Add("優先度様式再試行回数",FormulaType.Number);
  var scope=RecordType.Empty().Add("Topic",topic);var checks=new List<object>();
  foreach(var item in root.GetProperty("expressions").EnumerateArray()){
   var result=engine.Check(item.GetProperty("expression").GetString()!,scope,options);
   var expected=item.GetProperty("expected").GetString()=="Boolean"?FormulaType.Boolean:item.GetProperty("expected").GetString()=="Number"?FormulaType.Number:FormulaType.String;
   checks.Add(new{id=item.GetProperty("id").GetString(),success=result.IsSuccess&&result.ReturnType.Equals(expected),type=result.ReturnType?.ToString(),errors=result.Errors.Select(x=>x.ToString()).ToArray()});
  }
  var runs=new List<object>();
  foreach(var item in root.GetProperty("cases").EnumerateArray()){
   var text=item.GetProperty("input").GetString()!;
   var values=FormulaValue.NewRecordFromFields(new NamedValue("Topic",FormulaValue.NewRecordFromFields(new NamedValue("目的回答",FormulaValue.New(text)))));
   var normalized=engine.Eval(root.GetProperty("normalize").GetString()!,values,options);
   var parsed=engine.Eval(root.GetProperty("choose").GetString()!,FormulaValue.NewRecordFromFields(new NamedValue("Topic",FormulaValue.NewRecordFromFields(new NamedValue("目的選択入力",normalized)))),options);
   runs.Add(new{input=text,success=parsed is StringValue s&&s.Value==item.GetProperty("expected").GetString(),result=parsed.ToObject()});
  }
  var formats=new List<object>();
  foreach(var item in root.GetProperty("formatCases").EnumerateArray()){
   var state=new Dictionary<string,FormulaValue>{{"優先度判定結果",FormulaValue.New(item.GetProperty("text").GetString()!)}};
   foreach(var step in root.GetProperty("formatSteps").EnumerateArray()){
    var context=FormulaValue.NewRecordFromFields(new NamedValue("Topic",FormulaValue.NewRecordFromFields(state.Select(x=>new NamedValue(x.Key,x.Value)))));
    state[step.GetProperty("variable").GetString()!]=engine.Eval(step.GetProperty("expression").GetString()!,context,options);
   }
   bool accepted=state["優先度表示検証"] is StringValue status&&status.Value=="合格";
   bool keepsWaiting=true;
   if(accepted){
    var context=FormulaValue.NewRecordFromFields(new NamedValue("Topic",FormulaValue.NewRecordFromFields(new NamedValue("優先度判定結果",state["優先度表示組立"]))));
    keepsWaiting=engine.Eval(root.GetProperty("completion").GetString()!,context,options) is BooleanValue flag&&flag.Value;
   }
   bool expectedWait=!item.TryGetProperty("expectWait",out var waitValue)||waitValue.GetBoolean();
   formats.Add(new{name=item.GetProperty("name").GetString(),success=accepted==item.GetProperty("accept").GetBoolean()&&keepsWaiting==expectedWait,accepted,keepsWaiting,status=state["優先度表示検証"].ToObject()});
  }
  Console.WriteLine(JsonSerializer.Serialize(new{package="Microsoft.PowerFx.Interpreter 1.8.1",scope="Standalone SDK, not the Studio host; no live model",checks,runs,formats},new JsonSerializerOptions{WriteIndented=true}));
 }
}
