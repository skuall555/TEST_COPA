"""Apply additions only to three existing priority prompt nodes; no schema/control changes."""
from restart_support import edit
import additional_rules as rules

def replace_section(text, start, end, replacement):
    a=text.index(start); b=text.index(end,a)
    return text[:a]+replacement+text[b:]

def apply(field):
    def guide(n):
        text=n['value'][2:-1].replace('""','"')
        text=text.replace('# 全現場共通で基本的に「高」',rules.FACTS+'# 全現場共通で基本的に「高」',1)
        for start,end,replacement in [
            ('【ガス検知調査】','# ガス濃度測定',rules.SURVEY),
            ('# ガス濃度測定','# 窓等の開放・換気',rules.CONCENTRATION),
            ('# メーターガス栓閉止','# 分岐バルブ・引込管ガス遮断装置等',rules.METER),
            ('# 分岐バルブ・引込管ガス遮断装置等','# 消火器',rules.VALVE),
            ('# 消火器','# 消防・警察への要請',rules.EXTINGUISHER),
            ('# 立入禁止・保安柵・警戒区域','# 避難誘導',rules.FENCE),
            ('# 周辺住戸・建物調査','# マンホール蓋開放・換気',rules.NEIGHBORS),
        ]:text=replace_section(text,start,end,replacement)
        text=text.replace('【改善後の再評価】',rules.ALARM+'【改善後の再評価】',1)
        text=text.replace('この節は消防・警察要請の判定に適用する。他の初動措置の条件は維持する。','この節は消防・警察要請の判定に適用する。他の初動措置は各節と今回の関連付けで判定する。',1)
        # Resolve location-table defaults rather than append conflicting high rules only.
        start=text.index('# 場所別の基本判定');end=text.index('# 強制的に「高」へ昇格する危険トリガー',start)
        table=text[start:end]
        table=table.replace('# 場所別の基本判定','# 場所別の基本判定\n\n以下は条件未適用の基本表。各措置の明示された高条件・建物種別・関連付けを先に適用し、基本表の中・低で下げない。',1)
        table=table.replace('・メーターガス栓\n\n中：','・メーターガス栓\n・消火器（臭気箇所または検知反応あり）\n\n中：',1)
        table=table.replace('・室内流入確認\n・換気\n\n中：','・室内流入確認\n・換気\n・消火器（臭気箇所または検知反応あり）\n・保安柵または同等措置（危険あり＋第三者立入り可能性）\n\n中：',1)
        a=table.index('## 屋内共用部');b=table.index('## 屋外・敷地・道路',a)
        common=table[a:b].replace('・換気\n','・換気\n・メーターガス栓（屋内臭気・検知あり。対象・系統は確認）\n',1).replace('中：\n・メーターガス栓','中：\n・メーターガス栓（上記の高条件なしの場合）',1)
        table=table[:a]+common+table[b:]
        table=table.replace('・消火器\n','・消火器（臭気・検知・他の高条件なしの場合に限る）\n')
        table=table.replace('・分岐／引込遮断','・分岐／引込遮断（戸建て原則低・非戸建て昇格等は個別節を優先）')
        table=table.replace('ただし検知器反応がある場合、\n消火器は高へ昇格する。','ただし臭気箇所または検知器反応がある場合は消火器を高とする。危険あり＋第三者立入り可能性なら保安柵を高とし、圧力低下・流入反応等では周辺調査を高とする。')
        text=text[:start]+table+text[end:]
        text=text.replace('H-06\n室内・屋内・床下・天井点検口等でLEL10％以上\n→ 供給遮断・滞留ガス排出を高','H-06\nLEL10％以上（都市ガスの概算換算相当を含む）\n→ 多量ガス漏えい。供給遮断・滞留ガス排出を高',1)
        text=text.replace('H-07\n密閉空間でLEL30％以上\n→ 進入禁止を高','H-07\nLEL30％以上（都市ガスの概算換算相当を含む、密閉空間に限定しない）\n→ 当該測定空間より先の進入禁止と保安柵または同等の立入防止を高',1)
        text=text.replace('他の初動措置の既存基準は維持する。','他の初動措置は今回追加した各節・関連付けも適用し、既存のより厳しい高条件を維持する。',1)
        text=text.replace('# 判定手順',rules.LINKED+'# 判定手順',1)
        text=text.replace('場所を確定する。\n不明なら質問する。','場所・建物種別・対象を確認し、不足は必要最小限で質問する。ただし成立済みの高・緊急条件の案内を質問で遅らせない。',1)
        text=text.replace('H-01～H-12の危険トリガーを照合する。','H-01～H-12と各措置節・判定項目の関連付けを照合する。元の測定値・単位・場所を保ち、必要な都市ガス概算換算は元値と換算値を区別する。',1)
        text=text.replace('存在や状態を推測せず「中＋確認事項」とする。','存在や状態を推測せず、明示の高条件がなければ「中＋確認事項」とする。既に成立した高条件・保安柵の危険ありで立入り可能性不明の暫定高は、他の未確認だけを理由に下げない。',1)
        text=text.replace('明確に実施済みと確認できた措置だけを「対応済み」とする。','明確に実施済みと確認できた措置だけを「対応済み」（実施済み）とする。措置名の完全一致は不要で、場所と検知結果を伴う調査、同等の有効な立入防止措置も認識する。範囲不足の保安措置は設置事実と追加の拡大・再設置の未完了を別項目で示す。',1)
        text=text.replace('・入力されていないLEL値を作らない','・入力されていない実測LEL値を作らない。許可された都市ガスVol換算は元値・単位・場所と概算換算値を併記し、実測と区別する',1)
        n['value']='="'+text.replace('"','""')+'"'
    def prompt(n):
        n['value']=n['value'].replace('今回指定された消防・警察の現在危険と改善後再評価の規則を反映したものです。','今回指定された消防・警察の現在危険・改善後再評価と追加要件1〜9を反映したものです。',1)
        n['value']=n['value'][:-1]+'\n'+rules.PROMPT.replace('"','""')+'"'
    def answer(n):
        n['additionalInstructions']+='\n追加要件1〜9の各措置節・関連付けも適用する。元の測定値・単位・場所と概算換算値を区別し、警報による濃度の可能性を実測値にしない。場所と結果を伴う調査・有効な同等立入防止を実施済みとして認識し、部分設置と追加の拡大・再設置の未完了を分ける。明示された高条件を情報不足や場所別の基本表で下げない。'
    field.write_text(edit(field,{'setVariable_priorityGuideFixed':guide,'setVariable_priorityPrompt':prompt,'answer_priority':answer}))
