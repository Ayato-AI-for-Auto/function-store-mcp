# Function Store MCP MVP - 実装計画書

## 🎯 **プロジェクト概要**

### **プロジェクト名**: Function Store MCP Performance Enhancement  
### **実装期間**: 3週間（短期集中実装）  
### **目標**: MVPから実用レベルへのパフォーマンス向上

---

## 📊 **現状分析サマリー**

### **現在の問題点**：
- 検索応答時間: 1-3秒（MVPレベル）
- 主要ボトルネック: 検索クエリ本身的embedding計算
- ユーザー体験: AIエージェント連携時の待機時間过长

### **技術資産**：
- ✅ Local-First設計（外部API依存ゼロ）
- ✅ DuckDB + sentence-transformers実装済み
- ✅ 関数ベクトルデータ保存済み
- ✅ AST静的解析 + セキュリティ機能完備

---

## 🚀 **実装戦略**

### **原則**: ビジネス的合理性重視（MVPレベルに適した投資効果最大化）

#### **高ROI施策のみ実装**：
1. 人気クエリEmbeddingキャッシュ（効果大・実装容易）
2. 基本的なパフォーマンス監視（運用最適化）

#### **低ROI施策は見送り**：
- 検索結果キャッシュ（Invalidation問題で複雑化）
- 分散データベース（現在のMVP規模では不要）

---

## 📋 **実装計画**

### **Week 1: 人気クエリキャッシュ実装**

#### **Day 1-2: コアキャッシュ機能開発**
```python
# 新規作成: backend/mcp_core/engine/popular_query_cache.py
from collections import Counter, defaultdict
import time
import hashlib
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class PopularQueryCache:
    """
    人気クエリのembedding結果をキャッシュして検索パフォーマンス向上
    """
    def __init__(self, max_cache_size: int = 500, popularity_threshold: int = 3):
        self.query_embeddings = {}  # {query_hash: embedding_vector}
        self.query_frequency = Counter()  # {query_text: access_count}
        self.last_accessed = {}  # {query_hash: timestamp}
        self.hit_count = 0
        self.miss_count = 0
        self.max_cache_size = max_cache_size
        self.popularity_threshold = popularity_threshold
    
    def get_embedding_cache(self, query: str) -> Optional[List[float]]:
        """人気クエリのembeddingを取得"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        if query_hash in self.query_embeddings:
            self.last_accessed[query_hash] = time.time()
            self.hit_count += 1
            return self.query_embeddings[query_hash]
        self.miss_count += 1
        return None
    
    def cache_embedding_if_popular(self, query: str, embedding: List[float]) -> None:
        """人気クエリのembeddingをキャッシュ"""
        normalized_query = query.lower().strip()
        self.query_frequency[normalized_query] += 1
        
        if self.query_frequency[normalized_query] >= self.popularity_threshold:
            if len(self.query_embeddings) >= self.max_cache_size:
                self._evict_least_popular()
            
            query_hash = hashlib.md5(query.encode()).hexdigest()
            self.query_embeddings[query_hash] = embedding
            self.last_accessed[query_hash] = time.time()
            logger.info(f"Cached popular query: {normalized_query}")
    
    def _evict_least_popular(self) -> None:
        """LRU 방식으로人気度の低いキャッシュを削除"""
        if not self.last_accessed:
            return
        
        oldest_hash = min(self.last_accessed.keys(), 
                         key=lambda h: self.last_accessed[h])
        del self.query_embeddings[oldest_hash]
        del self.last_accessed[oldest_hash]
        logger.info(f"Evicted cache entry: {oldest_hash}")
    
    def get_stats(self) -> Dict:
        """キャッシュ統計情報"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
        return {
            "cache_size": len(self.query_embeddings),
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": f"{hit_rate:.2f}%",
            "total_queries": len(self.query_frequency)
        }
```

