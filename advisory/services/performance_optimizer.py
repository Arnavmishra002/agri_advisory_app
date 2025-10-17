#!/usr/bin/env python3
"""
Performance Optimization Module for Krishimitra AI
Implements caching, query optimization, and performance monitoring
"""

import os
import json
import logging
import time
import threading
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict, OrderedDict
import psutil
import redis
from django.core.cache import cache
from django.db import connection
from django.conf import settings
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.start_time = time.time()
        self.lock = threading.Lock()
    
    def record_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Record a performance metric"""
        with self.lock:
            self.metrics[metric_name].append({
                'value': value,
                'timestamp': time.time(),
                'tags': tags or {}
            })
    
    def get_metrics(self, metric_name: str = None, time_window: int = 3600) -> Dict[str, Any]:
        """Get performance metrics"""
        current_time = time.time()
        
        if metric_name:
            metrics = {metric_name: self.metrics.get(metric_name, [])}
        else:
            metrics = dict(self.metrics)
        
        # Filter by time window
        filtered_metrics = {}
        for name, values in metrics.items():
            filtered_values = [
                v for v in values 
                if current_time - v['timestamp'] <= time_window
            ]
            if filtered_values:
                filtered_metrics[name] = filtered_values
        
        return filtered_metrics
    
    def get_summary_stats(self, metric_name: str, time_window: int = 3600) -> Dict[str, float]:
        """Get summary statistics for a metric"""
        metrics = self.get_metrics(metric_name, time_window)
        values = [m['value'] for m in metrics.get(metric_name, [])]
        
        if not values:
            return {}
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'p95': sorted(values)[int(len(values) * 0.95)] if len(values) > 1 else values[0],
            'p99': sorted(values)[int(len(values) * 0.99)] if len(values) > 1 else values[0]
        }


class CacheManager:
    """Advanced caching manager with multiple backends"""
    
    def __init__(self):
        self.redis_client = None
        self.local_cache = OrderedDict()
        self.local_cache_size = 1000
        self.cache_stats = defaultdict(int)
        self.lock = threading.Lock()
        
        # Initialize Redis if available
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            redis_url = getattr(settings, 'REDIS_URL', None)
            if redis_url:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()  # Test connection
                logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"Redis not available, using local cache only: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        self.cache_stats['get_attempts'] += 1
        
        # Try Redis first
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    self.cache_stats['redis_hits'] += 1
                    return json.loads(value)
                self.cache_stats['redis_misses'] += 1
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        # Try local cache
        with self.lock:
            if key in self.local_cache:
                # Move to end (LRU)
                value = self.local_cache.pop(key)
                self.local_cache[key] = value
                self.cache_stats['local_hits'] += 1
                return value
            self.cache_stats['local_misses'] += 1
        
        return default
    
    def set(self, key: str, value: Any, timeout: int = 300):
        """Set value in cache"""
        self.cache_stats['set_attempts'] += 1
        
        # Set in Redis
        if self.redis_client:
            try:
                self.redis_client.setex(key, timeout, json.dumps(value))
            except Exception as e:
                logger.error(f"Redis set error: {e}")
        
        # Set in local cache
        with self.lock:
            if key in self.local_cache:
                self.local_cache.pop(key)
            elif len(self.local_cache) >= self.local_cache_size:
                # Remove oldest item (LRU)
                self.local_cache.popitem(last=False)
            
            self.local_cache[key] = value
    
    def delete(self, key: str):
        """Delete key from cache"""
        # Delete from Redis
        if self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
        
        # Delete from local cache
        with self.lock:
            if key in self.local_cache:
                del self.local_cache[key]
    
    def clear(self):
        """Clear all cache"""
        # Clear Redis
        if self.redis_client:
            try:
                self.redis_client.flushdb()
            except Exception as e:
                logger.error(f"Redis clear error: {e}")
        
        # Clear local cache
        with self.lock:
            self.local_cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_hits = self.cache_stats['redis_hits'] + self.cache_stats['local_hits']
        total_attempts = self.cache_stats['get_attempts']
        
        hit_rate = (total_hits / total_attempts * 100) if total_attempts > 0 else 0
        
        return {
            'hit_rate': hit_rate,
            'total_hits': total_hits,
            'total_misses': self.cache_stats['redis_misses'] + self.cache_stats['local_misses'],
            'redis_hits': self.cache_stats['redis_hits'],
            'redis_misses': self.cache_stats['redis_misses'],
            'local_hits': self.cache_stats['local_hits'],
            'local_misses': self.cache_stats['local_misses'],
            'local_cache_size': len(self.local_cache),
            'redis_available': self.redis_client is not None
        }


class QueryOptimizer:
    """Database query optimization"""
    
    def __init__(self):
        self.query_stats = defaultdict(int)
        self.slow_queries = []
        self.lock = threading.Lock()
    
    def optimize_queryset(self, queryset, select_related: List[str] = None, 
                         prefetch_related: List[str] = None):
        """Optimize queryset with select_related and prefetch_related"""
        if select_related:
            queryset = queryset.select_related(*select_related)
        
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)
        
        return queryset
    
    def log_query(self, query: str, execution_time: float):
        """Log query execution time"""
        with self.lock:
            self.query_stats['total_queries'] += 1
            self.query_stats['total_time'] += execution_time
            
            if execution_time > 1.0:  # Log slow queries (> 1 second)
                self.slow_queries.append({
                    'query': query,
                    'execution_time': execution_time,
                    'timestamp': datetime.now().isoformat()
                })
    
    def get_query_stats(self) -> Dict[str, Any]:
        """Get query statistics"""
        total_queries = self.query_stats['total_queries']
        total_time = self.query_stats['total_time']
        
        return {
            'total_queries': total_queries,
            'total_time': total_time,
            'avg_time': total_time / total_queries if total_queries > 0 else 0,
            'slow_queries_count': len(self.slow_queries),
            'slow_queries': self.slow_queries[-10:]  # Last 10 slow queries
        }


class AsyncTaskManager:
    """Async task management for concurrent operations"""
    
    def __init__(self, max_workers: int = 10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_tasks = {}
        self.task_results = {}
        self.lock = threading.Lock()
    
    async def run_concurrent_tasks(self, tasks: List[Callable], timeout: int = 30) -> List[Any]:
        """Run multiple tasks concurrently"""
        async def run_task(task):
            try:
                if asyncio.iscoroutinefunction(task):
                    return await asyncio.wait_for(task(), timeout=timeout)
                else:
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(self.executor, task)
            except Exception as e:
                logger.error(f"Task execution error: {e}")
                return None
        
        results = await asyncio.gather(*[run_task(task) for task in tasks], return_exceptions=True)
        return results
    
    def submit_task(self, task_id: str, task_func: Callable, *args, **kwargs):
        """Submit a task for background execution"""
        future = self.executor.submit(task_func, *args, **kwargs)
        
        with self.lock:
            self.active_tasks[task_id] = future
        
        return future
    
    def get_task_result(self, task_id: str) -> Any:
        """Get result of a completed task"""
        with self.lock:
            if task_id in self.active_tasks:
                future = self.active_tasks[task_id]
                if future.done():
                    result = future.result()
                    self.task_results[task_id] = result
                    del self.active_tasks[task_id]
                    return result
            elif task_id in self.task_results:
                return self.task_results[task_id]
        
        return None


def performance_monitor(metric_name: str = None, tags: Dict[str, str] = None):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Record metric
                monitor_name = metric_name or f"{func.__module__}.{func.__name__}"
                performance_monitor.instance.record_metric(monitor_name, execution_time, tags)
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                error_tags = (tags or {}).copy()
                error_tags['error'] = str(type(e).__name__)
                
                monitor_name = metric_name or f"{func.__module__}.{func.__name__}"
                performance_monitor.instance.record_metric(monitor_name, execution_time, error_tags)
                
                raise
        
        return wrapper
    return decorator


def cache_result(timeout: int = 300, key_func: Callable = None):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__module__}.{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = cache_result.cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_result.cache_manager.set(cache_key, result, timeout)
            
            return result
        
        return wrapper
    return decorator


def optimize_database_queries(select_related: List[str] = None, prefetch_related: List[str] = None):
    """Decorator to optimize database queries"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # This would be implemented to automatically optimize querysets
            # For now, it's a placeholder for the concept
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


