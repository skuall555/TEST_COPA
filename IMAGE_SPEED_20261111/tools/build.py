"""Patch only the pre-Teams image topic; preserve every original action body."""
import copy
import difflib
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(REPO / 'TEAMS_DISPLAY_20261105/tools'))
from yaml_edit import edit, nodes, setv, cg
import yaml

BASE = '4fa63fbcfc1ccf39d063276d9999a5ffb3166132'
NAME = '4-9-画像分析エージェント_緊急保安_optimized.yaml'
VERSION = 'photo-guide-20261111-v1|cr88f_SUBARU_search.file._.pdf_Ten'


def v(ident, variable, expression):
    return setv('setVariable_imageSpeed_' + ident, variable, expression)


def diagnostic(stage):
    return v('diagnostic_' + stage, 'Global.画像分析最新診断',
        '="image-speed-20261111-v1|stage=' + stage + '"'
        ' & "|guide=" & Topic.撮影要領取得経路'
        ' & "|factsMs=" & Text(Topic.画像事実処理ms, "0")'
        ' & "|guideMs=" & Text(Topic.撮影要領処理ms, "0")'
        ' & "|judgeMs=" & Text(Topic.照合判定処理ms, "0")'
        ' & "|totalMs=" & Text(DateDiff(Topic.画像処理計測開始, Now(), TimeUnit.Milliseconds), "0")')


def cache_guard():
    return '=And(Topic.撮影要領再利用, Not(IsBlank(Topic.画像要領会話ID)), Not(IsBlank(Topic.画像要領利用者ID)), Not(IsBlank(Topic.画像要領チャネル)), Global.画像要領キャッシュ会話ID = Topic.画像要領会話ID, Global.画像要領キャッシュ利用者ID = Topic.画像要領利用者ID, Global.画像要領キャッシュチャネル = Topic.画像要領チャネル, Global.画像要領キャッシュ版 = Topic.画像要領キャッシュ版, Not(IsBlank(Global.画像要領キャッシュ取得時刻)), DateDiff(Global.画像要領キャッシュ取得時刻, Now(), TimeUnit.Seconds) >= 0, DateDiff(Global.画像要領キャッシュ取得時刻, Now(), TimeUnit.Seconds) < Topic.撮影要領再利用秒数, Not(IsBlank(Global.画像要領キャッシュ本文)), CountIf(Sequence(18), Not(("MS-" & Text(Value, "000")) in Global.画像要領キャッシュ本文)) = 0)'


def cache_store_guard():
    return '=And(Topic.撮影要領再利用, Not(IsBlank(Topic.画像要領会話ID)), Not(IsBlank(Topic.画像要領利用者ID)), Not(IsBlank(Topic.画像要領チャネル)), Not(IsBlank(Topic.撮影要領本文)), Trim(Topic.撮影要領本文) <> "なし", CountIf(Sequence(18), Not(("MS-" & Text(Value, "000")) in Topic.撮影要領本文)) = 0)'


def replace_search(original):
    store = [
        v('storeBody', 'Global.画像要領キャッシュ本文', '=Topic.撮影要領本文'),
        v('storeConversation', 'Global.画像要領キャッシュ会話ID', '=Topic.画像要領会話ID'),
        v('storeUser', 'Global.画像要領キャッシュ利用者ID', '=Topic.画像要領利用者ID'),
        v('storeChannel', 'Global.画像要領キャッシュチャネル', '=Topic.画像要領チャネル'),
        v('storeVersion', 'Global.画像要領キャッシュ版', '=Topic.画像要領キャッシュ版'),
        v('storeTime', 'Global.画像要領キャッシュ取得時刻', '=Now()'),
    ]
    return [
        v('guideStart', 'Topic.撮影要領計測開始', '=Now()'),
        diagnostic('guide'),
        cg('conditionGroup_imageSpeed_reuseGuide', cache_guard(), [
            v('reuseBody', 'Topic.撮影要領本文', '=Global.画像要領キャッシュ本文'),
            v('guideHit', 'Topic.撮影要領取得経路', '="cache"'),
        ], [
            v('guideMiss', 'Topic.撮影要領取得経路', '="search"'),
            diagnostic('guideSearch'),
            copy.deepcopy(original),
            cg('conditionGroup_imageSpeed_storeGuide', cache_store_guard(), store),
        ]),
        v('guideDuration', 'Topic.撮影要領処理ms', '=DateDiff(Topic.撮影要領計測開始, Now(), TimeUnit.Milliseconds)'),
        diagnostic('afterGuide'),
    ]


