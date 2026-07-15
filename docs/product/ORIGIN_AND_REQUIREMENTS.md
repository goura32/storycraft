# 元ネタの調査記録

> この文書は要件や仕様の正本ではない。調査時の参考情報を残すための記録である。
>
> 製品上の約束は[要件](REQUIREMENTS.md)、実装方針は[仕様](SPECIFICATION.md)を参照する。

## 参考にした公開情報

- Sudowriteは、章を場面の集合として扱い、場面ごとに本文を書く流れを案内している。
  <https://docs.sudowrite.com/using-sudowrite/1ow1qkGqof9rtcyGnrWUBS/scenes--chapter-prose/49p5MTVxTKkVFEC5rVUzpY>
- NovelAIは、設定集、記憶、選択範囲の書き直しを中心に自由な執筆を支援している。
  <https://docs.novelai.net/en/text/editor/>
- KDPはシリーズを作成して販売でき、電子書籍には条件により最大70%のロイヤリティ制度がある。
  <https://kdp.amazon.co.jp/ja_JP/help/topic/GMFKBUS43QQ5AJ5A>
  <https://kdp.amazon.com/ja_JP/help/topic/G200644210>
- KDP Selectは90日間の任意プログラムで、Kindle Unlimitedおよび販促機会を提供する。
  <https://kdp.amazon.com/ja_JP/help/topic/G200798990>

## 調査から得た方向性

- 自由執筆型は発想を止めないが、長編を終わらせる責任は利用者側に残る。
- 構成支援型は整理しやすいが、確認回数や内部管理が多いと執筆開始までが重くなる。
- Storycraftは、利用者の初回企画だけを受け取り、その後は完結まで自動で進める方向を選ぶ。
- KDPでの無料化は販売先のルールに依存するため、製品の固定要件は「初巻を無料導入巻として扱う」とする。
