# Solo-MCP Monetization Roadmap (Horiemon Style)

## コンセプト
システム開発におけるAIエージェントによる車輪の再発明の防止。
「世界中の関数を、あなたの武器に。」

## Executive Summary

Solo-MCPは **「Public-First (まずは公開)」** 戦略を採用し、圧倒的なユーザー数とコンテンツ（関数）を確保した後に、プライバシーとセキュリティで課金するモデルへ移行する。

1.  **Public (Free)**: 「Public Dump」。誰もが無料で関数を公開・利用可能。Supabaseの公開テーブルを使用。
2.  **Private (Paid)**: 「Private Vault」。自分だけの、あるいはチームだけの秘密の関数ストレージ。
3.  **Enterprise (High-Ticket)**: 「Enterprise Gate」。企業の安心・安全（監査、品質保証）をお金に変える。

---

## Phase 1: The "Public Dump" MVP (Current Status)

**目的:** ユーザー獲得とコンテンツの集積（トラフィック重視）。
**マネタイズ:** なし（完全無料）。

### 提供価値
- **Global Sync:** ワンクリックで自作関数を世界中に公開。
- **Unlimited Access:** 世界中のエンジニアが作った関数を無料で使い放題。
- **Zero Friction:** Dockerレス、設定不要、0.1秒で即保存。

### インフラコスト
- **Compute:** ユーザーのPC（ローカル）にオフロード。サーバーコストほぼゼロ。
- **Storage:** Supabase (Free Tier) を活用。

---

## Phase 2: The "Private Vault" (Next Step)

**目的:** 「秘密にしたい」という欲求への課金（月額サブスクリプション）。
**ターゲット:** フリーランス、小規模チーム、スタートアップ。

### Pro機能 ($5 - $10 / month)
- **Private Storage:** 公開せずに自分専用のクラウドストレージに関数を保存。
- **Team Sync:** 招待したメンバー間でのみ関数を共有。
- **Version History (Unlimited):** 無制限のバージョン管理とロールバック。

### 実装予定機能
- [ ] Supabase RLS (Row Level Security) によるアクセス制御。
- [ ] Stripe 決済の統合。
- [ ] プライベートリポジトリへの招待機能。

---

## Phase 3: The "Enterprise Gate" (Future)

**目的:** 企業の「コンプライアンス」と「品質保証」への課金。
**ターゲット:** 中堅・大企業。

### Enterprise機能 (Custom Pricing)
- **Cloud Quality Gate:** クラウド上での厳密な静的解析・脆弱性診断。
- **Audit Logs:** 「誰が」「いつ」「どの関数を」使ったかの完全なログ。
- **SLA:** 稼働率保証。
- **On-Premise / VPC:** 顧客環境へのデプロイオプション。

### マネタイズ設定
- APIコール課金、または年間ライセンス契約。

---

## Revenue Projection (予測)

| Phase | 期間 | 目標MRR | ユーザー数 |
|---|---|---|---|
| **Phase 1 (Public)** | Now - 3ヶ月 | $0 | 1,000+ |
| **Phase 2 (Private)** | 3 - 6ヶ月 | $1,000 | 3,000+ |
| **Phase 3 (Ent)** | 6 - 12ヶ月 | $10,000+ | 10,000+ |

---

## Competitive Moat (競合優位性)

1.  **Speed:** Dockerを廃止し、他社製品より圧倒的に速い（0.1秒保存）。
2.  **Network Effect:** 「Public Store」に関数が集まるほど、後発エージェントはここを使わざるを得なくなる。
3.  **Simplicity:** `uv` ひとつで動く、究極の手軽さ。