def main():
    ROOT.mkdir(exist_ok=True)
    (ROOT / 'source').mkdir(exist_ok=True)
    (ROOT / 'validation').mkdir(exist_ok=True)
    raw = subprocess.check_output(['git', '-C', str(REPO), 'show', BASE + ':SUBARU_optimized/' + NAME])
    source = ROOT / 'source' / NAME
    source.write_bytes(raw)

    def initialize(n):
        return [copy.deepcopy(n),
            v('start', 'Topic.画像処理計測開始', '=Now()'),
            v('factsInit', 'Topic.画像事実処理ms', '=0'),
            v('guideInit', 'Topic.撮影要領処理ms', '=0'),
            v('judgeInit', 'Topic.照合判定処理ms', '=0'),
            v('modeInit', 'Topic.撮影要領取得経路', '="notStarted"'),
            v('cacheEnabled', 'Topic.撮影要領再利用', '=true'),
            v('cacheSeconds', 'Topic.撮影要領再利用秒数', '=300'),
            v('conversation', 'Topic.画像要領会話ID', '=Text(System.Conversation.Id)'),
            v('user', 'Topic.画像要領利用者ID', '=Text(System.User.Id)'),
            v('channel', 'Topic.画像要領チャネル', '=Lower(Text(System.Activity.ChannelId))'),
            v('cacheVersion', 'Topic.画像要領キャッシュ版', '=' + json.dumps(VERSION)),
            diagnostic('received'),
        ]

    def facts(n):
        return [v('factsStart', 'Topic.画像事実計測開始', '=Now()'), diagnostic('image'), copy.deepcopy(n),
            v('factsDuration', 'Topic.画像事実処理ms', '=DateDiff(Topic.画像事実計測開始, Now(), TimeUnit.Milliseconds)'), diagnostic('afterImage')]

    def judge(n):
        return [v('judgeStart', 'Topic.照合判定計測開始', '=Now()'), diagnostic('judge'), copy.deepcopy(n),
            v('judgeDuration', 'Topic.照合判定処理ms', '=DateDiff(Topic.照合判定計測開始, Now(), TimeUnit.Milliseconds)'), diagnostic('afterJudge')]

    ops = {
        'setVariable_debugMode': initialize,
        'invokeAIBuilderModelAction_imageFacts': facts,
        'search_photoGuidelineRetrieve': replace_search,
        'answer_photoGuidelineJudge': judge,
        'sendActivity_analysisResult': lambda n: [diagnostic('done'), copy.deepcopy(n)],
        'sendActivity_unsupportedImageType': lambda n: [diagnostic('unsupported'), copy.deepcopy(n)],
        'sendActivity_promptNotConnected': lambda n: [diagnostic('noFacts'), copy.deepcopy(n)],
    }
    result = edit(source, ops)
    target = ROOT / '4-9_貼り替え用.txt'
    target.write_text(result, encoding='utf-8')
    before = yaml.safe_load(raw)
    after = yaml.safe_load(result)
    old = {n['id']: n for n in nodes(before) if 'kind' in n and 'id' in n}
    new = {n['id']: n for n in nodes(after) if 'kind' in n and 'id' in n}
    # All original nodes except containers with added children must compare equal.
    changed = []
    for ident, n in old.items():
        a = {k: val for k, val in n.items() if k not in ('actions', 'elseActions', 'conditions')}
        b = {k: val for k, val in new[ident].items() if k not in ('actions', 'elseActions', 'conditions')}
        if a != b:
            changed.append(ident)
    assert not changed, changed
    assert set(old) <= set(new)
    assert before['beginDialog']['condition'] == after['beginDialog']['condition']
    (ROOT / 'validation/scope.json').write_text(json.dumps({
        'baseline_commit': BASE, 'baseline_sha256': hashlib.sha256(raw).hexdigest(),
        'output_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
        'original_node_bodies_changed': changed, 'original_node_ids_preserved': len(old),
        'new_nodes': len(new) - len(old),
        'quality_verification': 'NOT_RUN: no live images/model/tenant execution',
        'latency_measurement': 'NOT_RUN: no live tenant timing',
        'first_image_external_calls': 'unchanged: vision + guideline search/generation + judge',
        'cache_hit_external_calls': 'vision + judge; no guideline search/generation',
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (ROOT / 'validation/image-only.diff').write_text(''.join(difflib.unified_diff(raw.decode().splitlines(True), result.splitlines(True), fromfile='4fa63fb/4-9', tofile='image-speed/4-9')), encoding='utf-8')
    print('Created image-only patch; original action bodies unchanged:', len(old))


if __name__ == '__main__':
    main()
