# GitHub City

元のアイソメトリックな夜景を、GitHubの活動から毎日生成するSVGに変更しました。
PythonがGitHub GraphQL APIを読み、描画用パラメーターに変換してから静的なSVGを出力します。
Python 3.12以降の標準ライブラリだけで動作します。

プロフィールに貼ったSVGの内部ではAPIを呼びません。
GitHub Actionsが生成した画像を専用の `city-art` ブランチに保存し、READMEからその画像を参照します。
自動更新のコミットは `city-art` にだけ作るため、ソースのあるデフォルトブランチに毎日の画像更新コミットは入りません。

## 街への対応

| GitHubから取得する情報 | 対応するパラメーター | 街での表現 |
| --- | --- | --- |
| 直近365日のコミット貢献数 | `skyline_height` | ビル群の高さ。既定の上限は330 |
| 所有する公開リポジトリ数（forkを除外） | `building_count` | 建物の数。既定では2〜9棟 |
| 直近365日に作成したPR数 | `neon_buildings` | 屋上の縁にネオンのある建物の数 |
| 直近365日のPRレビュー数 | `rooftop_beacons` | 屋上にアンテナと赤い灯火のある建物の数 |
| 直近30日の貢献数 | `window_light_rate`, `car_count` | 点灯する窓の割合と車の数 |
| 所有する公開リポジトリの主要言語 | 建物ごとのアクセントカラー | 言語色を明るくしたネオンと窓の配色 |
| 所有する公開リポジトリが受けたStarの合計 | `star_count` | 夜空の星の数 |
| 直近365日で貢献があった日数 | `tree_count` | 街路樹の数 |
| ユーザー名、または任意のseed | `seed` | 建物の高さの配分、配色、窓や星の配置を決める乱数の種 |

建物の数は縮尺を抑えた表現です。
1リポジトリを1棟として描いているわけではありません。
使用言語の重みは「その言語を主要言語とする所有公開リポジトリの数」であり、コードの行数やバイト数ではありません。
Starとリポジトリ数は取得時点の合計で、コミット、PR、レビューは直近365日分です。
Issue作成数も取得してSVGのメタデータに記録しますが、既定の見た目には割り当てていません。

