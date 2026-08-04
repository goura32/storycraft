# LLM と検証の設計

## 1. 責務の分離

| 層 | 責務 | 採用可否 |
|---|---|---|
| LLM 境界 | Ollama の送受信、通信失敗、時間切れ、技術的再試行、シード、呼出し保存 | 決めない |
| 決定的応答検証 | JSON 解析、スキーマ、ID、参照、更新範囲、`invalid_response_limit` 回までの形式不正再呼出し | 形式有効だけを決める |
| 品質ループ | 生成、独立確認、修正、再確認、品質上限時の注意付き採用 | 通常工程の候補を採用する |
| 永続化・復旧 | 不変確定、採用参照、停止、復旧 | LLM 記録を物語正本にしない |

各行は責務境界を示す名称であり、クラス名・関数名・実装APIを契約にしません。

### 1.1 LLM 境界（wire 契約）

LLM 境界は Ollama との通信のみを担当し、シード・タイムアウト・技術的再試行を制御します。Ollama への全通信は **OpenAI 互換 API** を使う。モデル能力は `GET /v1/models/{model}` の `{ "id": "model", "context_length": 正の整数 }` から取得する。接続直前にhostnameを許可済みloopback/private addressへ解決してHTTP requestをそのliteral addressへpinし、redirectは追従しない。HTTP・接続・時間切れ・provider error envelope は技術的失敗として扱い、`technical_retry_limit` は各論理処理で許可する物理試行回数（初回を含む）です。成功 HTTP の capability payload で `id` が不一致、`context_length` が欠落または正整数でない場合は形式不正として `invalid_response_limit` を消費する。いずれも各物理試行を `model_capability` call record として保存し、該当上限到達時はそれぞれ `technical_retry_exhausted` または `invalid_response_limit` で `blocked` にする。実装上の例外は共通の失敗分類へ変換し、クライアント固有の関数名を契約にしない。生成は `POST /v1/chat/completions` に `model`、`messages`、`think: true`、`stream: false`、`options: {"num_ctx": context_length}`、指定済みの `request_options`、および構造化時の `response_format: {"type":"json_schema","json_schema":{"name":"storycraft_response","strict":true,"schema":<工程スキーマ>}}` を送る。`schema` がある場合は `choices[0].message.content` を JSON として解析し、`schema` がない場面本文では同じ欄を raw text として受け取る。Ollama ネイティブ API（`/api/generate` 等）は使わない。

provider境界は有効な`settings_id`、`workspace_root`、およびworkspace内のcanonicalな`runtime/calls` directoryを必須とします。HTTP開始前にworkspace rootとrecord directoryのdirectory descriptorを保持し、能力取得とcompletionの両方を同じFD anchorへ束縛してから通信します。record保存時にpathとdescriptorのidentityが一致しなければfail-closedで停止し、保存先を再解決しません。raw logも同様に、workspace内の`runtime/raw_logs` descriptorへJSON/Markdown pairのatomic書込みを固定します。HTTP openerは環境変数のproxy設定を使わず、hostnameのliteral address pinningを迂回させません。
provider境界ではworkspace rootだけでなく`runtime`とcanonicalな`runtime/calls`のdescriptorもLLMClient生成時に保持し、各物理呼出しへ引き渡します。`runtime`のcounterとcall recordはこの保持FDから操作し、pathをprovider呼出し直前に再解決しません。provider境界へはHTTP wire実装だけが到達可能で、Python SDK client、SDK stream、別provider transportへのfallbackを持ちません。`ollama_http_boundary` が真でない場合、provider call開始前に契約エラーで停止します。初回path検査で取得したroot/対象directoryのidentityと、実際に開いたdescriptorを比較してから通信・保存を開始し、call record leafの公開後identityも再検証して差替えを検知します。raw logの予約後targetも既存entryを置換せず、JSON/Markdown各leafの公開後identityを再検証します。各物理HTTP呼出しのcall recordは固有のseedを保存し、同じ論理呼出しで能力取得とcompletionを行う場合もseedを共有しません。能力取得はcompletionとは別の決定的seedを使い、completion requestの`options.seed`は呼出し元のseedを使います。

provider endpointのpathは正規化後にちょうど一つの`/v1` suffixを持ち、`/v1/v1`の重複はcanonical pathへ畳み込みます。

### 1.2 決定的応答検証

