using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text.Json;
using Microsoft.PowerFx;
using Microsoft.PowerFx.Types;

class Jump : Exception { public string Target; public Jump(string target) { Target = target; } }
class Done : Exception { }
class Program {
    static void Main(string[] args) {
        var data = JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;
        var engine = new RecalcEngine(new PowerFxConfig());
        var options = new ParserOptions { NumberIsFloat = true, MaxExpressionLength = 1000000 };
        FormulaType TypeOf(string name) => name switch {
            "DateTime" => FormulaType.DateTime, "Number" => FormulaType.Number,
            "Boolean" => FormulaType.Boolean, "Facts" => RecordType.Empty().Add("text", FormulaType.String),
            _ => FormulaType.String
        };
        var types = data.GetProperty("variables").EnumerateObject().ToDictionary(g => g.Name,
            g => g.Value.EnumerateObject().ToDictionary(v => v.Name, v => TypeOf(v.Value.GetString()!)));
        var groupTypes = types.ToDictionary(g => g.Key, g => g.Value.Aggregate(RecordType.Empty(), (rt, v) => rt.Add(v.Key, v.Value)));
        var attachmentType = RecordType.Empty().Add("Name", FormulaType.String).Add("ContentType", FormulaType.String).Add("Content", FormulaType.String);
        var systemType = RecordType.Empty()
            .Add("Activity", RecordType.Empty().Add("Text", FormulaType.String).Add("ChannelId", FormulaType.String).Add("Attachments", attachmentType.ToTable()))
            .Add("Conversation", RecordType.Empty().Add("Id", FormulaType.String))
            .Add("User", RecordType.Empty().Add("Id", FormulaType.String));
        var scope = groupTypes.Aggregate(RecordType.Empty(), (rt, g) => rt.Add(g.Key, g.Value)).Add("System", systemType);
        var checks = new List<object>();
        foreach (var item in data.GetProperty("checks").EnumerateArray()) {
            var result = engine.Check(item.GetProperty("expression").GetString()!, scope, options);
            checks.Add(new { id = item.GetProperty("id").GetString(), success = result.IsSuccess && result.ReturnType.Equals(TypeOf(item.GetProperty("type").GetString()!)), errors = result.Errors.Select(e => e.ToString()).ToArray() });
        }
        FormulaValue Default(FormulaType type) {
            if (type.Equals(FormulaType.String)) return FormulaValue.New("");
            if (type.Equals(FormulaType.Number)) return FormulaValue.New(0d);
            if (type.Equals(FormulaType.Boolean)) return FormulaValue.New(false);
            if (type.Equals(FormulaType.DateTime)) return FormulaValue.NewBlank(FormulaType.DateTime);
            return FormulaValue.NewRecordFromFields(new NamedValue("text", FormulaValue.New("")));
        }
        var seed = types["Global"].ToDictionary(v => v.Key, v => Default(v.Value));
        var runs = new List<object>();
        var compared = new[] { "写真措置済みテキスト", "写真要確認テキスト", "緊急保安追加情報履歴", "緊急保安画像受付中" };
        foreach (var c in data.GetProperty("cases").EnumerateArray()) {
            Dictionary<string, FormulaValue> Run(JsonElement program, bool patched, out int searchCalls, out int visionCalls, out int judgeCalls, out string[] messages, out string[] errors, out string visionInput, out string judgeInput) {
                var state = types.ToDictionary(g => g.Key, g => g.Value.ToDictionary(v => v.Key, v => Default(v.Value)));
                state["Global"] = new Dictionary<string, FormulaValue>(seed);
                if (c.TryGetProperty("clearCache", out var clear) && clear.GetBoolean()) {
                    foreach (var key in state["Global"].Keys.Where(k => k.StartsWith("画像要領キャッシュ")).ToArray()) state["Global"][key] = Default(types["Global"][key]);
                }
                if (c.TryGetProperty("ageSeconds", out var age)) state["Global"]["画像要領キャッシュ取得時刻"] = FormulaValue.New(DateTime.UtcNow.AddSeconds(-age.GetDouble()));
                if (c.TryGetProperty("oldVersion", out var old)) state["Global"]["画像要領キャッシュ版"] = FormulaValue.New(old.GetString()!);
                var sys = c.GetProperty("system");
                var attachment = FormulaValue.NewRecordFromFields(new NamedValue("Name", FormulaValue.New("現場写真.jpg")), new NamedValue("ContentType", FormulaValue.New(c.TryGetProperty("mime", out var mime) ? mime.GetString()! : "image/jpeg")), new NamedValue("Content", FormulaValue.New("scripted-image-bytes")));
                var system = FormulaValue.NewRecordFromFields(
                    new NamedValue("Activity", FormulaValue.NewRecordFromFields(new NamedValue("Text", FormulaValue.New("写真です")), new NamedValue("ChannelId", FormulaValue.New(sys.GetProperty("channel").GetString()!)), new NamedValue("Attachments", FormulaValue.NewTable(attachmentType, attachment)))),
                    new NamedValue("Conversation", FormulaValue.NewRecordFromFields(new NamedValue("Id", FormulaValue.New(sys.GetProperty("conversation").GetString()!)))),
                    new NamedValue("User", FormulaValue.NewRecordFromFields(new NamedValue("Id", FormulaValue.New(sys.GetProperty("user").GetString()!)))));
                RecordValue Context() => FormulaValue.NewRecordFromFields(state.Select(g => new NamedValue(g.Key, FormulaValue.NewRecordFromFields(g.Value.Select(v => new NamedValue(v.Key, v.Value))))).Append(new NamedValue("System", system)));
                FormulaValue Eval(string expression) {
                    var value = engine.Eval(expression.StartsWith("=") ? expression[1..] : expression, Context(), options);
                    if (value is ErrorValue error) throw new Exception(string.Join(";", error.Errors.Select(e => e.Message)));
                    return value;
                }
                void Set(string variable, FormulaValue value) { var parts = variable.Split('.', 2); state[parts[0]][parts[1]] = value; }
                var msgs = new List<string>(); var err = new List<string>(); int searches = 0, visions = 0, judges = 0, steps = 0;
                string vi = "", ji = "";
                void RunList(JsonElement array) {
                    var list = array.EnumerateArray().ToArray();
                    var positions = list.Select((n, i) => (id: n.GetProperty("id").GetString()!, i)).ToDictionary(x => x.id, x => x.i);
                    int pc = 0;
                    while (pc < list.Length) { try { RunNode(list[pc]); pc++; } catch (Jump jump) { if (!positions.TryGetValue(jump.Target, out pc)) throw; } }
                }
                void RunNode(JsonElement node) {
                    if (++steps > 800) throw new Exception("Unexpected execution loop");
                    var kind = node.GetProperty("kind").GetString(); var id = node.GetProperty("id").GetString()!;
                    if (kind == "SetVariable") {
                        var value = Eval(node.GetProperty("value").GetString()!);
                        if (id == "setVariable_imageSpeed_cacheEnabled" && c.TryGetProperty("cacheEnabled", out var enabled)) value = FormulaValue.New(enabled.GetBoolean());
                        Set(node.GetProperty("variable").GetString()!, value);
                    } else if (kind == "ConditionGroup") {
                        bool matched = false;
                        foreach (var condition in node.GetProperty("conditions").EnumerateArray()) if ((Eval(condition.GetProperty("condition").GetString()!) as BooleanValue)?.Value == true) { matched = true; RunList(condition.GetProperty("actions")); break; }
                        if (!matched && node.TryGetProperty("elseActions", out var otherwise)) RunList(otherwise);
                    } else if (kind == "InvokeAIBuilderModelAction") {
                        visions++; vi = ((StringValue)Eval(node.GetProperty("input").GetProperty("binding").GetProperty("ContextText").GetString()!)).Value;
                        Set("Topic.画像分析出力", FormulaValue.NewRecordFromFields(new NamedValue("text", FormulaValue.New(c.GetProperty("facts").GetString()!))));
                    } else if (kind == "SearchAndSummarizeContent") {
                        searches++; Set(node.GetProperty("variable").GetString()!, FormulaValue.New(c.GetProperty("guide").GetString()!));
                    } else if (kind == "AnswerQuestionWithAI") {
                        judges++; ji = ((StringValue)Eval(node.GetProperty("userInput").GetString()!)).Value;
                        Set(node.GetProperty("variable").GetString()!, FormulaValue.New(c.GetProperty("judgment").GetString()!));
                    } else if (kind == "SendActivity") msgs.Add(id);
                    else if (kind == "EndDialog") throw new Done();
                    else if (kind == "GotoAction") throw new Jump(node.GetProperty("actionId").GetString()!);
                    else throw new Exception("Unhandled node " + kind);
                }
                try { RunList(program.GetProperty("beginDialog").GetProperty("actions")); } catch (Done) { } catch (Exception ex) { err.Add(ex.ToString()); }
                searchCalls = searches; visionCalls = visions; judgeCalls = judges; messages = msgs.ToArray(); errors = err.ToArray(); visionInput = vi; judgeInput = ji;
                return state["Global"];
            }
            var legacy = Run(data.GetProperty("baseline"), false, out _, out _, out _, out var legacyMessages, out var legacyErrors, out var legacyVision, out var legacyJudge);
            var actual = Run(data.GetProperty("patched"), true, out var searchCalls, out var visionCalls, out var judgeCalls, out var messages, out var errors, out var visionInput, out var judgeInput);
            bool same = compared.All(key => Equals(legacy[key].ToObject(), actual[key].ToObject())) && legacyMessages.SequenceEqual(messages) && legacyVision == visionInput && legacyJudge == judgeInput;
            bool success = same && errors.Length == 0 && legacyErrors.Length == 0 && searchCalls == c.GetProperty("expectedSearch").GetInt32() && visionCalls == c.GetProperty("expectedVision").GetInt32() && judgeCalls == c.GetProperty("expectedJudge").GetInt32();
            var cachePresent = !string.IsNullOrEmpty((actual["画像要領キャッシュ本文"] as StringValue)?.Value);
            if (c.TryGetProperty("expectedCache", out var cacheExpected)) success &= cachePresent == cacheExpected.GetBoolean();
            runs.Add(new { name = c.GetProperty("name").GetString(), success, originalInputsAndResultsIdentical = same, searchCalls, visionCalls, judgeCalls, cachePresent, diagnostic = (actual["画像分析最新診断"] as StringValue)?.Value, errors, legacyErrors });
            if (c.TryGetProperty("saveSeed", out var save) && save.GetBoolean()) seed = actual;
        }
        Console.WriteLine(JsonSerializer.Serialize(new { scope = "Native Power Fx and actual YAML control flow with scripted external results; no image-quality or live-latency test", package = "Microsoft.PowerFx.Interpreter 1.8.1", checks, runs }, new JsonSerializerOptions { WriteIndented = true }));
    }
}
