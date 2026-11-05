using System;using System.IO;using System.Linq;using System.Collections.Generic;using System.Text.Json;using Microsoft.PowerFx;using Microsoft.PowerFx.Types;
class Program{static void Main(string[]args){
 var data=JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;var engine=new RecalcEngine(new PowerFxConfig());var options=new ParserOptions{NumberIsFloat=true};
 var type=RecordType.Empty().Add("初回入力",FormulaType.String).Add("入口入力小文字",FormulaType.String).Add("目的再試行回数",FormulaType.Number);
 var scope=RecordType.Empty().Add("Topic",type);var results=new List<object>();
 foreach(var c in data.GetProperty("cases").EnumerateArray()){
  var original=c.GetProperty("input").GetString()!;var count=c.GetProperty("retry").GetDouble();var text="";
  RecordValue Context()=>FormulaValue.NewRecordFromFields(new NamedValue("Topic",FormulaValue.NewRecordFromFields(new NamedValue("初回入力",FormulaValue.New(original)),new NamedValue("入口入力小文字",FormulaValue.New(text)),new NamedValue("目的再試行回数",FormulaValue.New(count)))));
  text=(engine.Eval(data.GetProperty("normalize").GetString()!,Context(),options)as StringValue)?.Value??"";
  var check=engine.Check(data.GetProperty("guard").GetString()!,scope,options);var actual=(engine.Eval(data.GetProperty("guard").GetString()!,Context(),options)as BooleanValue)?.Value??false;
  results.Add(new{input=original,success=check.IsSuccess&&check.ReturnType.Equals(FormulaType.Boolean)&&actual==c.GetProperty("field").GetBoolean(),directFieldRoute=actual,retry=count,errors=check.Errors.Select(x=>x.ToString()).ToArray()});
 }
 Console.WriteLine(JsonSerializer.Serialize(new{scope="Actual Power Fx guard evaluation; no live model, agent routing host, Teams or SharePoint execution",package="Microsoft.PowerFx.Interpreter 1.8.1",cases=results},new JsonSerializerOptions{WriteIndented=true}));
}}
