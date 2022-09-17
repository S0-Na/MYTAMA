
# 機能

**問合せ**

`@tama` で用語検索（2文字以上部分一致検索）

- 用語集検索、問合せ返答
- 用語がない場合には不明単語集に記録
- 用語がない場合で不明単語集に過去に記録がある場合には回数をインクレメント
- 用語がない場合にはログで不明単語が検索されたことを通達

**用語追加**

`/tama create` でモーダルが表示される

- モーダルに新規用語と新規説明を追加
- 既に存在している場合には既知であることを通達し、用語更新へ案内
- 追加された内容をログに出力

**用語更新**

`/tama update`でモーダルが表示される

- モーダルに更新用語と更新する説明内容を追加
- 不明である場合には不明であることを通達し、用語新規追加へ案内
- 更新された内容をログに出力

# **処理フロー**

Excelに答えがある場合

```mermaid
graph LR
subgraph azure
 subgraph webapps
  tama[[たま]]
 end
 subgraph SQL
  excel[(たま用語集)]
 end
end
subgraph interface
 subgraph Web
  slack[[slack]]
 end
 subgraph clientPC
  users([users])
 end

end

  users -."1.@query".-> slack -."2.botToken".-> tama -."3.query".-> excel -."4.response".-> tama -."5.answer".-> slack -."6.answer".-> users

```

用語集に答えがない場合

```mermaid
sequenceDiagram
    actor users
    participant slack
		actor tama
		participant sql

    users->>slack: @tama `問合せ`
		activate slack
    slack->>tama: 単語を認識
		deactivate slack
		activate tama
rect rgb(191, 223, 255)
note right of tama: Azure
		tama->>sql: 用語検索（2文字以上部分一致）
		deactivate tama
		activate sql
		sql->>tama: 検索結果なし
		deactivate sql
		activate tama
		tama->>sql: unknownテーブル検索
		activate sql
		alt exist unknown 
		tama->>sql: 用語がなければ追加
		else not exist unknown
		tama->>sql: 用語があれば検索された回数を加算
		end
end
		deactivate sql
		tama->>slack: 知らない旨を通達、ログを投稿
		activate slack
		deactivate tama
		slack->>users: 誰かに聞いて登録してもらう等、二次対応
		deactivate slack
```


SlackBolt

[https://slack.dev/bolt-python/concepts](https://slack.dev/bolt-python/concepts)
