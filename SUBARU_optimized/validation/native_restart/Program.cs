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
  var existingNames=new HashSet<string>(new[]{"初回入力","追加情報履歴","目的回答","目的分野","目的選択入力","対象フォルダ","実行バージョン","優先度ガイド取得結果","優先度判定プロンプト","第1段プロンプト","第2段プロンプト","優先度表示原文","優先度表示組立","優先度表示検証","優先度表示区分","優先度判定結果"});
  foreach(var item in root.GetProperty("stringVariables").EnumerateArray())if(existingNames.Add(item.GetString()!))topic=topic.Add(item.GetString()!,FormulaType.String);
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
   bool placement=true;
   string Get(string key)=>state.TryGetValue(key,out var value)&&value is StringValue str?str.Value:"";
   if(accepted&&item.TryGetProperty("expectBucket",out var bucket)){
    var map=new Dictionary<string,string>{{"high","判定高欄"},{"middle","判定中欄"},{"low","判定低欄"}};
    var label=item.GetProperty("expectLabel").GetString()!;
    placement=map.All(x=>Get(x.Value).Contains(label)==(x.Key==bucket.GetString()));
   }
   if(accepted&&item.TryGetProperty("expectEvacHigh",out var evac)&&evac.GetBoolean())placement&=Get("判定高欄").Contains("避難誘導");
   if(accepted&&item.TryGetProperty("expectCheckPrefix",out var prefix))placement&=Get("判定確認文").StartsWith(prefix.GetString()!);
   bool previousMatches=true;
   if(item.TryGetProperty("comparePrevious",out var comparePrevious)&&comparePrevious.GetBoolean()){
    var previousState=new Dictionary<string,FormulaValue>{{"優先度判定結果",FormulaValue.New(item.GetProperty("text").GetString()!)}};
    foreach(var step in root.GetProperty("previousFormatSteps").EnumerateArray()){
     var context=FormulaValue.NewRecordFromFields(new NamedValue("Topic",FormulaValue.NewRecordFromFields(previousState.Select(x=>new NamedValue(x.Key,x.Value)))));
     previousState[step.GetProperty("variable").GetString()!]=engine.Eval(step.GetProperty("expression").GetString()!,context,options);
    }
    bool previousAccepted=previousState["優先度表示検証"] is StringValue previousStatus&&previousStatus.Value=="合格";
    previousMatches=previousAccepted==accepted&&(!accepted||((StringValue)previousState["優先度表示組立"]).Value==Get("優先度表示組立"));
   }
   formats.Add(new{name=item.GetProperty("name").GetString(),success=accepted==item.GetProperty("accept").GetBoolean()&&keepsWaiting==expectedWait&&placement&&previousMatches,accepted,keepsWaiting,placement,previousMatches,status=state["優先度表示検証"].ToObject()});
  }
  var fieldPromptItems=new List<object>();bool fieldPromptSuccess=true;
  foreach(var item in root.GetProperty("fieldPrompts").EnumerateArray()){
   var guide=engine.Eval(item.GetProperty("guide").GetString()!,options:options)as StringValue;
   var context=FormulaValue.NewRecordFromFields(new NamedValue("Topic",FormulaValue.NewRecordFromFields(new NamedValue("優先度ガイド取得結果",guide!),new NamedValue("初回入力",FormulaValue.New("浴室で臭気あり")),new NamedValue("追加情報履歴",FormulaValue.New("")))));
   var prompt=engine.Eval(item.GetProperty("prompt").GetString()!,context,options)as StringValue;
   var concept=root.GetProperty("fieldConceptSource").GetString()!;
   int copies=prompt==null?0:(prompt.Value.Length-prompt.Value.Replace(concept,"").Length)/concept.Length;
   bool isCurrent=item.GetProperty("name").GetString()=="current";
   bool success=prompt!=null&&(!isCurrent||copies==1);
   fieldPromptSuccess&=success;
   fieldPromptItems.Add(new{name=item.GetProperty("name").GetString(),success,characters=prompt?.Value.Length,conceptCopies=copies,conceptHeadingCopies=prompt==null?0:prompt.Value.Split("# 現場調査・遮断・供給支障の追加概念",StringSplitOptions.None).Length-1});
  }
  var fieldPrompts=new{success=fieldPromptSuccess,items=fieldPromptItems,scope="Evaluated prompt assembly; character counts are not model tokens or latency"};

  var imageState=new Dictionary<string,FormulaValue>{{"画像同時テキスト",FormulaValue.New("写真です")}};
  foreach(var step in root.GetProperty("imageSteps").EnumerateArray()){
   var context=FormulaValue.NewRecordFromFields(new NamedValue("Topic",FormulaValue.NewRecordFromFields(imageState.Select(x=>new NamedValue(x.Key,x.Value)))));
   imageState[step.GetProperty("variable").GetString()!]=engine.Eval(step.GetProperty("expression").GetString()!,context,options);
  }
  var imageContext=FormulaValue.NewRecordFromFields(new NamedValue("Topic",FormulaValue.NewRecordFromFields(imageState.Select(x=>new NamedValue(x.Key,x.Value)))));
  var firstPrompt=engine.Eval(root.GetProperty("imageContext").GetString()!,imageContext,options) as StringValue;
  var secondPrompt=imageState["第2段プロンプト"] as StringValue;
  var featureResults=root.GetProperty("featureSources").EnumerateArray().Select(x=>new{first=firstPrompt?.Value.Contains(x.GetString()!)==true,second=secondPrompt?.Value.Contains(x.GetString()!)==true}).ToArray();
  var imageFeatures=new{success=featureResults.All(x=>x.first&&x.second),count=featureResults.Length,items=featureResults,scope="Prompt assembly only; no image or AI model executed"};
  Console.WriteLine(JsonSerializer.Serialize(new{package="Microsoft.PowerFx.Interpreter 1.8.1",scope="Standalone SDK, not the Studio host; no live model",checks,runs,formats,imageFeatures,fieldPrompts},new JsonSerializerOptions{WriteIndented=true}));
 }
}
