import threading
import json
import logging
import traceback
from typing import List, Dict, Tuple, Optional, Any
import docker

logger = logging.getLogger(__name__)

class DockerRuntime:
    """
    Executes Python code in isolated Docker containers.
    Implements 'Warm Pool' strategy for zero-latency execution.
    """
    
    # Mapping dependencies/tags to base images
    IMAGE_MAP = {
        "minimal": "function-store/minimal:latest",
        "data-science": "function-store/data-science:latest",
        "ai-ml": "function-store/ai-ml:latest"
    }

    def __init__(self, warm_pool_size: int = 1):
        self.warm_pool_size = warm_pool_size
        self.client = None
        self._pool: Dict[str, List[Any]] = {k: [] for k in self.IMAGE_MAP}
        self._init_lock = threading.Lock()
        
        # Defer client initialization to first use to avoid blocking startup (context deadline exceeded)
        logger.info("DockerRuntime: Lazy initialization enabled.")

    def _ensure_client(self) -> bool:
        """Lazily initializes the Docker client."""
        if self.client:
            return True
            
        with self._init_lock:
            if self.client:
                return True
                
            try:
                self.client = docker.from_env()  # type: ignore
                self.client.ping()              # type: ignore
                logger.info("DockerRuntime: Docker client initialized successfully (Lazy).")
                return True
            except Exception as e:
                logger.warning(f"DockerRuntime: Docker initialization failed: {e}")
                self.client = None
                return False

    def prewarm_now(self):
        """Manually trigger pre-warming (should be called with a delay from server.py)"""
        if self._ensure_client():
            logger.info(f"DockerRuntime: Pre-warming pool (size={self.warm_pool_size})...")
            threading.Thread(target=self._prewarm_pool, daemon=True).start()

    def _prewarm_pool(self):
        if not self.client:
            return
        logger.info(f"DockerRuntime: Pre-warming pool (size={self.warm_pool_size})...")
        for image_key in self.IMAGE_MAP:
            # For MVP, we only pre-warm 'minimal' to save resources
            if image_key == "minimal":
                for _ in range(self.warm_pool_size):
                    self._create_warm_container(image_key)

    def _create_warm_container(self, image_key: str) -> Optional[Any]:
        image_name = self.IMAGE_MAP[image_key]
        try:
            container = self.client.containers.run(  # type: ignore
                image_name,
                command=["sleep", "infinity"],
                detach=True,
                remove=True,
                labels={"function-store": "warm-pool", "image-key": image_key}
            )
            self._pool[image_key].append(container)
            logger.info(f"DockerRuntime: Warm container created: {container.short_id} ({image_key})")
            return container
        except Exception as e:
            logger.error(f"DockerRuntime: Failed to create warm container for {image_key}: {e}")
            return None

    def _get_container(self, image_key: str) -> Optional[Any]:
        # Try to get from pool
        while self._pool[image_key]:
            container = self._pool[image_key].pop()
            try:
                container.reload()
                if container.status == "running":
                    return container
            except Exception:
                continue
        
        # If pool empty, create one on-the-fly (but it's a 'warm-style' container)
        return self._create_warm_container(image_key)

    def is_available(self) -> bool:
        return self.client is not None

    def run_function(self, code: str, test_cases: List[Dict], dependencies: List[str] = []) -> Tuple[bool, str]:
        """
        Run code in a Docker container using the Warm Pool.
        """
        if not self._ensure_client():
            return False, "Docker is not available."

        image_key = self._select_image_key(dependencies)
        container = self._get_container(image_key)
        
        if not container:
            return False, "Could not acquire a container for execution."

        try:
            logger.debug(f"DockerRuntime: Executing in container {container.short_id} ({image_key})")
            
            runner_script = self._create_runner_script(code, test_cases)
            
            # Execute script via python -c
            # We use a trick: pass the code via env var or file to avoid shell escape issues
            # For MVP, we'll try passing it as a command argument (simple but potentially problematic for huge code)
            exec_result = container.exec_run(
                cmd=["python3", "-c", runner_script],
                workdir="/app"
            )
            
            # Return container back to pool (stateless assumption for now)
            # In production, we should reset the container or discard it if it was mutated
            self._pool[image_key].append(container)
            
            output = exec_result.output.decode("utf-8").strip()
            
            if exec_result.exit_code != 0:
                return False, f"Container execution failed (Exit {exec_result.exit_code}): {output}"

            try:
                # Find the last JSON line in case there's other output
                lines = output.splitlines()
                if not lines:
                    return False, "Container produced no output."
                
                json_out = json.loads(lines[-1])
                if json_out.get("status") == "success":
                    return True, ""
                else:
                    return False, json_out.get("error", "Unknown error")
            except (json.JSONDecodeError, IndexError):
                return False, f"Failed to parse container output: {output}"

        except Exception as e:
            logger.error(f"DockerRuntime Exception: {traceback.format_exc()}")
            return False, f"Docker Runtime Exception: {str(e)}"

    def cleanup(self):
        """Stops and removes all containers in the warm pool."""
        if not self.client:
            return
        # ... rest remains same
        logger.info("DockerRuntime: Cleaning up warm pool...")
        for image_key, containers in self._pool.items():
            for container in containers:
                try:
                    # container.remove(force=True) might fail if logger is closed or container already gone
                    container.remove(force=True)
                except Exception:
                    # During atexit, logging might be closed, so we just ignore
                    pass
        self._pool = {k: [] for k in self.IMAGE_MAP}

    def _select_image_key(self, dependencies: List[str]) -> str:
        # Simple heuristic to select image key
        deps_str = " ".join(dependencies).lower()
        if any(lib in deps_str for lib in ["torch", "transformers", "sentence-transformers"]):
            return "ai-ml"
        if any(lib in deps_str for lib in ["pandas", "numpy", "scipy", "sklearn"]):
            return "data-science"
        return "minimal"

    def _create_runner_script(self, code: str, test_cases: List[Dict]) -> str:
        # Same runner logic as SubprocessRuntime
        return f"""
import json
import traceback
import sys

def run():
    namespace = {{}}
    try:
        exec({repr(code)}, namespace)
    except Exception:
        return {{"status": "error", "error": "Compilation/Setup Error:\\n" + traceback.format_exc()}}
    
    candidates = [v for k, v in namespace.items() if callable(v) and not k.startswith('_')]
    if not candidates:
        return {{"status": "error", "error": "No function found in code."}}
    func = candidates[-1]

    test_cases = {json.dumps(test_cases)}
    errors = []
    for i, tc in enumerate(test_cases):
        try:
            res = func(**tc.get('input', {{}}))
            if res != tc.get('expected'):
                errors.append(f"Test {{i+1}}: Expected {{tc.get('expected')}}, got {{res}}")
        except Exception:
            errors.append(f"Test {{i+1}}: Runtime Error - " + traceback.format_exc())
    
    if errors:
        return {{"status": "error", "error": "; ".join(errors)}}
    return {{"status": "success"}}

if __name__ == "__main__":
    print(json.dumps(run()))
"""

docker_runtime = DockerRuntime()
