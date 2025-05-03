"""
Comprehensive caching system with multiple cache levels
"""
import os
import json
import time
import hashlib
from typing import Dict, Any, Optional, List, Tuple

from cachetools import TTLCache
from diskcache import Cache

from config.settings import CACHE_DIR, CACHE_TTL

class CacheManager:
    """Manages multi-level caching for improved performance"""
    
    def __init__(self):
        # Create cache directories
        self.cache_base = CACHE_DIR
        self.video_cache_dir = os.path.join(self.cache_base, "videos")
        self.query_cache_dir = os.path.join(self.cache_base, "queries")
        
        for dir_path in [self.video_cache_dir, self.query_cache_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # Memory cache (fastest, limited size)
        self.memory_cache = TTLCache(maxsize=1000, ttl=CACHE_TTL)
        
        # Disk cache (slower, persistent)
        self.disk_cache = Cache(os.path.join(self.cache_base, "diskcache"))
        
        # Track embeddings for semantic similarity
        self.embedding_cache = {}
        
    def has_processed_video(self, video_id: str) -> bool:
        """
        Check if a video has been processed and cached
        
        Args:
            video_id: Unique video identifier
            
        Returns:
            True if video is cached and valid
        """
        # Check memory cache first (fastest)
        memory_key = f"video_processed:{video_id}"
        if memory_key in self.memory_cache:
            return True
            
        # Check disk cache next
        if self.disk_cache.get(memory_key, default=None):
            # Refresh memory cache
            self.memory_cache[memory_key] = True
            return True
            
        # Finally check file cache
        video_path = os.path.join(self.video_cache_dir, f"{video_id}.json")
        if not os.path.exists(video_path):
            return False
            
        # Check if cache is still valid
        try:
            with open(video_path, 'r') as f:
                data = json.load(f)
                
            cache_time = data.get('timestamp', 0)
            is_valid = (time.time() - cache_time) < CACHE_TTL
            
            # Update memory cache with result
            if is_valid:
                self.memory_cache[memory_key] = True
                self.disk_cache.set(memory_key, True, expire=CACHE_TTL)
                
            return is_valid
        except:
            return False
        
    def mark_video_processed(self, video_id: str) -> None:
        """
        Mark a video as processed in cache
        
        Args:
            video_id: Unique video identifier
        """
        # Update all cache levels
        memory_key = f"video_processed:{video_id}"
        self.memory_cache[memory_key] = True
        self.disk_cache.set(memory_key, True, expire=CACHE_TTL)
        
        # Update file cache
        video_path = os.path.join(self.video_cache_dir, f"{video_id}.json")
        with open(video_path, 'w') as f:
            json.dump({
                'video_id': video_id,
                'timestamp': time.time(),
                'processed': True
            }, f)
    
    def get_cached_response(self, video_id: str, query: str) -> Optional[str]:
        """
        Get cached response for a query
        
        Args:
            video_id: Unique video identifier
            query: User query
            
        Returns:
            Cached response or None if not found
        """
        # Normalize query (lowercase, remove extra whitespace)
        normalized_query = ' '.join(query.lower().split())
        
        # Create cache keys
        query_hash = self._hash_query(normalized_query)
        memory_key = f"query:{video_id}:{query_hash}"
        
        # Check memory cache first (fastest)
        if memory_key in self.memory_cache:
            return self.memory_cache[memory_key]
            
        # Check disk cache next
        disk_result = self.disk_cache.get(memory_key, default=None)
        if disk_result:
            # Refresh memory cache
            self.memory_cache[memory_key] = disk_result
            return disk_result
            
        # Finally check file cache
        query_path = os.path.join(self.query_cache_dir, f"{video_id}_{query_hash}.json")
        if not os.path.exists(query_path):
            return self._check_similar_queries(video_id, normalized_query)
            
        # Load from file cache
        try:
            with open(query_path, 'r') as f:
                data = json.load(f)
                
            cache_time = data.get('timestamp', 0)
            if (time.time() - cache_time) < CACHE_TTL:
                response = data.get('response', None)
                
                # Update faster caches
                if response:
                    self.memory_cache[memory_key] = response
                    self.disk_cache.set(memory_key, response, expire=CACHE_TTL)
                    
                return response
        except:
            pass
            
        # No valid cache found
        return self._check_similar_queries(video_id, normalized_query)
    
    def _check_similar_queries(self, video_id: str, query: str) -> Optional[str]:
        """
        Check for responses to similar queries
        
        Args:
            video_id: Unique video identifier
            query: Normalized query
            
        Returns:
            Response for similar query or None
        """
        # Simple similarity check based on word overlap
        # In a real implementation, you would use embeddings here
        
        try:
            # Get all cached queries for this video
            query_files = [f for f in os.listdir(self.query_cache_dir) 
                         if f.startswith(f"{video_id}_") and f.endswith(".json")]
            
            # Extract query text from each file
            cached_queries = []
            for qf in query_files:
                try:
                    with open(os.path.join(self.query_cache_dir, qf), 'r') as f:
                        data = json.load(f)
                        original_query = data.get('query', '')
                        response = data.get('response', '')
                        timestamp = data.get('timestamp', 0)
                        
                        # Skip expired items
                        if (time.time() - timestamp) >= CACHE_TTL:
                            continue
                            
                        if original_query and response:
                            cached_queries.append((original_query, response, qf))
                except:
                    continue
            
            # Find the most similar query
            if cached_queries:
                query_words = set(query.split())
                best_match = None
                best_score = 0.5  # Threshold for similarity
                
                for cached_query, response, filename in cached_queries:
                    cached_words = set(cached_query.lower().split())
                    
                    # Calculate Jaccard similarity
                    if not cached_words or not query_words:
                        continue
                        
                    intersection = len(query_words.intersection(cached_words))
                    union = len(query_words.union(cached_words))
                    
                    if union > 0:
                        similarity = intersection / union
                        if similarity > best_score:
                            best_score = similarity
                            best_match = (cached_query, response)
                
                if best_match:
                    return best_match[1]
        except Exception as e:
            print(f"Error in similar query check: {e}")
            
        return None
    
    def cache_response(self, video_id: str, query: str, response: str) -> None:
        """
        Cache a query response
        
        Args:
            video_id: Unique video identifier
            query: User query
            response: Response to cache
        """
        # Normalize query
        normalized_query = ' '.join(query.lower().split())
        
        # Create cache keys
        query_hash = self._hash_query(normalized_query)
        memory_key = f"query:{video_id}:{query_hash}"
        
        # Update all cache levels
        self.memory_cache[memory_key] = response
        self.disk_cache.set(memory_key, response, expire=CACHE_TTL)
        
        # Update file cache
        query_path = os.path.join(self.query_cache_dir, f"{video_id}_{query_hash}.json")
        with open(query_path, 'w') as f:
            json.dump({
                'video_id': video_id,
                'query': normalized_query,
                'response': response,
                'timestamp': time.time()
            }, f)
    
    def _hash_query(self, query: str) -> str:
        """
        Create a hash of the query for file naming
        
        Args:
            query: Query to hash
            
        Returns:
            Hash string
        """
        return hashlib.md5(query.encode()).hexdigest()
