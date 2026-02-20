import logging
import threading
from multiprocessing.connection import Client, Listener
from typing import Any, Tuple

logger = logging.getLogger(__name__)

# Windows Named Pipe Path
IPC_PATH = r"\\.\pipe\fstore_mcp"


class IPCManager:
    """
    Manages lightweight Inter-Process Communication (IPC) using Named Pipes.
    Handles role election (Master vs Proxy) and message passing.
    """

    def __init__(self):
        self.role = None
        self.connection = None
        self.listener = None
        self._stop_event = threading.Event()

    def determine_role(self) -> Tuple[str, Any]:
        """
        Determines if the current process should be a Master or a Proxy.
        Returns (role, connection/listener).
        """
        try:
            # Try to connect as a Client (Proxy)
            conn = Client(IPC_PATH, "AF_PIPE")
            self.role = "PROXY"
            self.connection = conn
            logger.info("IPCManager: Connected to existing Master (Role: PROXY)")
            return self.role, self.connection
        except Exception:
            # Connection failed -> Try to become the Master (Listener)
            try:
                self.listener = Listener(IPC_PATH, "AF_PIPE")
                self.role = "MASTER"
                logger.info(
                    "IPCManager: No Master found. Starting as Master (Role: MASTER)"
                )
                return self.role, self.listener
            except Exception as e:
                logger.error(f"IPCManager: Failed to start as Master: {e}")
                return "ERROR", str(e)

    def proxy_call(self, tool_name: str, arguments: dict) -> dict:
        """Sends a tool call to the Master and waits for a response."""
        if self.role != "PROXY" or not self.connection:
            return {"error": "IPCManager: Not in PROXY role or connection lost."}

        try:
            payload = {"tool": tool_name, "arguments": arguments}
            self.connection.send(payload)
            response = self.connection.recv()
            return response
        except Exception as e:
            logger.error(f"IPCManager: Proxy call failed: {e}")
            return {"error": f"IPCManager: Communication error with Master: {e}"}

    def start_master_loop(self, executor_func):
        """
        Starts the Master listener loop in a background thread.
        executor_func: A function(tool_name, arguments) -> result
        """
        if self.role != "MASTER" or not self.listener:
            logger.error("IPCManager: Cannot start Master loop without MASTER role.")
            return

        def run_loop():
            logger.info("IPCManager: Master loop started.")
            while not self._stop_event.is_set():
                try:
                    # accept() blocks until a new client connects
                    # In a real scenario, we might want to handle multiple clients concurrently,
                    # but for MCP simple sequential is often enough or we can spawn threads.
                    conn = self.listener.accept()
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(conn, executor_func),
                        daemon=True,
                    )
                    client_thread.start()
                except Exception as e:
                    if not self._stop_event.is_set():
                        logger.error(f"IPCManager: Listener error: {e}")
                    break

        self.worker_thread = threading.Thread(target=run_loop, daemon=True)
        self.worker_thread.start()

    def _handle_client(self, conn, executor_func):
        """Handles a single Proxy client connection."""
        try:
            while True:
                try:
                    request = conn.recv()
                    tool = request.get("tool")
                    args = request.get("arguments", {})

                    # Execute tool call
                    result = executor_func(tool, args)

                    # Return result
                    conn.send({"result": result})
                except (EOFError, ConnectionResetError):
                    break
                except Exception as e:
                    logger.error(f"IPCManager: Client handling error: {e}")
                    conn.send({"error": str(e)})
                    break
        finally:
            conn.close()

    def close(self):
        """Stops the listener and closes connections."""
        self._stop_event.set()
        if self.listener:
            try:
                # To break the accept() block, we might need a dummy connection
                # or just let the process exit as it's a daemon thread.
                self.listener.close()
            except:
                pass
        if self.connection:
            try:
                self.connection.close()
            except:
                pass


# Global Instance
ipc_manager = IPCManager()