コミット数はGitHubのcontribution集計です。
全ブランチのすべてのコミットを数えた値とは一致しません。
対象のメールアドレスやブランチなど、GitHubの[contribution集計条件](https://docs.github.com/en/account-and-profile/reference/profile-contributions-reference)が適用されます。
PR数は作成数であり、マージ済みPR数ではありません。

直近30日の貢献数にはコミット、PR、Issue、レビューなど、APIのcontribution calendarに含まれる活動が入ります。
集計対象は直前に完了したUTCの日を終端とする365日間です。
当日途中の数値を除いて、朝と夜の実行で街が変わることを抑えています。
トークンで読めるデータと、GitHubの公開設定に従って返された集計値を使用します。
非公開活動の集計がAPIの結果に含まれる場合は数値に反映されますが、非公開リポジトリ名は取得していません。

## プロフィールへの導入

プロフィール用の公開リポジトリ `seikasan/seikasan` に、`github_city.py`、`city_renderer.py`、`city.config.json`、`publish_city.sh` と `tests` フォルダーをコピーします。
`.github/workflows/github-city.yml` は、同じパスに置きます。
既存のREADMEは置き換えず、後述の画像参照を追記してください。
`examples` とこの説明書は、動作確認や改造の参考用です。

GitHub Desktopを使う場合は、ローカルのプロフィール用リポジトリにこれらをコピーして、変更をコミットし、普段の運用に従って反映できます。
設定を変更しない場合、Actionsではリポジトリ所有者のユーザー名を使用します。
別のユーザーの街を生成したい場合は、workflowの `CITY_USERNAME` をそのユーザー名に変更します。

APIの読み取り用トークンを用意します。
GitHubの Settings → Developer settings → Personal access tokens → Fine-grained tokens から、公開リポジトリを読むトークンを作成できます。
公開情報で使用する場合は、GitHub公式の[GraphQL認証の説明](https://docs.github.com/en/graphql/guides/forming-calls-with-graphql)に従い、まず追加権限を付けずに試せます。
APIが必要な権限を明示してエラーを返した場合は、その権限を確認してください。
非公開contributionを読む目的で権限を追加する場合は、公開SVGに集計値が記録される点も確認してください。

プロフィール用リポジトリの Settings → Secrets and variables → Actions → New repository secret に移動し、名前を `GH_CITY_TOKEN`、値を作成したトークンとして登録します。
トークンはコードやREADMEに書かず、Secretにだけ設定します。
トークンの有効期限を更新したら、このSecretの値も更新します。

通常の `GITHUB_TOKEN` は画像を書き込むために使用し、個人の活動統計を読むトークンと分けています。
GitHub Actionsの組み込みトークンはそのworkflowがあるリポジトリに権限が制限されるためです。
workflowでは `contents: write` を指定しています。
組織のポリシーやブランチ規則が `city-art` への書き込みを制限している場合は、その設定に従ってください。

リポジトリの Actions → Update GitHub City → Run workflow で初回実行します。
成功すると、`city-art` ブランチに `city.svg` が作成されます。
その後は毎日、日本時間9:20の予定で実行します。
GitHubのscheduleは遅延することがあり、長期間リポジトリの活動がない公開リポジトリではscheduleが無効化される場合もあります。
手動実行は同じ Actions 画面から行えます。

READMEには次を追記します。

```markdown
![GitHub City](https://raw.githubusercontent.com/seikasan/seikasan/city-art/city.svg)
```

別のリポジトリに導入する場合は、URL内の所有者名とリポジトリ名を変更します。
画像の表示にはGitHubのキャッシュが介在するため、生成成功直後に同じ画像URLの表示が更新されるとは限りません。
Actionsが失敗した場合は既存の画像を更新せず、最後に成功した街を維持します。

## 数値と配色の調整

`city.config.json` が調整用ファイルです。
`scales` の各値は、その指標の描画が最大になる基準です。
例えば `commits` の2500を5000に変更すると、同じコミット数でもビルの高さが低くなります。
基準を超えた数値はSVGのメタデータにはそのまま保存し、見た目は上限で止めます。

```text
normalized = min(1, log(1 + count) / log(1 + scale))
height = min_height + (max_height - min_height) * normalized
```

描画上は各建物に固定の倍率を付け、高さを6単位に丸めています。
活動量の小さな変化が、必ずその日の見た目に変化を起こすわけではありません。
直近365日の指標は、集計期間から古い活動が外れると小さくなることもあります。

`appearance` では高さ、建物数、窓の点灯率の範囲を変更できます。
例えば全体のアクセントをシアンに固定したい場合は、`accent` を `"#62dce8"` に変更します。
`null` の場合はGitHubの主要言語から配色します。
任意の形を固定したい場合は `seed` に `"mizuki-night-city"` のような文字列を設定します。
同じseedと同じ統計からは同じSVGを生成します。

統計からの変換を一部だけ上書きするには `overrides` にパラメーターを指定します。
例えば、建物を9棟に固定し、窓の点灯率だけは活動量から変える設定は次のとおりです。

```json
"overrides": {
  "building_count": 9
}
```

上書き可能な値は `building_count`、`skyline_height`、`window_light_rate`、`neon_buildings`、`rooftop_beacons`、`car_count`、`star_count`、`tree_count` です。
建物数は1〜9、高さは32〜350、窓の点灯率は0〜1、ネオンとアンテナは0〜9、車は0〜16、星は0〜150、樹木は0〜20の範囲で指定できます。
ネオンとアンテナの数は、実際の建物数が上限になります。

SVG内の `<metadata id="city-data">` には、集計値と最終的なパラメーターをJSONで保存しています。
`data-buildings`、`data-commits`、`data-pull-requests` もSVGのルートに付いています。
これらは値の確認用です。
値を直接編集するだけでは座標は再計算されないため、形を変えるときは生成コードを実行します。

## オフラインでの確認

`examples` のJSONとSVGは架空の統計です。
実際のseikasanアカウントから取得した値ではありません。
同じseedで静かな街、活動中の街、大都市の3種類を生成しています。

```bash
python github_city.py --stats-file examples/active.json --output dist/city.svg
```

変換後のパラメーターも保存する場合は、`--export-parameters` を追加します。

```bash
python github_city.py --stats-file examples/active.json --output dist/city.svg --export-parameters dist/parameters.json
```

実データをローカルで生成するときは、環境変数 `GH_CITY_TOKEN` にトークンを設定して、`python github_city.py` を実行します。
画像ファイルをブラウザで開くと確認できます。
GitHubに導入するだけなら、ローカルでPythonを操作する必要はありません。

テストは次のコマンドで実行します。

```bash
python -m unittest discover -s tests -v
```

入力が同じ場合の再現性、窓の点灯の単調性、ゼロ件と極端な件数、SVGの独立性、APIのページ送り、期間の境界、API失敗時の処理を確認しています。
Linuxでは一時的なローカルGitリポジトリを作り、初回の画像ブランチ作成、更新履歴の維持、同じ画像の再実行でコミットしないこと、mainの内容が変わらないことも確認します。
実APIへの認証とGitHub上でのActions実行は、Secretを設定してからの初回実行で確認してください。

APIスキーマはGitHub公式の[Users reference](https://docs.github.com/en/graphql/reference/users)に基づきます。
画像として表示するSVGのJavaScriptと外部リソースの制約は[MDN SVG as an image](https://developer.mozilla.org/en-US/docs/Web/SVG/Guides/SVG_as_an_image)で確認できます。
