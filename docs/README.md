# 2511youtuber documentation

日常の入口はrepository rootの [README.md](../README.md)、agent運用契約は [AGENTS.md](../AGENTS.md) です。このdirectoryには、現在のコードや設定から安全に推測できない長期有効な仕様・運用境界だけを残します。

## Maintained documents

| 目的 | 文書 |
| --- | --- |
| branded videoの提供・review境界 | [business/branded-video-bulletin.md](business/branded-video-bulletin.md) |
| 資格コンテンツのmarket/config仕様 | [markets/qualification.md](markets/qualification.md) |
| providerのinternet access境界 | [internet-access.md](internet-access.md) |
| YouTube Analytics実測値のfeedback contract | [performance-feedback.md](performance-feedback.md) |
| thumbnail生成仕様 | [thumbnail.md](thumbnail.md) |
| 外部調査の原資料 | [references/](references/) |

## Source of truth

現在のruntime behaviorは実行可能コード、`config/default.yaml`、models、tests、CIを優先します。Taskやcommandは [Taskfile.yml](../Taskfile.yml) を確認してください。

文書と実装が食い違う場合は、実装・current configuration・primary provider documentationを確認して文書を更新します。古い設定値や過去の調査結果を現在値として扱いません。

## What does not belong here

次はmaintained documentationにしません。

- README / AGENTS / source treeを再説明する巨大handbook
- 一度限りの日付付き調査報告
- 実装されていないfuture architectureやprovider価格比較
- source treeから生成したdirectory-by-directory解説
- root/sudoを前提にした古いcommand集
- GitHub Issueの代替として置かれたissue memo

過去の判断材料が必要な場合はGit historyまたはGitHub Issue/PRを参照します。