JSON 解析・スキーマ検証・ID形式・参照存在・更新範囲・根拠位置解決を決定的に行います。契約は「未知項目拒否」「スキーマ・ID・参照・範囲・根拠位置の 5 観点で検証」「不合格は形式不正 1 回と数える」だけを定め、実装関数シグネチャは定めません。

### 1.3 品質ループ

生成・決定的検証・確認を行い、重大な指摘があれば、正の `quality_revision_limit` の範囲で修正・再確認を繰り返します。上限到達時は最後の形式有効候補を注意付き採用します。形式不正上限到達は、生成または確認で有効候補がない場合は `blocked`、修正応答が形式不正の場合も `blocked` とします。品質修正は必ず有限回で終了します。

V1 の提供者は `ollama` だけです。設定検証器は他の提供者を拒否します。

すべての生成・確認・修正呼出しは Thinking を有効化する（OpenAI 互換 request の `think: true`）。実行時は、選択したモデルが公開する最大コンテキスト長を前記 endpoint から取得し、その値を request の `options.num_ctx` に指定する。トークン量・文字数・費用を理由に入力を配分・切詰め・停止しない。provider がモデルの context window 超過を返した場合は技術的失敗として再試行し、上限到達時は `technical_retry_exhausted` とする。

温度、`top_p`、`top_k`、`repeat_penalty` は `settings.request_options` で任意に指定できる。**既定では `request_options` を省略し、これらのキーを request に送らない。**指定されたキーだけを `options` に追加し、Ollama のモデル既定値を上書きしない。

## 2. 二種類の再試行

技術的再試行と形式不正再呼出しを混ぜません。

| 区分 | 対象 | 上限 | 上限到達 |
|---|---|---|---|
| 技術的再試行 | 接続不能、提供者エラー、HTTP/接続時間切れ | `technical_retry_limit`。作業場所作成時に固定 | `blocked`、`last_error.code=technical_retry_exhausted` |
| 形式不正再呼出し | 空応答、解析失敗、非オブジェクト、スキーマ・参照・根拠・更新範囲の不適合、成功 HTTP の capability payload 不正 | 各論理処理で初回を含め `invalid_response_limit` 回 | 生成・確認で有効候補がなければ `blocked`、`last_error.code=invalid_response_limit`。修正応答が形式不正上限に達した場合も `blocked` |

生成、確認（provider operation=`review`）、修正（provider operation=`revise`）は別々の論理処理です。`request` を含む構造化工程には CandidateResponse の品質ループを適用します。`scene_prose` の生成・修正だけは wire 上 raw textで、promptとrequestにresponse schemaを含めず、コードが保存時の座標付き `scene-prose` contentへ変換してから同じ候補検証・品質ループへ渡します。技術失敗は応答本文がないため、形式不正再呼出しを消費しません。形式不正の各回は別のシードを使い、すべての物理呼出しを記録します。

各論理処理の `format_attempt` は1から始め、成功 HTTP 応答が形式不正だったときだけ1増やします。各 `format_attempt` 内の `technical_attempt` は1から始め、通信失敗・提供者エラー・時間切れごとに増やします。call recordのfailure codeは `connection_error`、`http_error`、`timeout`、`provider_error` のいずれかです。技術的再試行が成功したら、その応答の形式検証結果を同じ `format_attempt` に記録します。技術的再試行上限に達した場合は形式不正を消費せず、論理処理を `blocked` にします。

各論理処理は `format_attempt=1` から開始し、各回で技術的再試行を完了してから応答を決定的に検証します。有効ならその値を返し、形式不正なら次のシードで次の `format_attempt` に進めます。物理呼出しと provider 境界の検証結果は call record に保存します。call recordを保存するprovider境界は有効な `settings_id` と、call record directoryを含む作業場所の `workspace_root` を必須とし、保存先が作業場所外ならHTTP呼出し前に契約エラーで停止してrecordを作りません。工程固有の意味・参照・根拠検証を通過した値だけが candidate/review/quality record になり、別の validation 成果物は作りません。raw logはJSON/Markdownの両方を同一予約stemでatomicに保存し、prompt/response/exceptionに含まれるcredential-shaped valueをredactします。上限まで有効な応答がなければ、処理を `invalid_response_limit` として終了します。関数名やクラス名を実装契約にしません。

