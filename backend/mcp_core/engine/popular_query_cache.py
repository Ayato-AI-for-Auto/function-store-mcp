import hashlib
import logging
import time
from collections import Counter
from typing import Dict, List, Optional

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
        """人気度の低いキャッシュを削除"""
        if not self.last_accessed:
            return

        oldest_hash = min(
            self.last_accessed.keys(), key=lambda h: self.last_accessed[h]
        )
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
            "total_queries": len(self.query_frequency),
        }
