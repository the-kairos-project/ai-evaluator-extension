"""
Performance tracking utilities for measuring operation timings.

This module provides a simple performance tracker that collects timing
metrics throughout an operation and logs them as a single summary line.
"""

import time
from typing import Dict, Optional, Any
from contextlib import asynccontextmanager
import logging


class PerformanceTracker:
    """Tracks performance metrics for an operation and logs a summary."""
    
    def __init__(self, operation_name: str):
        """Initialize the performance tracker.
        
        Args:
            operation_name: Name of the operation being tracked
        """
        self.operation_name = operation_name
        self.timings: Dict[str, float] = {}
        self.metadata: Dict[str, Any] = {}
        self.start_time = time.time()
        
    def record_duration(self, phase_name: str, duration: float) -> None:
        """Record the duration of a specific phase.
        
        Args:
            phase_name: Name of the phase (e.g., "plugin_init", "mcp_session")
            duration: Duration in seconds
        """
        self.timings[phase_name] = round(duration, 2)
        
    def record_phase_start(self, phase_name: str) -> float:
        """Record the start of a phase and return the start time.
        
        Args:
            phase_name: Name of the phase
            
        Returns:
            The start time for this phase
        """
        return time.time()
        
    def record_phase_end(self, phase_name: str, start_time: float) -> None:
        """Record the end of a phase using its start time.
        
        Args:
            phase_name: Name of the phase
            start_time: When the phase started (from record_phase_start)
        """
        duration = time.time() - start_time
        self.record_duration(phase_name, duration)
        
    def add_metadata(self, **kwargs) -> None:
        """Add metadata fields to be included in the summary.
        
        Args:
            **kwargs: Key-value pairs to include in the log
        """
        self.metadata.update(kwargs)
        
    def get_total_time(self) -> float:
        """Get the total elapsed time since tracker creation."""
        return round(time.time() - self.start_time, 2)
        
    def log_summary(self, logger: logging.Logger, level: int = logging.INFO) -> None:
        """Log a single-line summary of all collected metrics.
        
        Args:
            logger: Logger instance to use
            level: Logging level (default: INFO)
        """
        total_time = self.get_total_time()
        
        # Build the timing breakdown string
        timing_parts = [f"{k}={v}s" for k, v in sorted(self.timings.items())]
        timing_str = " | ".join(timing_parts) if timing_parts else "no_breakdown"
        
        # Build the metadata string
        metadata_parts = [f"{k}={v}" for k, v in sorted(self.metadata.items())]
        metadata_str = " | ".join(metadata_parts) if metadata_parts else ""
        
        # Construct the final log message
        message_parts = [
            f"{self.operation_name} completed",
            f"total_time={total_time}s"
        ]
        
        if timing_str != "no_breakdown":
            message_parts.append(timing_str)
            
        if metadata_str:
            message_parts.append(metadata_str)
            
        message = " | ".join(message_parts)
        logger.log(level, message)


@asynccontextmanager
async def track_async_operation(operation_name: str, logger: logging.Logger):
    """Async context manager for tracking an operation's performance.
    
    Usage:
        async with track_async_operation("linkedin_scrape", logger) as tracker:
            tracker.add_metadata(user="john-doe")
            # ... do work ...
            tracker.record_duration("network_call", 1.5)
    
    Args:
        operation_name: Name of the operation
        logger: Logger to use for the summary
        
    Yields:
        PerformanceTracker instance
    """
    tracker = PerformanceTracker(operation_name)
    try:
        yield tracker
    finally:
        tracker.log_summary(logger)


def track_operation(operation_name: str, logger: logging.Logger):
    """Context manager for tracking a synchronous operation's performance.
    
    Usage:
        with track_operation("data_processing", logger) as tracker:
            tracker.add_metadata(items=100)
            # ... do work ...
            tracker.record_duration("validation", 0.5)
    
    Args:
        operation_name: Name of the operation
        logger: Logger to use for the summary
        
    Yields:
        PerformanceTracker instance
    """
    tracker = PerformanceTracker(operation_name)
    try:
        yield tracker
    finally:
        tracker.log_summary(logger)