`invalid_response_limit` は、生成・確認・修正の各論理処理で形式不正の再呼出しを制限する。上限到達時は `blocked` にして `last_error.code=invalid_response_limit` を保存する。

## 3. 通常の品質ループ

構造有効な候補だけを独立 LLM が確認します。構造化工程のテンプレートに渡す root 値は `context`、`candidate`、`critique`、`output_schema` です。`scene_prose` の生成・修正テンプレートだけは `context`、必要な `candidate`、`critique` を渡し、`output_schema` を渡しません。provider operation は確認を `review`、修正を `revise` とし、user template のファイル名はそれぞれ `critique_{stage}.j2`、`fix_{stage}.j2` です。構造化工程の生成・修正 wire は CandidateResponse、`scene_prose` の生成・修正 wire は raw text です。ID は呼出し側が束縛し、LLM 応答には含めません。

| 処理 | LLM への必須入力 |
|---|---|
| 生成 | `context`（スナップショットから組み立てた当該工程の正本入力、固定設定、許可済み文脈） |
| 確認 | **同じ `context` + 確認対象 `candidate`** |
| 修正 | **同じ `context` + 現在の `candidate` + 有効な `critique`** |
| 再確認 | **同じ `context` + 修正後 `candidate`** |

`request_intake` だけは selection 前の入力例外です。`keywords` は `inputs/keywords-.../record.json` の `keywords` 配列と `language` だけ、`settings` は `runtime/settings/.../record.json` の `payload` だけを、この順で `### keywords`、`### settings` の固定ラベル下に置きます。各値は同じ canonical JSON（UTF-8、`ensure_ascii=false`、`sort_keys=true`、`separators=(",", ":")`）でシリアライズし、record envelope、作成時刻、内部path、selection snapshot、採用済み作品成果物は送信しません。候補記録は `input_selection_id=null`、`keywords_id`、`settings_id` を保存する。確認記録は対象候補IDとcall IDで候補記録へ結び付き、呼出し記録は `settings_id` と `input_refs`（keywords/settingsを含む）で入力源を追跡する。確認・呼出し記録へ候補と同じフィールドを重複保存しない。その他の工程では工程契約が列挙する必須入力スロットの順番で、各 slot の採用成果物を **canonical JSON** としてシリアライズする。工程契約が明示参照を列挙する場合は、slot 名と成果物 ID をその後に同じ形式で加える。生成・確認・修正は、その時点で必要な context、候補、確認応答、system/user 指示文、応答schema、固定メタデータを省略せず送る。ただし`scene_prose`の生成・修正はraw text transportのためresponse schemaを送らず、本文をそのままuser promptへ置く。2回目以降の確認は前回の修正出力 `candidate(r)` を必ず含み、2回目以降の修正は前回の修正出力 `candidate(r)` と今回の確認出力 `critique(r)` を必ず含む。初回生成 `candidate(0)` や過去の確認を、直前候補・今回確認の代わりに使わない。確認応答に解決不能な根拠位置が一つでもあれば、応答全体を形式不正として採用せず、`invalid_response_limit` の対象にします。`issues`、`explanation`、`evidence_locations` に人工的な件数・長さ上限は設けず、選択モデルの最大コンテキスト内で要求全体を送ります。slot、candidate、critiqueはテンプレートで定めた別々のJSON値として固定位置に置き、値同士を区切り文字で連結しません。system messageとuser messageの境界、各ラベル、候補・確認の配置はテンプレートを正本とし、再確認・改稿でも同じ境界を使います。



```text
生成(context) → 決定的検証 → 確認(context + candidate)
  ├─ 重大なし: clean 採用
  ├─ 重大あり・上限前: 修正(context + candidate + critique)
  │                         → 決定的検証
  │                         → 再確認(context + revised candidate)
  重大あり・上限到達: 最後の構造有効候補を注意付き採用。構造有効候補が一度も生成されていない場合（**形式不正再呼出し上限**すべて形式不正）は、`blocked` と `last_error.code=invalid_response_limit` とする。
```

`quality_revision_limit` を含む設定入力は `init --config FILE` だけが読み、検証済みの全設定を不変 `settings` 成果物へ一回だけ確定します。以後の処理は選択スナップショットの `settings` スロットだけを読み、設定入力ファイルや可変 `runtime/config.json` を保存・参照しません。`quality_revision_limit=N` は1以上の整数で、重大指摘に対する修正を最大 `N` 回許可します。修正回数が `N` に達した時点で重大指摘が残っていれば、最後の形式有効候補を注意付き採用して次工程へ進みます。