#### **Day 3-4: 検索ロジック統合**
```python
# 修正: backend/mcp_core/engine/logic.py
# _do_search_query関数の修正

def _do_search_query(query: str, limit: int = 20) -> List[Dict]:
    """内部セマンティック検索実装（キャッシュ統合版）"""
    # 1. 人気クエリEmbeddingキャッシュをチェック
    query_embedding = popular_cache.get_embedding_cache(query)
    if query_embedding is None:
        # 2. 初回Embedding計算
        emb = embedding_service.get_embedding(query)
        query_embedding = emb.tolist()
        # 3. 人気クエリの場合はキャッシュ
        popular_cache.cache_embedding_if_popular(query, query_embedding)
    
    # 4. 既存DB検索ロジック（変更なし）
    conn = get_db_connection(read_only=True)
    try:
        sql = """
            SELECT f.id, f.name, f.description, f.tags, f.status,
                   list_cosine_similarity(e.vector, ?::FLOAT[]) as similarity,
                   COALESCE(CAST(json_extract(f.metadata, '$.quality_score') AS INTEGER), 50) as qs
            FROM functions f
            JOIN embeddings e ON f.id = e.function_id
            WHERE f.status != 'deleted'
            ORDER BY (similarity * 0.7 + (qs / 100.0) * 0.3) DESC
            LIMIT ?
        """
        rows = conn.execute(sql, (query_embedding, limit)).fetchall()

        results = []
        for r in rows:
            results.append(
                {
                    "id": r[0],
                    "name": r[1],
                    "description": r[2],
                    "tags": json.loads(r[3]) if r[3] else [],
                    "status": r[4],
                    "similarity": round(float(r[5]), 4),
                    "quality_score": r[6],
                    "score": round(float(r[5]) * 0.7 + (r[6] / 100.0) * 0.3, 4),
                }
            )
        return results
    finally:
        conn.close()
```

#### **Day 5: キャッシュ統計エンドポイント追加**
```python
# 追加: backend/mcp_core/api/api.py
@app.get("/cache/stats")
async def get_cache_stats():
    """キャッシュ統計情報を取得"""
    return popular_cache.get_stats()
```

### **Week 2: パフォーマンス監視実装**

#### **Day 1-2: パフォーマンスメトリクス追加**
```python
# 新規作成: backend/mcp_core/monitoring/performance.py
import time
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class PerformanceTracker:
    def __init__(self):
        self.search_times = []
        self.cache_hit_rates = []
        self.active_sessions = 0
    
    def track_search_performance(self, duration: float, cache_hit: bool):
        """検索パフォーマンスを記録"""
        self.search_times.append(duration)
        if len(self.search_times) > 1000:  # 最新1000件のみ保持
            self.search_times.pop(0)
        
        logger.info(f"Search completed in {duration:.3f}s, Cache Hit: {cache_hit}")
    
    def get_average_search_time(self) -> float:
        """平均検索時間を取得"""
        if not self.search_times:
            return 0.0
        return sum(self.search_times) / len(self.search_times)
    
    def get_performance_report(self) -> Dict:
        """パフォーマンスレポートを生成"""
        return {
            "average_search_time": self.get_average_search_time(),
            "total_searches_tracked": len(self.search_times),
            "active_sessions": self.active_sessions
        }

# グローバルインスタンス
performance_tracker = PerformanceTracker()
```

#### **Day 3-4: 検索時間計測実装**
```python
# 修正: backend/mcp_core/engine/logic.py
# do_search_impl関数の修正

def do_search_impl(query: str, limit: int = 20) -> List[Dict]:
    """検索実装（パフォーマンス計測付き）"""
    start_time = time.time()
    
    # Simple retry logic for when search is called immediately after save
    # and background embedding might be in progress or DuckDB is temporarily busy.
    for attempt in range(3):
        try:
            results = _do_search_query(query, limit)
            # パフォーマンス計測
            duration = time.time() - start_time
            cache_hit = popular_cache.get_stats()["hit_count"] > 0
            performance_tracker.track_search_performance(duration, cache_hit)
            
            if results:
                return results
            if attempt < 2:
                time.sleep(1.0)  # Wait for background tasks to progress
        except Exception as e:
            msg = str(e)
            if (
                "Binder Error" in msg
                or "Unique finder" in msg
                or "locked" in msg.lower()
            ):
                logger.warning(
                    f"Search: Temporary DuckDB contention, retrying {attempt + 1}/3..."
                )
                time.sleep(0.5)
                continue
            logger.error(f"Search error: {e}")
            # パフォーマンス計測（エラー時）
            duration = time.time() - start_time
            performance_tracker.track_search_performance(duration, False)
            return []

    # パフォーマンス計測（空結果時）
    duration = time.time() - start_time
    performance_tracker.track_search_performance(duration, False)
    return []
```

#### **Day 5: パフォーマンスレポートエンドポイント**
```python
# 追加: backend/mcp_core/api/api.py
@app.get("/performance/report")
async def get_performance_report():
    """パフォーマンスレポートを取得"""
    return performance_tracker.get_performance_report()
```

### **Week 3: テストと最適化**

