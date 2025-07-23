"""
External MCP Process Management.

This module handles the lifecycle management of external MCP server processes,
including starting, stopping, and monitoring their health.
"""

import asyncio
import subprocess
import time
from typing import List, Optional
from pathlib import Path
from src.utils.logging import get_structured_logger

from .external_mcp_client import ExternalMCPClient
from src.core.protocol.mcp_constants import (
    DEFAULT_MCP_HOST,
    DEFAULT_MCP_PORT,
    DEFAULT_STARTUP_TIMEOUT,
)

logger = get_structured_logger(__name__)


class ExternalMCPProcess:
    """Manages an external MCP server process."""
    
    def __init__(
        self,
        server_path: Path,
        server_args: List[str],
        host: str = DEFAULT_MCP_HOST,
        port: int = DEFAULT_MCP_PORT,
        startup_timeout: int = DEFAULT_STARTUP_TIMEOUT
    ):
        """Initialize the external MCP process manager.
        
        Args:
            server_path: Path to the server executable/script
            server_args: Arguments to pass to the server
            host: Host to bind the server to
            port: Port to bind the server to
            startup_timeout: Timeout for server startup
        """
        self.server_path = server_path
        self.server_args = server_args
        self.host = host
        self.port = port
        self.startup_timeout = startup_timeout
        self.process: Optional[subprocess.Popen] = None
        self.server_url = f"http://{host}:{port}"
        
    async def start(self) -> bool:
        """Start the external MCP server process.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        if self.process and self.process.poll() is None:
            logger.info("External MCP server already running")
            return True
            
        try:
            # Build command - use python to run the script
            cmd = [
                "python",
                str(self.server_path),
                *self.server_args,
                "--transport", "streamable-http",
                "--host", self.host,
                "--port", str(self.port)
            ]
            
            logger.info("Starting external MCP server", cmd=cmd)
            
            # Start process with correct working directory
            cwd = self.server_path.parent
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(cwd)
            )
            
            # Wait for server to be ready
            client = ExternalMCPClient(self.server_url)
            start_time = time.time()
            
            while time.time() - start_time < self.startup_timeout:
                if await client.health_check():
                    logger.info("External MCP server started successfully")
                    await client.close()
                    return True
                    
                # Check if process died
                if self.process.poll() is not None:
                    stdout, stderr = self.process.communicate()
                    logger.error(
                        "External MCP server process died",
                        stdout=stdout,
                        stderr=stderr
                    )
                    await client.close()
                    return False
                    
                await asyncio.sleep(1)
            
            await client.close()
            logger.error("External MCP server startup timeout")
            await self.stop()
            return False
            
        except Exception as e:
            logger.error("Failed to start external MCP server", error=str(e))
            return False
    
    async def stop(self) -> None:
        """Stop the external MCP server process.
        
        This method gracefully stops the running process:
        1. Sends SIGTERM signal for graceful shutdown
        2. Waits up to 5 seconds for the process to exit
        3. Forces termination with SIGKILL if needed
        4. Cleans up process resources
        
        Safe to call multiple times - no-op if process not running.
        """
        if self.process and self.process.returncode is None:
            logger.info("Stopping external MCP process", pid=self.process.pid)
            
            try:
                # Try graceful shutdown first
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
                logger.info("External MCP process stopped gracefully")
            except asyncio.TimeoutError:
                # Force kill if graceful shutdown fails
                logger.warning("Graceful shutdown timed out, forcing termination")
                self.process.kill()
                await self.process.wait()
            except Exception as e:
                logger.error("Error stopping process", error=str(e))
            
            self.process = None
    
    def is_running(self) -> bool:
        """Check if the external MCP server process is running.
        
        Returns:
            bool: True if running, False otherwise
        """
        return self.process is not None and self.process.poll() is None 