class PerformanceOptimizer:
    """Main performance optimization class"""
    
    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.cache_manager = CacheManager()
        self.query_optimizer = QueryOptimizer()
        self.task_manager = AsyncTaskManager()
        
        # Set up decorator instances
        performance_monitor.instance = self.monitor
        cache_result.cache_manager = self.cache_manager
        
        logger.info("Performance optimizer initialized")
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network I/O
            network = psutil.net_io_counters()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu': {
                    'usage_percent': cpu_percent,
                    'count': psutil.cpu_count()
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'used': memory.used,
                    'percent': memory.percent
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                },
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                }
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {'error': str(e)}
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        return {
            'timestamp': datetime.now().isoformat(),
            'system_metrics': self.get_system_metrics(),
            'cache_stats': self.cache_manager.get_stats(),
            'query_stats': self.query_optimizer.get_query_stats(),
            'performance_metrics': self.monitor.get_metrics()
        }
    
    def optimize_api_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize API response by removing unnecessary data"""
        # Remove large or unnecessary fields
        optimized_data = response_data.copy()
        
        # Remove debug information in production
        if not settings.DEBUG:
            optimized_data.pop('debug_info', None)
            optimized_data.pop('internal_data', None)
        
        # Compress large arrays
        if 'crop_recommendations' in optimized_data:
            recommendations = optimized_data['crop_recommendations']
            if isinstance(recommendations, list) and len(recommendations) > 10:
                optimized_data['crop_recommendations'] = recommendations[:10]
                optimized_data['total_recommendations'] = len(recommendations)
        
        return optimized_data
    
    def batch_process_requests(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple requests in batches for better performance"""
        batch_size = 10
        results = []
        
        for i in range(0, len(requests), batch_size):
            batch = requests[i:i + batch_size]
            
            # Process batch concurrently
            tasks = [self._process_single_request(req) for req in batch]
            batch_results = asyncio.run(self.task_manager.run_concurrent_tasks(tasks))
            
            results.extend(batch_results)
        
        return results
    
    async def _process_single_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single request (placeholder)"""
        # This would implement actual request processing
        await asyncio.sleep(0.1)  # Simulate processing time
        return {'processed': True, 'request_id': request.get('id')}
    
    def cleanup_old_data(self, days: int = 7):
        """Clean up old performance data"""
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        # Clean up old metrics
        for metric_name in list(self.monitor.metrics.keys()):
            self.monitor.metrics[metric_name] = [
                m for m in self.monitor.metrics[metric_name]
                if m['timestamp'] > cutoff_time
            ]
        
        # Clean up old slow queries
        self.query_optimizer.slow_queries = [
            q for q in self.query_optimizer.slow_queries
            if datetime.fromisoformat(q['timestamp']).timestamp() > cutoff_time
        ]
        
        logger.info(f"Cleaned up performance data older than {days} days")


# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()


# Convenience functions
def monitor_performance(metric_name: str = None, tags: Dict[str, str] = None):
    """Monitor function performance"""
    return performance_monitor(metric_name, tags)


def cache_function_result(timeout: int = 300, key_func: Callable = None):
    """Cache function result"""
    return cache_result(timeout, key_func)


def optimize_queries(select_related: List[str] = None, prefetch_related: List[str] = None):
    """Optimize database queries"""
    return optimize_database_queries(select_related, prefetch_related)


# Example usage decorators
@monitor_performance('api_response_time')
@cache_function_result(timeout=600)
def get_crop_recommendations_optimized(location: str, **kwargs):
    """Example of optimized crop recommendations function"""
    # This would contain the actual implementation
    pass


@monitor_performance('database_query_time')
@optimize_queries(select_related=['user'], prefetch_related=['crops'])
def get_user_crops_optimized(user_id: str):
    """Example of optimized database query function"""
    # This would contain the actual implementation
    pass