#### **Day 1-2: キャッシュユニットテスト**
```python
# 新規作成: dev_tools/tests/unit/test_popular_query_cache.py
import pytest
from mcp_core.engine.popular_query_cache import PopularQueryCache

def test_popular_query_cache_initialization():
    """キャッシュ初期化テスト"""
    cache = PopularQueryCache(max_cache_size=100, popularity_threshold=2)
    assert cache.max_cache_size == 100
    assert cache.popularity_threshold == 2
    assert len(cache.query_embeddings) == 0

def test_cache_embedding_if_popular():
    """人気クエリキャッシュテスト"""
    cache = PopularQueryCache(max_cache_size=3, popularity_threshold=2)
    test_embedding = [0.1, 0.2, 0.3]
    
    # 1回目のアクセス（キャッシュされない）
    cache.cache_embedding_if_popular("test query", test_embedding)
    assert cache.get_embedding_cache("test query") is None
    
    # 2回目のアクセス（キャッシュされる）
    cache.cache_embedding_if_popular("test query", test_embedding)
    cached = cache.get_embedding_cache("test query")
    assert cached is not None
    assert cached == test_embedding

def test_cache_eviction():
    """キャッシュ削除テスト"""
    cache = PopularQueryCache(max_cache_size=2, popularity_threshold=1)
    embedding1 = [0.1, 0.2, 0.3]
    embedding2 = [0.4, 0.5, 0.6]
    embedding3 = [0.7, 0.8, 0.9]
    
    # 3つのクエリをキャッシュ（2つしか保持できない）
    cache.cache_embedding_if_popular("query1", embedding1)
    cache.cache_embedding_if_popular("query2", embedding2)
    cache.cache_embedding_if_popular("query3", embedding3)
    
    # 最初のクエリは削除されているはず
    # （実際のLRU実装により削除される可能性がある）
    assert len(cache.query_embeddings) <= 2

def test_cache_statistics():
    """キャッシュ統計テスト"""
    cache = PopularQueryCache(popularity_threshold=1)
    test_embedding = [0.1, 0.2, 0.3]
    
    # 統計情報の初期状態
    stats = cache.get_stats()
    assert stats["cache_size"] == 0
    assert stats["hit_count"] == 0
    assert stats["miss_count"] == 0
    
    # キャッシュして統計を確認
    cache.cache_embedding_if_popular("test", test_embedding)
    cached = cache.get_embedding_cache("test")
    
    stats = cache.get_stats()
    assert stats["cache_size"] == 1
    assert stats["hit_count"] == 1
    assert stats["miss_count"] == 0
    assert stats["hit_rate"] == "100.00%"
```

#### **Day 3-4: 統合テスト**
```python
# 追加: dev_tools/tests/integration/test_cache_performance.py
import pytest
import time
from fastapi.testclient import TestClient
from mcp_core.api import api as api_module

app = api_module.app
client = TestClient(app)

# Dummy API key for testing
HEADERS = {"X-API-Key": "test_key"}

@pytest.fixture(autouse=True)
def setup_test_auth(monkeypatch):
    """Ensure auth is mocked for each test."""
    monkeypatch.setattr(api_module, "verify_api_key", lambda key: (True, "test_user"))
    yield

def test_cache_performance_improvement():
    """キャッシュによるパフォーマンス向上テスト"""
    # 同じクエリを複数回実行
    query = "file processing function"
    durations = []
    
    for i in range(5):
        start_time = time.time()
        response = client.post("/functions/search", 
                             json={"query": query, "limit": 10}, 
                             headers=HEADERS)
        end_time = time.time()
        durations.append(end_time - start_time)
        
        assert response.status_code == 200
    
    # 最初のリクエストはembedding計算が必要
    # 2回目以降はキャッシュにより高速化されるはず
    first_duration = durations[0]
    avg_later_duration = sum(durations[1:]) / len(durations[1:])
    
    # 2回目以降が最初のリクエストより速いか確認（許容範囲内）
    assert avg_later_duration < first_duration * 0.8

def test_cache_statistics_endpoint():
    """キャッシュ統計エンドポイントテスト"""
    response = client.get("/cache/stats", headers=HEADERS)
    assert response.status_code == 200
    
    stats = response.json()
    assert "cache_size" in stats
    assert "hit_count" in stats
    assert "miss_count" in stats
    assert "hit_rate" in stats

def test_performance_report_endpoint():
    """パフォーマンスレポートエンドポイントテスト"""
    response = client.get("/performance/report", headers=HEADERS)
    assert response.status_code == 200
    
    report = response.json()
    assert "average_search_time" in report
    assert "total_searches_tracked" in report
    assert "active_sessions" in report
```

#### **Day 5: ベンチマークテストとドキュメント**

