"""Load each editable feature source into a separate runtime SetVariable node."""
from restart_support import edit,setv
from pathlib import Path
ITEMS=[('01','火気厳禁表示シート'),('02','ポケット警報器'),('03','可燃性ガス検知器と排水口調査'),('04','消火器'),('05','メーターガス栓'),('06','分岐バルブ等'),('07','窓扉と換気'),('08','濃度表示'),('09','保安柵等'),('10','消防警察等'),('11','既存ホワイトシート')]
def lit(s):return '="'+s.replace('"','""')+'"'
def body(n):return n['value'][2:-1].replace('""','"')
def apply(photo):
    root=photo.parent
    feature_nodes=[]
    for code,name in ITEMS:feature_nodes.append(setv('setVariable_imageFeature'+code,'Topic.特徴_'+name,lit((root/'image_features'/(code+'_'+name+'.md')).read_text())))
    expr='""'
    for _,name in ITEMS:expr+=' & Topic.特徴_'+name+' & Char(10) & Char(10)'
    feature_nodes.append(setv('setVariable_imageFeatureCatalog','Topic.画像特徴カタログ','='+expr))
    def first(n):
        text=body(n);a=text.index('【機器の見分け方】');b=text.index('【特に確認する観点】',a)
        text=text[:a]+'''【項目別の特徴を使う】
後ろに連結した「項目別特徴カタログ」を読み、各アイテムを別々に照合する。画像に複数コマがあれば全景・拡大の各領域を確認する。拡大画像だけで全景の表示物を見落とさない。一つの機器を識別できないことを理由に他の項目まで未確認へ落とさない。
識別した物と根拠を「■写っている物」に名称別で書き、場所・配置・採取ホース等を機器ごとに結び付ける。見えない手持ち動作を作らない。数値が読めないこと、機器名が不明なこと、設置・調査が確認できることを分ける。

'''+text[b:]
        text=text.replace('機器は【機器の見分け方】の名称で書く','機器は【項目別特徴カタログ】の名称で書く').replace('扉、窓、換気の状態（上記の見分け方に従う）','扉、窓、換気の状態（項目別特徴カタログの根拠条件に従う）')
        # Illustration examples and old hard-coded appearance paragraphs now live in individual nodes.
        if '【画像・イラスト用の描写指定】'in text:text=text[:text.index('【画像・イラスト用の描写指定】')]
        n['value']=lit(text)+' & Char(10) & "【項目別特徴カタログ】" & Char(10) & Topic.画像特徴カタログ'
        return feature_nodes+[n]
    def second(n):
        text=body(n);a=text.index('【事実からIDを引くための対応表】');b=text.index('【判定と仕分け】',a)
        text=text[:a]+'''【項目ごとの照合】
後ろに連結した「項目別特徴カタログ」で、対象物の特徴・対応MS-ID・設置／調査の条件を一つずつ確認する。カタログは管理者が設定する識別補助であり、未観察の物の存在証拠ではない。実施条件は取得した撮影要領と照合する。特徴の変更は他の項目の定義を上書きしない。
前段で表示シート・ポケット警報器・検知器調査を識別している場合、各項目を別々に照合する。型番・濃度が読めないだけで、識別できた設置・調査を取り消さない。検知器を置き、採取ホース等を排水口に接続して調査する状態も対象。手持ちや人の写り込みは必須条件にしない。使用状態が全く不明で単なる置き物なら測定済みとはしない。
写真外の項目は原則として判定なし。写っていないというだけで未実施にしたり、全項目の撮り直し要求を要確認へ並べたりしない。必要な識別根拠・設置条件が不足する項目だけを具体的に要確認へ示す。ユーザーの明確な実施報告を画像が見えないことだけで取り消さない。

'''+text[b:]
        a=text.index('【判定前の自己点検】');b=text.index('【出力形式】',a)
        text=text[:a]+'【判定前の自己点検】\nカタログの各項目と前段の事実を一つずつ照合し、識別できた項目の落とし漏れがないか確認する。設置・調査の確認と濃度の可読性を混同しない。\n\n'+text[b:]
        if '【機器の描写の整合】'in text:text=text[:text.index('【機器の描写の整合】')]
        n['value']=lit(text)+' & Char(10) & "【項目別特徴カタログ】" & Char(10) & Topic.画像特徴カタログ'
    photo.write_text(edit(photo,{'setVariable_prompt1':first,'setVariable_prompt2':second}))
