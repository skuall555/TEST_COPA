"""Check cache expiry/scoping and differential execution against original image YAML."""
import json
import re
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path
import yaml
from build import ROOT, NAME, VERSION


def walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)


def main():
    baseline = yaml.safe_load((ROOT / 'source' / NAME).read_text())
    patched = yaml.safe_load((ROOT / '4-9_貼り替え用.txt').read_text())
    variables = {'Topic': {}, 'Global': {}}
    for g, name in re.findall(r'\b(Topic|Global)\.([^\W\d]\w*)', (ROOT / '4-9_貼り替え用.txt').read_text()):
        variables[g][name] = 'String'
    for node in walk(patched):
        if node.get('kind') != 'SetVariable':
            continue
        g, name = node['variable'].split('.', 1)
        expression = node['value']
        if expression == '=Now()':
            variables[g][name] = 'DateTime'
        elif expression in ('=true', '=false'):
            variables[g][name] = 'Boolean'
        elif expression in ('=0', '=300') or expression.startswith('=DateDiff('):
            variables[g][name] = 'Number'
    variables['Topic']['画像形式対応'] = 'Boolean'
    variables['Topic']['画像事実実質長'] = 'Number'
    variables['Topic']['画像分析出力'] = 'Facts'
    variables['Global']['緊急保安画像受付中'] = 'Boolean'
    checks = []
    for node in walk(patched):
        if node.get('kind') == 'SetVariable' and node['id'].startswith('setVariable_imageSpeed_'):
            g, name = node['variable'].split('.', 1)
            checks.append({'id': node['id'], 'expression': node['value'][1:], 'type': variables[g][name]})
        if node.get('kind') == 'ConditionGroup' and node['id'].startswith('conditionGroup_imageSpeed_'):
            for condition in node['conditions']:
                checks.append({'id': condition['id'], 'expression': condition['condition'][1:], 'type': 'Boolean'})
    guide = '\n'.join(f'MS-{i:03d} 撮影対象・必須視認要素・設置場所の条件。原文相当の試験用文字列。' for i in range(1, 19))
    facts = '■写っている物\n・消火器を確認。\n■位置・向き・状態\n・床に配置。\n■人物・動作\n・該当なし\n■文字・数値\n・不明\n■現場周辺の状況\n・通行人なし\n■画像だけでは確認できないこと\n・画像外は不明'
    judgment = '[追加情報]\n・床に消火器がある。\n[措置済み]\n・【写真有】消火器設置（MS-010）根拠：床に配置。\n[要確認]\n・なし\n[判定なし]\n・写真外の項目'
    def case(name, search=1, vision=1, judge=1, **kw):
        return dict(name=name, system=dict(conversation='会話A', user='利用者A', channel='msteams'), facts=facts, guide=guide, judgment=judgment, expectedSearch=search, expectedVision=vision, expectedJudge=judge, **kw)
    cases = [
        case('初回は3処理・原文を無変更保存', saveSeed=True, expectedCache=True),
        case('2枚目は要領検索だけ省略', search=0),
        case('同じファイル名でも画像事実は毎回再抽出', search=0),
        case('期限切れは再検索', ageSeconds=301),
        case('時計が逆行したキャッシュは再検索', ageSeconds=-30),
        case('別会話は再検索'),
        case('別利用者は再検索'),
        case('別チャネルは再検索'),
        case('要領参照版が変われば再検索', oldVersion='previous-guide-version'),
        case('会話IDなしでは再利用・保存しない', clearCache=True, expectedCache=False),
        case('利用者IDなしでは再利用・保存しない', clearCache=True, expectedCache=False),
        case('チャネルなしでは再利用・保存しない', clearCache=True, expectedCache=False),
        case('MS-ID不足の取得文は再利用用に保存しない', clearCache=True, expectedCache=False),
        case('撮影要領空は元の判定保留処理', judge=0, clearCache=True, expectedCache=False),
        case('撮影要領なしは元の判定保留処理', judge=0, clearCache=True, expectedCache=False),
        case('事実抽出空は検索も判定も行わない', search=0, judge=0),
        case('非対応画像は外部呼出しなし', search=0, vision=0, judge=0, mime='image/webp'),
        case('再利用を無効にすれば元の3処理', cacheEnabled=False),
        case('照合が形式不正でも元と同じく措置済みを消す', search=0),
    ]
    cases[2]['facts'] = facts.replace('消火器', '火気厳禁表示シート')
    cases[2]['judgment'] = judgment.replace('消火器', '火気厳禁表示シート').replace('MS-010', 'MS-003')
    for i, key in [(5, 'conversation'), (6, 'user'), (7, 'channel')]:
        cases[i]['system'][key] = '別の値'
    for i, key in [(9, 'conversation'), (10, 'user'), (11, 'channel')]:
        cases[i]['system'][key] = ''
    cases[12]['guide'] = guide.rsplit('\n', 1)[0]
    cases[13]['guide'] = ''
    cases[14]['guide'] = 'なし'
    cases[15]['facts'] = ''
    cases[18]['judgment'] = '形式が不正な出力・写真有とは扱わない'
    data = dict(variables=variables, baseline=baseline, patched=patched, checks=checks, cases=cases)
    temp = Path('/tmp/image-speed-native')
    temp.mkdir(exist_ok=True)
    for p in Path('/tmp/teams-display-native').glob('Microsoft.*.dll'):
        shutil.copy2(p, temp / p.name)
    for package, version in [('microsoft.powerfx.core', '1.8.1'), ('microsoft.powerfx.interpreter', '1.8.1'), ('microsoft.powerfx.transport.attributes', '1.8.1'), ('microsoft.bcl.asyncinterfaces', '6.0.0')]:
        archive = temp / (package + '.nupkg')
        if not archive.exists():
            urllib.request.urlretrieve(f'https://api.nuget.org/v3-flatcontainer/{package}/{version}/{package}.{version}.nupkg', archive)
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                if name.startswith('lib/netstandard2.0/') and name.endswith('.dll'):
                    (temp / name.rsplit('/', 1)[-1]).write_bytes(z.read(name))
    dotnet = Path('/tmp/subaru-dotnet/dotnet')
    sdk = max((dotnet.parent / 'sdk').iterdir(), key=lambda p: tuple(int(x) for x in p.name.split('.')))
    refs = list((dotnet.parent / 'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net8.0/*.dll')) + list(temp.glob('Microsoft.*.dll'))
    (temp / 'compile.rsp').write_text('-nologo\n-target:exe\n-out:' + str(temp / 'check.dll') + '\n' + '\n'.join('-r:' + str(p) for p in refs) + '\n' + str(ROOT / 'tools/NativeImage.cs'))
    (temp / 'check.runtimeconfig.json').write_text(json.dumps({'runtimeOptions': {'tfm': 'net8.0', 'framework': {'name': 'Microsoft.NETCore.App', 'version': '8.0.0'}}}))
    subprocess.run([str(dotnet), str(sdk / 'Roslyn/bincore/csc.dll'), '@' + str(temp / 'compile.rsp')], check=True)
    (temp / 'input.json').write_text(json.dumps(data, ensure_ascii=False))
    r = subprocess.run([str(dotnet), str(temp / 'check.dll'), str(temp / 'input.json')], capture_output=True, text=True, check=True)
    report = json.loads(r.stdout)
    (ROOT / 'validation/PowerFx検証.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    for key in ('checks', 'runs'):
        failures = [item for item in report[key] if not item['success']]
        print(key, len(report[key]), 'failed', len(failures))
        for failure in failures[:2]:
            print(json.dumps(failure, ensure_ascii=False))
    if any(not item['success'] for key in ('checks', 'runs') for item in report[key]):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
