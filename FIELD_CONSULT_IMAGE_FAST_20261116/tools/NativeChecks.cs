using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text.Json;
using Microsoft.PowerFx;
using Microsoft.PowerFx.Types;

class NativeChecks
{
    static FormulaType TypeOf(string name) => name switch
    {
        "Boolean" => FormulaType.Boolean,
        "Number" => FormulaType.Number,
        "DateTime" => FormulaType.DateTime,
        _ => FormulaType.String,
    };

    static RecordType Record(JsonElement element)
    {
        var record = RecordType.Empty();
        foreach (var item in element.EnumerateObject()) record = record.Add(item.Name, TypeOf(item.Value.GetString()!));
        return record;
    }

    static FormulaValue JsonValue(JsonElement value) => value.ValueKind switch
    {
        JsonValueKind.True => FormulaValue.New(true),
        JsonValueKind.False => FormulaValue.New(false),
        JsonValueKind.Number => FormulaValue.New(value.GetDouble()),
        _ => FormulaValue.New(value.GetString()!),
    };

    static void Main(string[] args)
    {
        var root = JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;
        var config = new PowerFxConfig();
        config.EnableRegExFunctions();
        var engine = new RecalcEngine(config);
        var options = new ParserOptions { MaxExpressionLength = 1_000_000, NumberIsFloat = true };

        var conversation = RecordType.Empty().Add("Id", FormulaType.String);
        var user = RecordType.Empty().Add("Id", FormulaType.String);
        var attachment = RecordType.Empty()
            .Add("Name", FormulaType.String)
            .Add("ContentType", FormulaType.String)
            .Add("Content", FormulaType.String);
        var activity = RecordType.Empty()
            .Add("ChannelId", FormulaType.String)
            .Add("Text", FormulaType.String)
            .Add("Attachments", attachment.ToTable());
        var system = RecordType.Empty().Add("Conversation", conversation).Add("User", user).Add("Activity", activity);
        var scope = RecordType.Empty()
            .Add("Topic", Record(root.GetProperty("topicTypes")))
            .Add("Global", Record(root.GetProperty("globalTypes")))
            .Add("System", system);

        var checks = new List<object>();
        foreach (var item in root.GetProperty("expressions").EnumerateArray())
        {
            var result = engine.Check(item.GetProperty("expression").GetString()!, scope, options);
            var expected = TypeOf(item.GetProperty("expected").GetString()!);
            checks.Add(new
            {
                id = item.GetProperty("id").GetString(),
                success = result.IsSuccess && result.ReturnType.Equals(expected),
                type = result.ReturnType?.ToString(),
                errors = result.Errors.Select(error => error.ToString()).ToArray(),
            });
        }

        var semantics = new List<object>();
        foreach (var item in root.GetProperty("semanticCases").EnumerateArray())
        {
            var fields = item.GetProperty("topic").EnumerateObject()
                .Select(pair => new NamedValue(pair.Name, JsonValue(pair.Value)));
            var contextFields = new List<NamedValue>
            {
                new NamedValue("Topic", FormulaValue.NewRecordFromFields(fields)),
            };
            if (item.TryGetProperty("global", out var globalElement))
            {
                var globalFields = globalElement.EnumerateObject()
                    .Select(pair => new NamedValue(pair.Name, JsonValue(pair.Value)));
                contextFields.Add(new NamedValue("Global", FormulaValue.NewRecordFromFields(globalFields)));
            }
            var context = FormulaValue.NewRecordFromFields(contextFields);
            var result = engine.Eval(item.GetProperty("expression").GetString()!, context, options);
            var success = item.TryGetProperty("expectedString", out var expectedString)
                ? result is StringValue text && text.Value == expectedString.GetString()
                : result is BooleanValue flag && flag.Value == item.GetProperty("expectedBoolean").GetBoolean();
            semantics.Add(new
            {
                name = item.GetProperty("name").GetString(),
                success,
                result = result.ToObject(),
            });
        }

        var formats = new List<object>();
        foreach (var item in root.GetProperty("fieldCases").EnumerateArray())
        {
            var state = new Dictionary<string, FormulaValue>
            {
                ["優先度判定結果"] = FormulaValue.New(item.GetProperty("text").GetString()!),
                ["判定ユーザー回答"] = FormulaValue.New(item.GetProperty("answer").GetString()!),
                ["前回確定優先度原文"] = FormulaValue.New(""),
                ["最新利用者入力"] = FormulaValue.New(""),
                ["写真判定反映中"] = FormulaValue.New(false),
            };
            var global = FormulaValue.NewRecordFromFields(
                new NamedValue("写真措置済みテキスト", FormulaValue.New(""))
            );
            string failure = null;
            foreach (var step in root.GetProperty("fieldSteps").EnumerateArray())
            {
                try
                {
                    var context = FormulaValue.NewRecordFromFields(
                        new NamedValue("Topic", FormulaValue.NewRecordFromFields(state.Select(pair => new NamedValue(pair.Key, pair.Value)))),
                        new NamedValue("Global", global)
                    );
                    state[step.GetProperty("variable").GetString()!] = engine.Eval(step.GetProperty("expression").GetString()!, context, options);
                    if (state[step.GetProperty("variable").GetString()!] is ErrorValue error)
                    {
                        failure = step.GetProperty("id").GetString() + ": " + string.Join(" | ", error.Errors.Select(e => e.Message));
                        break;
                    }
                }
                catch (Exception exception)
                {
                    failure = step.GetProperty("id").GetString() + ": " + exception.Message;
                    break;
                }
            }
            string Get(string key) => state.TryGetValue(key, out var value) && value is StringValue text ? text.Value : "";
            var accepted = Get("優先度表示検証") == "合格";
            var rendered = Get("優先度表示組立");
            var incomplete = Get("判定未完了");
            var success = failure == null
                && accepted == item.GetProperty("accept").GetBoolean()
                && (!item.TryGetProperty("contains", out var contains) || rendered.Contains(contains.GetString()!))
                && (!item.TryGetProperty("incomplete", out var pending) || incomplete == pending.GetString());
            formats.Add(new
            {
                name = item.GetProperty("name").GetString(),
                success,
                accepted,
                status = Get("優先度表示検証"),
                incomplete,
                renderedPrefix = rendered.Length > 180 ? rendered.Substring(0, 180) : rendered,
                failure,
            });
        }

        Console.WriteLine(JsonSerializer.Serialize(new
        {
            package = "Microsoft.PowerFx.Interpreter 1.8.1",
            scope = "Standalone Power Fx SDK; no live Copilot Studio host and no AI model call",
            checks,
            semantics,
            formats,
        }, new JsonSerializerOptions { WriteIndented = true }));
    }
}
