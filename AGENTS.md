# 2511youtuber Agent Operating Contract

このrepositoryは、金融・教育系ニュースから動画を生成し、設定に応じてYouTubeへ公開する現行パイプラインです。`AGENTS.md` をrepository運用の正準とし、tool固有instruction fileには差分だけを書きます。

## Authority

判断順序は次です。

1. 現在のユーザー指示
2. この `AGENTS.md`
3. 現在の実行可能コード、`config/default.yaml`、tests、CI、runtime/API evidence
4. 現在の公式provider/API documentation
5. README / `docs/` / historical Issue・PR
6. 推論

古い設計資料や過去の設定値で現在stateを上書きしません。未観測状態は `UNVERIFIED` のまま扱います。

## Repository boundaries

- `apps/`: application entry/composition
- `src/`: workflow, models, steps, providers, utilities
- `config/`: runtime settings, prompts, environment template, market/brand packs
- `assets/`: media resources
- `tests/`: deterministic regression evidence
- `scripts/`: operations and maintenance helpers
- `runs/`: runtime artifacts; source documentationではない
- `docs/`: repository固有の長期有効な仕様・運用契約だけを置く

設定値は `config/default.yaml` と現在のloader/modelを正準にします。同じ設定を別fileやhard-coded constantへ複製しません。news queryを変更するときも、過去の文字数や固定文言をauthorityにせず、現在のquery/query_buckets、selection logic、tests、目的を確認して変更します。

## Change policy

- 既存・標準機能を再利用し、`DELETE > MERGE > REPLACE > ADD` を優先する。
- 同じ責務のconfig、provider wrapper、workflow、schema、documentation、state storeを増やさない。
- repository固有の略語、maturity level、named gate、confidence score、独自taxonomyを実要件なしに作らない。
- open PR / active branch / owning Issueを先に確認し、canonical worklineを再利用する。
- mutationは1つずつ行い、write後にread-backする。
- mergeはexact PR headと必要なCIを確認し、可能ならexpected head SHAを固定する。
- testをgreenにするためにvalidation、安全境界、data-quality checkを弱めない。

## Publication boundary

通常の `task run` / `uv run python -m src.main` は現在の設定ではYouTube public公開へ到達し得ます。外部公開を許可しない検証では `--dry-run` を使います。brand-config付きrunは現在の実装どおりreview/dry-run境界を維持します。

公開を成功と報告するには、exact final artifact、実際に使われたmetadata/channel/visibility、API成功、remote video IDまたは同等receiptを確認します。local render、upload attempt、mock、dry-runをpublication PASSにしません。

## Facts, LLMs, and providers

- LLM outputはuntrusted inputとしてmodel/schema/validatorで検証する。
- ニュースの数値・日付・固有名・因果を補完せず、重要なclaimはsource/provenanceを保持する。
- provider固有promptをcanonical business dataにしない。Storyboard等のrepository contractからprovider adapterへ変換する。
- external API、internet access、credentialが必要な層とdeterministic local testを分離する。
- fallback artifactをrequested resultの成功として扱わない。

## Documentation

- `README.md`: 人間向けの目的、public/dry-run境界、最短の実行・検証入口
- `AGENTS.md`: repository/agent運用契約
- `docs/README.md`: 現在維持する詳細docsの索引
- `docs/business/`, `docs/markets/`: 独立したbusiness/market仕様
- その他: code/configから安全に推測できない現行contract、provenance、運用境界だけ残す

README/AGENTS/code/configを再コピーした「master handbook」、日付付き一回限りの調査報告、実装されていないfuture design、生成されたdirectory解説、古いcommand集はmaintained docsにしません。必要ならGit historyを参照します。

## Secrets and destructive operations

API key、OAuth token、Cookie、service-account secret、private webhookをcommit・fixture・log・docs・Issue・PRへ入れません。`.env` はlocal/runtime concernです。

`task bootstrap`、`task up`、`task cron`、外部投稿、service起動停止などは環境や外部stateを変更します。taskのacceptanceに必要な場合だけ実行し、対象と影響を確認します。sudo/root前提の手順を標準運用として増やしません。

## Validation

repositoryが定義するTaskfileを入口にします。

```bash
task check
```

個別確認が必要なら、現在のTaskfile/pyprojectに存在するcommandを使います。external API/E2E/publicationはcredentialと明示的な実行目的がある場合だけ行います。CI successはexact SHAで実際に走ったcheckだけのevidenceです。

## Completion

完了前に、変更結果、test/CI、mainへのread-back、必要なexternal postcondition、task-created residueを確認します。未実行のruntime/API/publication layerをPASSにしません。

最終報告は、実質的なBefore->After、repository/PR、実行したtest/CI、commit/merge SHA、external receipt、残る `UNVERIFIED` / blockerだけを簡潔に記録します。