修正は候補全体を置き換えられます。ただしスキーマ、ID、参照、更新可能範囲、作品状態の根拠契約は必ず再検証します。既存の確定物を、望む結果を探すために再生成・上書きしてはなりません。

レビュー重要度は `critical`、`notice` の二値です。LLM は提案し、コードが値と根拠位置を検証します。存在しない JSON パス、段落番号、本文位置が一つでもある確認応答は根拠位置検証失敗の形式不正として採用せず、`invalid_response_limit` の対象にします。

品質上限で重大指摘が残った選択結果は `accepted_with_notice` とします。通常の上限到達による注意種別は常に `編集` です。LLM が注意種別を提案・変更することはありません。巻公開時は定型文以外を読者原稿へ出しません。

## 4. LLM 応答からの ID 採番禁止

LLM は、候補、確認、修正のいずれでも、新しい成果物 ID、候補 ID、確認記録 ID、指摘 ID、人物 ID、計画 ID、状態 ID を生成・返却してはなりません。未解決事項は V1 の canonical `thread_name` を返し、別個の thread ID は作りません。その他の ID は呼出し側と永続化層だけが採番し、呼出し記録、入力選択、対象候補、確認観点、修正系譜に束縛します。

例外は、呼出し時に読み取り専用カタログとして渡した**既存 ID の選択**だけです。選択可能 ID の全一覧、各 ID の説明、選択対象の種別を入力に含め、出力検証器は選択値がその一覧に含まれることだけを許可します。LLM が新しい ID を作る、一覧外 ID を返す、ID を推測して補うことは形式不正です。

新規人物・新規未解決事項のように新しい識別子が必要な候補は、LLM が名前・役割・説明・関係の意味内容だけを返します。コードが候補全体を形式検証した後に ID を採番し、名前・関係記述を解決して正規形内容に ID を付与します。解決不能な参照、同名曖昧性、重複は形式不正です。

## 5. 生成・修正の共通候補スキーマ

構造化工程の生成と修正は、[`schemas-and-normalization.md` の CandidateResponse](schemas-and-normalization.md#31-candidateresponse-生成修正の応答) を返します。工程ごとに異なるのは `artifact_kind` が示す `payload` スキーマだけです。`scene_prose` の生成・修正は CandidateResponse envelope を wire で返さず、raw text を保存時の `scene-prose` contentへ変換します。修正専用スキーマ、差分だけを返すスキーマ、部分成果物だけを返すスキーマは持ちません。

構造化工程の生成と修正の LLM 応答は完全に同じ CandidateResponse スキーマであり、元候補 ID、対象確認記録 ID、基準選択 ID を含めません。これらは LLM 呼出しの入力コンテキストと、応答保存時にシステムが作る候補記録にだけ保持します。`payload` は必ず同じ成果物種類の完全スキーマを満たし、部分差分を返してはなりません。`scene_prose` はこの envelope の例外として raw text を受け取り、コードが完全な `scene-prose` contentを作ります。`generation` と `scene` はコード専用成果物であり、この応答の `artifact_kind` に含めません。`scene-prose` を修正した場合は、新候補採用後に対応する継続性更新を新たに生成します。

`ReviewResponse` の JSON スキーマと相関制約の正本は [`schemas-and-normalization.md` の §3.2](schemas-and-normalization.md#32-reviewresponse-確認の応答) です。ここでは品質ループ上の入力・採用規則だけを定めます。

## 6. 最小記録形式

call record は `runtime/calls/<call-id>/record.json` に保存します。完全な保存スキーマと相関制約の正本は [`schemas-and-normalization.md` の §3.7](schemas-and-normalization.md#37-call-record呼出し記録) です。待機時間の実測値は保存しません。

`quality-disposition.json` は採用済み品質判定 `quality/<quality-id>/record.json` の内容を指す名称であり、別ファイルを作らない。`quality-id` は `quality-{通番6桁}`、採用記録と本文採用 slot が同じ ID を参照する。

`status` と `validate` は提供者を呼ばず、これらの参照、形式、試行上限、シード重複、採用連鎖を再検証します。