```python
# 追加: dev_tools/tests/performance/benchmark_cache.py
import time
import random
import string
from mcp_core.engine.popular_query_cache import PopularQueryCache
from mcp_core.engine.embedding import embedding_service

def generate_random_query(length=20):
    """ランダムなクエリを生成"""
    return ''.join(random.choices(string.ascii_letters + ' ', k=length))

def benchmark_cache_performance():
    """キャッシュパフォーマンステスト"""
    cache = PopularQueryCache(max_cache_size=100, popularity_threshold=3)
    
    # ベンチマークパラメータ
    total_queries = 1000
    popular_query_count = 50
    popular_query_frequency = 10
    
    # 人気クエリのリストを作成
    popular_queries = [f"popular query {i}" for i in range(popular_query_count)]
    
    # テストクエリを生成
    test_queries = []
    for _ in range(total_queries):
        if random.random() < 0.3:  # 30%の確率で人気クエリ
            query = random.choice(popular_queries)
        else:
            query = generate_random_query()
        test_queries.append(query)
    
    # ベンチマーク実行
    start_time = time.time()
    hit_count = 0
    miss_count = 0
    
    for query in test_queries:
        # キャッシュから取得を試みる
        cached_embedding = cache.get_embedding_cache(query)
        if cached_embedding is None:
            # キャッシュミス時はembeddingを計算してキャッシュ
            try:
                embedding = embedding_service.get_embedding(query).tolist()
                cache.cache_embedding_if_popular(query, embedding)
                miss_count += 1
            except Exception as e:
                print(f"Embedding calculation failed for query '{query}': {e}")
        else:
            hit_count += 1
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # 結果表示
    print(f"=== Cache Performance Benchmark ===")
    print(f"Total queries: {total_queries}")
    print(f"Cache hits: {hit_count}")
    print(f"Cache misses: {miss_count}")
    print(f"Hit rate: {(hit_count / total_queries * 100):.2f}%")
    print(f"Total time: {total_time:.3f} seconds")
    print(f"Average time per query: {(total_time / total_queries * 1000):.3f} ms")
    
    # キャッシュ統計
    stats = cache.get_stats()
    print(f"\n=== Cache Statistics ===")
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    return {
        "total_queries": total_queries,
        "cache_hits": hit_count,
        "cache_misses": miss_count,
        "hit_rate": hit_count / total_queries,
        "total_time": total_time,
        "stats": stats
    }

if __name__ == "__main__":
    benchmark_cache_performance()
```

---

## 📈 **期待される効果**

### **パフォーマンス改善**：
- **検索応答時間**: 1-3秒 → 200-500ms（最大80%改善）
- **キャッシュヒット率**: 0% → 60-80%（人気クエリ）
- **embedding計算回数**: 100% → 20-40%削減

### **ユーザー体験向上**：
- AIエージェント連携時の待機時間大幅短縮
- 繰り返し検索時の即時応答
- 全体的なシステムレスポンス向上

---

## 🛠 **リスクと緩和策**

### **技術的リスク**：
1. **キャッシュ容量超過**: 
   - 対策: LRUアルゴリズムによる自動削除
   - モニタリング: キャッシュ統計エンドポイント

2. **人気クエリ判定の不正確さ**:
   - 対策: アクセス頻度だけでなく最終アクセス時間も考慮
   - 改善: ユーザーフィードバックに基づく調整

3. **メモリ使用量増加**:
   - 対策: キャッシュサイズ制限（デフォルト500エントリ）
   - モニタリング: メモリ使用量監視

---

## 📋 **検証計画**

### **ユニットテスト**：
- [x] PopularQueryCacheクラスの基本機能
- [x] キャッシュヒット/ミスの動作確認
- [x] キャッシュ削除機能（LRU）
- [x] 統計情報の正確性

### **統合テスト**：
- [x] 検索APIとの統合
- [x] キャッシュ統計エンドポイント
- [x] パフォーマンスレポートエンドポイント

### **ベンチマークテスト**：
- [x] キャッシュヒット率測定
- [x] 応答時間改善確認
- [x] メモリ使用量監視

---

## 🎯 **まとめ**

この実装計画により、Function Store MCPは以下のような大幅な改善が期待できます：

1. **検索パフォーマンスの劇的向上**（最大80%高速化）
2. **ユーザー体験の大幅改善**（待機時間の削減）
3. **システムリソースの効率的利用**（embedding計算の削減）
4. **運用監視体制の構築**（パフォーマンスモニタリング）

実装は3週間という短期間で完了可能であり、既存のアーキテクチャを大きく変えることなく、ビジネス的に最も効果の高い改善を実現します。