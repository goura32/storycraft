# 確定とクラッシュ復旧の契約

## 1. 共通前提

一つの workspace は一つの writer lock だけが変更できます。lock は `runtime/lock` にあり、workspace ID、run ID、PID、取得時刻を持ちます。`run`、`resume`、`step`、admin 解決登録は lock を取れなければ exit code `75` で何も変更しません。

ID 予約、staging 作成、final rename、run-state 更新は同じ filesystem で行います。ID の欠番は許可します。予約済み ID は再利用しません。

## 2. 共通収束表

`pending_commit` があるとき、Provider を呼ぶ前にこの表で収束します。

| staging | final | state 参照 | 処理 |
|---|---|---|---|
| 有効 | なし | 更新前 | staging を final へ rename。final を検証して state を更新 |
| なし | 有効 | 更新前 | final を再検証して state を更新 |
| なし | 有効 | 更新後 | final と state の参照を検証して pending を消す |
| 有効 | 有効 | 任意 | `blocked`。`stop_reason=manual_review_required`、cause=`authority_reference_inconsistency` |
| 不正 | 任意 | 任意 | `blocked`。`stop_reason=manual_review_required`、cause=`authority_reference_inconsistency` |
| なし | なし | 任意 | `blocked`。`stop_reason=manual_review_required`、cause=`internal_error` |

「有効」は schema、参照、input selection、種類ごとの不変条件に通ることです。自動削除、自動選択、LLM 再呼出しはしません。

## 3. kind ごとの state 更新

| kind | final 後に一回だけ行う state 更新 |
|---|---|
| candidate adoption | adoption record と successor selection を current selection にする。next stage / target を更新 |
| scene commit | scene、generation、scene commit、successor selection を参照し、current generation / selection と次 target を更新 |
| volume publication | publication record、manuscript、successor selection を参照し、published volumes と次巻 target または completed を更新 |
| resolution application | resolution record と successor selection を参照し、recovery stage / target と current selection を更新して running にする |

state 更新前に final artifact が不正なら停止します。state 更新後に final artifact が失われた場合も停止します。

## 4. candidate adoption の詳細

candidate、review records、quality disposition、adoption record、successor selection を同じ staging directory に作ります。quality disposition が `blocked` なら adoption を作りません。artifact を先に final にし、adoption と successor selection を検証してから run-state を更新します。

## 5. scene commit の詳細

scene commit の staging は scene、successor generation、commit record、successor selection を含みます。すべてが同じ base generation、scene coordinate、scene prose、continuity update を参照しなければなりません。generation の更新は一度だけ適用します。

## 6. volume publication の詳細

volume publication の staging は publication record、manuscript、successor selection を含みます。record は全 scene、quality disposition、plan、current state、settings を current selection の slot と照合します。final rename 後だけ published volumes を追加します。

## 7. lock の解放

正常終了、blocked、例外のすべてで lock を解放します。異常終了後の stale lock は、PID が存在せず、lock の workspace ID が一致し、run-state が running または blocked のときだけ削除できます。条件を満たさない lock は人手確認待ちにします。
