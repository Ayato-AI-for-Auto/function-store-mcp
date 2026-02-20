import logging
import queue
import threading
import time
from typing import Callable

logger = logging.getLogger(__name__)


class AsyncTaskWorker:
    """
    Singleton Worker that serializes all background tasks to prevent DB lock contention.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AsyncTaskWorker, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.task_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.worker_thread.start()
        self._initialized = True
        logger.info("AsyncTaskWorker: Singleton worker thread started.")

    def add_task(self, func: Callable, *args, **kwargs):
        """Adds a task to the queue."""
        self.task_queue.put((func, args, kwargs))
        logger.debug(
            f"AsyncTaskWorker: Task added. Queue size: {self.task_queue.qsize()}"
        )

    def _run_loop(self):
        while True:
            try:
                # Blocks until a task is available
                func, args, kwargs = self.task_queue.get()
                logger.info(f"AsyncTaskWorker: Executing task {func.__name__}...")

                # Execute the task
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    logger.error(
                        f"AsyncTaskWorker: Task execution failed: {e}", exc_info=True
                    )
                finally:
                    self.task_queue.task_done()
                    logger.debug(
                        f"AsyncTaskWorker: Task done. Remaining: {self.task_queue.qsize()}"
                    )
            except Exception as e:
                logger.error(f"AsyncTaskWorker: Loop error: {e}")
                time.sleep(1)


# Global Instance
task_worker = AsyncTaskWorker()
