# Solo-MCP Monetization Roadmap

## コンセプト
システム開発におけるAIエージェントによる車輪の再開発の防止

## Executive Summary

Solo-MCPは「個人開発者向けの無料コア(OS)」と「チーム/企業向けの有料クラウドサービス(App)」の2層構造でマネタイズする。

追加として、課金アイテムみたいな感じで、関数の買いきりの提供を行う。

---

## Phase 0: MVP Launch (現在)

**目標**: GitHub公開 + X宣伝 + 初期ユーザー獲得

### 完了済み機能
- [x] ローカルMCPサーバー (Stdio/SSE)
- [x] セマンティック検索 (Gemini Embedding API)
- [x] Quality Gate (Ruff + Mypy + AI Review)
- [x] Auto-Heal (説明文自動修復)
- [x] Data Sanitizer (絵文字・全角削除)
- [x] ワンクリック起動 (FunctionStore.bat)
- [x] UIダッシュボード (Flet)

### 収益: $0

---

## Open Core Strategy (公開範囲の定義)

Solo-MCPは「Open Core」モデルを採用し、以下のようにリポジトリを分離・管理する。これにより、コミュニティの力を借りつつ、ビジネスモデルを保護する。

| ディレクトリ/ファイル | 公開設定 | 理由 |
|:---|:---|:---|
| `solo_mcp/` (Core Logic) | **Public (OSS)** | コミュニティによる機能改善と信頼性の獲得 |
| `frontend/` (Dashboard) | **Public (OSS)** | UIのカスタマイズ性を開放し、ファンを増やす |
| `data/` (User Data) | **Private (.gitignore)** | ユーザーの関数資産・APIキー・設定は絶対に公開しない |
| `devops/` (CI/CD) | **Public (OSS)** | "DevOps Pack"としての価値をアピールするため公開 |
| `pdk/` (Plugin Dev Kit) | **Public (OSS)** | サードパーティ開発者がプラグインを作るためのキット |
| `pro_plugins/` (予定) | **Private (Proprietary)** | 有料版機能（Supabase Sync等）はここに隔離し、公開リポジトリには含めない |

---

## Phase 1: Community Growth (1-2ヶ月目)

**目標**: GitHub Star 100+、Xフォロワー500+、Blueskyのフォロワー100人

### タスク
- [ ] READMEの英語版作成
- [ ] デモ動画 (YouTube/X)
- [ ] r/LocalLLaMA, Hacker News, Dev.to への投稿
- [ ] Issue対応・コミュニティサポート

### 収益: $0 (投資フェーズ)

---

## Phase 2: Pro Version Launch (2-3ヶ月目)

**目標**: 初月 $500 MRR (月額課金)

### Free版 (BYOK: Bring Your Own Key)
| 機能 | 制限 |
|---|---|
| ローカルMCPサーバー | 無制限 |
| セマンティック検索 | 無制限 |
| Quality Gate | 無制限 |
| ローカル翻訳 (TranslateGemma) | HF_TOKEN必須、ユーザーGPU使用 |
| Supabase Sync | なし |

### Pro版 ($9.99/月)
| 機能 | 内容 |
|---|---|
| **Supabase Sync** | チームで関数ライブラリを共有 |
| **Managed API Keys** | Google API Key を提供 (BYOKの煩わしさ解消) |
| **Managed Translation** | Cloud Run上のTranslateGemmaエンドポイント |
| **優先サポート** | Discord/Slackチャンネル |

### 技術要件
- [ ] Supabase Auth + Row Level Security (RLS) 設定
- [ ] Cloud Run Proxy API (Managed Key用)
- [ ] Stripe連携 (サブスク課金)
- [ ] ダッシュボードに「Upgrade to Pro」ボタン

---

## Phase 3: Function Packs (4-6ヶ月目)

**目標**: MRR $2,000+

### Preset Function Packs (追加収益源)

| パック名 | 内容 | 価格 |
|---|---|---|
| **Data Science Pack** | Pandas/NumPy/Scikit-learn関連の厳選関数20個 | $4.99 (買い切り) |
| **Web Scraping Pack** | BeautifulSoup/Selenium/Playwright関数15個 | $4.99 |
| **API Integration Pack** | OpenAI/Stripe/Twilio等の連携関数15個 | $4.99 |
| **Automation Pack** | ファイル操作/スケジューリング関数15個 | $4.99 |

### 配布方法
1. **GitHub Releases**: `packs/data-science-pack.json` を公開
2. **ダッシュボード統合**: 「Import Pack from URL」ボタン
3. **Pro版限定**: ワンクリック同期 (Supabase経由)

---

## Phase 4: Enterprise (6-12ヶ月目)

**目標**: MRR $10,000+

### Enterprise版 ($99/月〜)
| 機能 | 内容 |
|---|---|
| **Self-hosted Option** | オンプレミスDeployment |
| **SSO (SAML/OIDC)** | 企業認証連携 |
| **Audit Log** | 操作履歴の完全記録 |
| **Priority SLA** | 99.9% Uptime保証 |
| **Custom Packs** | 企業専用関数ライブラリ構築支援 |

---

## Revenue Projection

| Phase | 期間 | 予想MRR | 累計ユーザー |
|---|---|---|---|
| Phase 0 | 現在 | $0 | 0 |
| Phase 1 | 1-2ヶ月目 | $0 | 100 |
| Phase 2 | 2-3ヶ月目 | $500 | 500 |
| Phase 3 | 4-6ヶ月目 | $2,000 | 1,500 |
| Phase 4 | 6-12ヶ月目 | $10,000+ | 5,000+ |

---

## Key Success Metrics

| 指標 | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| GitHub Stars | 100 | 500 | 1,000 |
| Monthly Active Users | 50 | 200 | 500 |
| Paid Subscribers | 0 | 50 | 200 |
| MRR | $0 | $500 | $2,000 |
| Churn Rate | - | < 10% | < 5% |

---

## Competitive Moat (参入障壁)

| 障壁 | 戦略 |
|---|---|
| **データロックイン** | 関数ライブラリが貯まるほど移行コスト増加 |
| **UX差別化** | Auto-Heal, Sanitizerは競合が真似しにくい |
| **コミュニティ** | Preset Packs、ユーザー投稿関数でエコシステム構築 |
| **ブランド** | 「Solo開発者のための」明確なポジショニング |

---

## Next Actions

1. **今すぐ**: GitHub公開 + X宣伝
2. **今週中**: server.py分割リファクタリング
3. **来週**: 統合テスト作成
4. **2週間後**: Supabase Sync設計開始
