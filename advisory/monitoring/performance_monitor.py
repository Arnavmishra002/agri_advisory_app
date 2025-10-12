#!/usr/bin/env python3
"""
Performance Monitoring System
Monitors system performance, API response times, and user metrics
"""

import time
import logging
import json
import psutil
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from django.db import connection
from django.utils import timezone

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    Performance monitoring system for the agricultural advisory application
    Tracks API performance, system metrics, and user behavior
    """
    
    def __init__(self):
        """Initialize the performance monitor"""
        self.metrics_cache = {}
        self.alert_thresholds = {
            'response_time_ms': 2000,  # 2 seconds
            'cpu_percent': 80,         # 80% CPU usage
            'memory_percent': 85,      # 85% memory usage
            'error_rate_percent': 5,   # 5% error rate
            'api_requests_per_minute': 1000  # 1000 requests per minute
        }
        
        # Metrics storage configuration
        self.metrics_retention = {
            'api_metrics': 7,      # 7 days
            'system_metrics': 1,   # 1 day
            'user_metrics': 30     # 30 days
        }
    
    def start_api_timing(self, endpoint: str, method: str = 'GET') -> str:
        """
        Start timing an API request
        
        Args:
            endpoint: API endpoint being called
            method: HTTP method
            
        Returns:
            Timing ID for tracking
        """
        timing_id = f"{endpoint}_{method}_{int(time.time() * 1000)}"
        
        # Store start time
        self.metrics_cache[f"start_{timing_id}"] = {
            'endpoint': endpoint,
            'method': method,
            'start_time': time.time(),
            'timestamp': datetime.now().isoformat()
        }
        
        return timing_id
    
    def end_api_timing(self, timing_id: str, status_code: int = 200, 
                      error_message: str = None) -> Dict[str, Any]:
        """
        End timing an API request and record metrics
        
        Args:
            timing_id: Timing ID from start_api_timing
            status_code: HTTP status code
            error_message: Error message if any
            
        Returns:
            API metrics dictionary
        """
        try:
            start_data = self.metrics_cache.get(f"start_{timing_id}")
            if not start_data:
                logger.warning(f"No start data found for timing ID: {timing_id}")
                return {}
            
            end_time = time.time()
            response_time = (end_time - start_data['start_time']) * 1000  # Convert to milliseconds
            
            # Create metrics record
            metrics = {
                'endpoint': start_data['endpoint'],
                'method': start_data['method'],
                'response_time_ms': round(response_time, 2),
                'status_code': status_code,
                'timestamp': start_data['timestamp'],
                'end_timestamp': datetime.now().isoformat(),
                'success': status_code < 400,
                'error_message': error_message
            }
            
            # Store metrics
            self._store_api_metrics(metrics)
            
            # Check for performance alerts
            self._check_performance_alerts(metrics)
            
            # Clean up cache
            del self.metrics_cache[f"start_{timing_id}"]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error ending API timing: {e}")
            return {}
    
    def record_system_metrics(self) -> Dict[str, Any]:
        """
        Record current system metrics
        
        Returns:
            System metrics dictionary
        """
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network I/O
            network = psutil.net_io_counters()
            
            # Database connections
            db_connections = len(connection.queries)
            
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': round(cpu_percent, 2),
                'memory_percent': round(memory_percent, 2),
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_percent': round(disk_percent, 2),
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'db_connections': db_connections,
                'active_threads': psutil.Process().num_threads(),
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            }
            
            # Store metrics
            self._store_system_metrics(metrics)
            
            # Check for system alerts
            self._check_system_alerts(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error recording system metrics: {e}")
            return {}
    
    def record_user_activity(self, user_id: str, activity_type: str, 
                           details: Dict[str, Any] = None) -> None:
        """
        Record user activity for analytics
        
        Args:
            user_id: User identifier
            activity_type: Type of activity (login, api_call, etc.)
            details: Additional activity details
        """
        try:
            activity = {
                'user_id': user_id,
                'activity_type': activity_type,
                'timestamp': datetime.now().isoformat(),
                'details': details or {},
                'ip_address': self._get_client_ip(),
                'user_agent': self._get_user_agent()
            }
            
            # Store user activity
            self._store_user_activity(activity)
            
        except Exception as e:
            logger.error(f"Error recording user activity: {e}")
    
    def get_api_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get API performance summary for the last N hours
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Performance summary dictionary
        """
        try:
            # Get API metrics from cache/database
            api_metrics = self._get_api_metrics(hours)
            
            if not api_metrics:
                return {'message': 'No metrics available'}
            
            # Calculate summary statistics
            response_times = [m['response_time_ms'] for m in api_metrics]
            status_codes = [m['status_code'] for m in api_metrics]
            endpoints = [m['endpoint'] for m in api_metrics]
            
            summary = {
                'time_period_hours': hours,
                'total_requests': len(api_metrics),
                'average_response_time_ms': round(sum(response_times) / len(response_times), 2),
                'min_response_time_ms': min(response_times),
                'max_response_time_ms': max(response_times),
                'success_rate_percent': round((len([s for s in status_codes if s < 400]) / len(status_codes)) * 100, 2),
                'error_rate_percent': round((len([s for s in status_codes if s >= 400]) / len(status_codes)) * 100, 2),
                'top_endpoints': self._get_top_endpoints(endpoints),
                'status_code_distribution': self._get_status_code_distribution(status_codes),
                'hourly_breakdown': self._get_hourly_breakdown(api_metrics)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting API performance summary: {e}")
            return {'error': str(e)}
    
    def get_system_health_status(self) -> Dict[str, Any]:
        """
        Get current system health status
        
        Returns:
            System health status dictionary
        """
        try:
            # Get latest system metrics
            system_metrics = self.record_system_metrics()
            
            # Determine health status
            health_status = 'healthy'
            alerts = []
            
            if system_metrics['cpu_percent'] > self.alert_thresholds['cpu_percent']:
                health_status = 'warning'
                alerts.append(f"High CPU usage: {system_metrics['cpu_percent']}%")
            
            if system_metrics['memory_percent'] > self.alert_thresholds['memory_percent']:
                health_status = 'warning'
                alerts.append(f"High memory usage: {system_metrics['memory_percent']}%")
            
            if system_metrics['disk_percent'] > 90:
                health_status = 'critical'
                alerts.append(f"Low disk space: {system_metrics['disk_percent']}% used")
            
            # Get recent API performance
            api_summary = self.get_api_performance_summary(hours=1)
            
            if api_summary.get('error_rate_percent', 0) > self.alert_thresholds['error_rate_percent']:
                health_status = 'warning'
                alerts.append(f"High error rate: {api_summary['error_rate_percent']}%")
            
            return {
                'status': health_status,
                'timestamp': datetime.now().isoformat(),
                'system_metrics': system_metrics,
                'api_summary': api_summary,
                'alerts': alerts,
                'uptime_seconds': time.time() - psutil.Process().create_time()
            }
            
        except Exception as e:
            logger.error(f"Error getting system health status: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _store_api_metrics(self, metrics: Dict[str, Any]) -> None:
        """Store API metrics in cache/database"""
        try:
            # Store in cache for quick access
            cache_key = f"api_metrics:{int(time.time())}"
            cache.set(cache_key, metrics, timeout=3600 * 24)  # 24 hours
            
            # Also store in a list for aggregation
            metrics_list_key = "api_metrics_list"
            metrics_list = cache.get(metrics_list_key, [])
            metrics_list.append(metrics)
            
            # Keep only last 1000 entries
            if len(metrics_list) > 1000:
                metrics_list = metrics_list[-1000:]
            
            cache.set(metrics_list_key, metrics_list, timeout=3600 * 24)
            
        except Exception as e:
            logger.error(f"Error storing API metrics: {e}")
    
    def _store_system_metrics(self, metrics: Dict[str, Any]) -> None:
        """Store system metrics"""
        try:
            cache_key = f"system_metrics:{int(time.time())}"
            cache.set(cache_key, metrics, timeout=3600)  # 1 hour
            
        except Exception as e:
            logger.error(f"Error storing system metrics: {e}")
    
    def _store_user_activity(self, activity: Dict[str, Any]) -> None:
        """Store user activity"""
        try:
            cache_key = f"user_activity:{activity['user_id']}:{int(time.time())}"
            cache.set(cache_key, activity, timeout=3600 * 24 * 30)  # 30 days
            
        except Exception as e:
            logger.error(f"Error storing user activity: {e}")
    
    def _get_api_metrics(self, hours: int) -> List[Dict[str, Any]]:
        """Get API metrics for the last N hours"""
        try:
            metrics_list = cache.get("api_metrics_list", [])
            cutoff_time = time.time() - (hours * 3600)
            
            # Filter metrics by timestamp
            filtered_metrics = []
            for metrics in metrics_list:
                try:
                    timestamp = datetime.fromisoformat(metrics['timestamp'])
                    if timestamp.timestamp() > cutoff_time:
                        filtered_metrics.append(metrics)
                except Exception:
                    continue
            
            return filtered_metrics
            
        except Exception as e:
            logger.error(f"Error getting API metrics: {e}")
            return []
    
    def _check_performance_alerts(self, metrics: Dict[str, Any]) -> None:
        """Check for performance alerts"""
        try:
            if metrics['response_time_ms'] > self.alert_thresholds['response_time_ms']:
                logger.warning(f"Slow API response: {metrics['endpoint']} took {metrics['response_time_ms']}ms")
            
            if not metrics['success']:
                logger.warning(f"API error: {metrics['endpoint']} returned {metrics['status_code']}")
                
        except Exception as e:
            logger.error(f"Error checking performance alerts: {e}")
    
    def _check_system_alerts(self, metrics: Dict[str, Any]) -> None:
        """Check for system alerts"""
        try:
            if metrics['cpu_percent'] > self.alert_thresholds['cpu_percent']:
                logger.warning(f"High CPU usage: {metrics['cpu_percent']}%")
            
            if metrics['memory_percent'] > self.alert_thresholds['memory_percent']:
                logger.warning(f"High memory usage: {metrics['memory_percent']}%")
                
        except Exception as e:
            logger.error(f"Error checking system alerts: {e}")
    
    def _get_top_endpoints(self, endpoints: List[str]) -> List[Dict[str, Any]]:
        """Get top endpoints by request count"""
        from collections import Counter
        endpoint_counts = Counter(endpoints)
        return [{'endpoint': endpoint, 'count': count} 
                for endpoint, count in endpoint_counts.most_common(10)]
    
    def _get_status_code_distribution(self, status_codes: List[int]) -> Dict[str, int]:
        """Get status code distribution"""
        from collections import Counter
        return dict(Counter(status_codes))
    
    def _get_hourly_breakdown(self, metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get hourly breakdown of requests"""
        from collections import defaultdict
        
        hourly_data = defaultdict(list)
        
        for metric in metrics:
            try:
                timestamp = datetime.fromisoformat(metric['timestamp'])
                hour_key = timestamp.strftime('%Y-%m-%d %H:00')
                hourly_data[hour_key].append(metric)
            except Exception:
                continue
        
        breakdown = []
        for hour, hour_metrics in hourly_data.items():
            response_times = [m['response_time_ms'] for m in hour_metrics]
            breakdown.append({
                'hour': hour,
                'request_count': len(hour_metrics),
                'average_response_time': round(sum(response_times) / len(response_times), 2),
                'success_rate': round((len([m for m in hour_metrics if m['success']]) / len(hour_metrics)) * 100, 2)
            })
        
        return sorted(breakdown, key=lambda x: x['hour'])
    
    def _get_client_ip(self) -> Optional[str]:
        """Get client IP address (placeholder)"""
        # This would be implemented to get the actual client IP
        return "127.0.0.1"
    
    def _get_user_agent(self) -> Optional[str]:
        """Get user agent (placeholder)"""
        # This would be implemented to get the actual user agent
        return "Krishimitra AI"


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


# Decorator for automatic API monitoring
def monitor_api_performance(endpoint_name: str = None):
    """
    Decorator to automatically monitor API performance
    
    Args:
        endpoint_name: Name of the endpoint for monitoring
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # Start timing
            endpoint = endpoint_name or request.path
            timing_id = performance_monitor.start_api_timing(endpoint, request.method)
            
            try:
                # Execute the view
                response = view_func(request, *args, **kwargs)
                
                # End timing with success
                performance_monitor.end_api_timing(
                    timing_id, 
                    status_code=response.status_code
                )
                
                return response
                
            except Exception as e:
                # End timing with error
                performance_monitor.end_api_timing(
                    timing_id, 
                    status_code=500,
                    error_message=str(e)
                )
                raise
                
        return wrapper
    return decorator


# Utility functions
def get_performance_summary() -> Dict[str, Any]:
    """Get comprehensive performance summary"""
    return {
        'api_performance': performance_monitor.get_api_performance_summary(),
        'system_health': performance_monitor.get_system_health_status(),
        'timestamp': datetime.now().isoformat()
    }


def record_user_activity(user_id: str, activity_type: str, details: Dict[str, Any] = None):
    """Record user activity"""
    performance_monitor.record_user_activity(user_id, activity_type, details)

