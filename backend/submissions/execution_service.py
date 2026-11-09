"""
Docker-based secure C code execution service.

Executes student-submitted code in isolated containers with strict security constraints.
"""

import base64
import logging
import os
import shlex
import tempfile
import time
from typing import Dict, Tuple

import docker
from requests.exceptions import ReadTimeout

logger = logging.getLogger(__name__)


class ExecutionConfig:
    """Configuration for code execution."""

    # Compilation
    COMPILER = "gcc"
    COMPILE_TIMEOUT = 30  # seconds
    C_STANDARD = "c11"

    # Execution
    EXECUTION_TIMEOUT = 10  # seconds per test case
    MAX_PROCESSES = 256
    MAX_FILE_SIZE = 1024 * 1024  # 1MB
    MAX_MEMORY = 256 * 1024 * 1024  # 256MB

    # Docker
    DOCKER_IMAGE = "gcc:11-bullseye"  # Slim C compiler image
    NETWORK_MODE = "none"  # No network access
    CPUS = "1"
    MEMORY = "512m"
    MEMORY_SWAP = "512m"  # No swap

    # Security
    READ_ONLY_ROOTFS = False  # Need writable /tmp for compilation
    CAP_DROP = [
        "NET_RAW",
        "NET_ADMIN",
        "SYS_ADMIN",
        "SYS_MODULE",
        "SYS_PTRACE",
    ]
    SECCOMP_PROFILE = "default"


class DockerExecutionService:
    """Secure Docker-based C code execution service."""

    def __init__(self):
        """Initialize Docker client."""
        try:
            self.client = docker.from_env()
            self.client.ping()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise

    def _create_execution_container(self) -> Tuple[str, str]:
        """
        Create a temporary working directory and return it with container ID.

        Returns:
            Tuple of (container_id, working_dir)
        """
        # Create unique temp directory
        temp_dir = tempfile.mkdtemp(prefix="codeexec_", suffix="_submission")
        logger.debug(f"Created temp directory: {temp_dir}")

        return temp_dir

    def compile_code(
        self,
        source_code: str,
        working_dir: str,
        optimization_level: str = "O0"
    ) -> Tuple[bool, str, float]:
        """
        Compile C code inside Docker container.

        Args:
            source_code: C source code
            working_dir: Working directory for compilation
            optimization_level: GCC optimization level

        Returns:
            Tuple of (success: bool, error_message: str, compilation_time_ms: float)
        """
        source_file = os.path.join(working_dir, "main.c")
        executable_file = os.path.join(working_dir, "main")
        container = None
        started_at = time.monotonic()

        try:
            # Write source code to file
            with open(source_file, "w") as f:
                f.write(source_code)
            logger.debug(f"Wrote source code to {source_file}")

            # Prepare compilation command
            compile_cmd = [
                ExecutionConfig.COMPILER,
                f"-{optimization_level}",
                f"-std={ExecutionConfig.C_STANDARD}",
                "-Wall",
                "-Wextra",
                "-o",
                "/work/main",
                "/work/main.c",
            ]

            # Run detached so Docker's wait API can enforce the compile limit.
            container = self.client.containers.run(
                ExecutionConfig.DOCKER_IMAGE,
                command=compile_cmd,
                volumes={working_dir: {"bind": "/work", "mode": "rw"}},
                working_dir="/work",
                network_mode=ExecutionConfig.NETWORK_MODE,
                cpu_quota=int(float(ExecutionConfig.CPUS) * 100000),
                mem_limit=ExecutionConfig.MEMORY,
                memswap_limit=ExecutionConfig.MEMORY_SWAP,
                cap_drop=ExecutionConfig.CAP_DROP,
                user="1000:1000",  # Non-root user
                remove=False,  # Keep for inspection
                detach=True,
            )

            try:
                wait_result = container.wait(timeout=ExecutionConfig.COMPILE_TIMEOUT)
            except ReadTimeout:
                logger.warning("Compilation timeout exceeded")
                try:
                    container.kill()
                except docker.errors.APIError:
                    logger.debug("Compile container had already stopped at timeout")
                return (
                    False,
                    f"Compilation timed out after {ExecutionConfig.COMPILE_TIMEOUT} seconds.",
                    ExecutionConfig.COMPILE_TIMEOUT * 1000,
                )

            compilation_time_ms = (time.monotonic() - started_at) * 1000
            compiler_output = self._decode_logs(
                container.logs(stdout=True, stderr=True)
            ).strip()

            if wait_result.get("StatusCode") != 0:
                logger.warning("Compilation failed: %s", compiler_output)
                return (
                    False,
                    compiler_output or "The compiler exited with an error.",
                    compilation_time_ms,
                )

            # Check if compilation succeeded
            if os.path.exists(executable_file) and os.access(executable_file, os.X_OK):
                logger.info(f"Compilation successful in {compilation_time_ms:.2f}ms")
                return True, "", compilation_time_ms

            else:
                logger.warning("Compilation failed: executable not created")
                return False, "Compilation failed: executable not created", compilation_time_ms

        except Exception as e:
            error_msg = f"Compilation error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, (time.monotonic() - started_at) * 1000
        finally:
            if container:
                try:
                    container.remove(force=True)
                except docker.errors.NotFound:
                    pass
                except Exception:
                    logger.exception("Failed to remove compilation container")

    def execute_test_case(
        self,
        working_dir: str,
        test_input: str,
        timeout_seconds: int = ExecutionConfig.EXECUTION_TIMEOUT
    ) -> Dict:
        """
        Execute compiled program with test input inside Docker container.

        Args:
            working_dir: Working directory containing compiled executable
            test_input: Input to provide to the program
            timeout_seconds: Execution timeout

        Returns:
            Dict with execution results
        """
        result = {
            "status": "runtime_error",
            "output": "",
            "error": "",
            "execution_time_ms": 0,
            "memory_used_mb": 0.0,
        }

        try:
            start_time = time.monotonic()
            encoded_input = base64.b64encode(test_input.encode("utf-8")).decode("ascii")
            shell_command = f"printf '%s' {shlex.quote(encoded_input)} | base64 -d | /work/main"
            container = None

            # Run program in isolated Docker container
            try:
                container = self.client.containers.run(
                    ExecutionConfig.DOCKER_IMAGE,
                    command=["/bin/sh", "-c", shell_command],
                    volumes={working_dir: {"bind": "/work", "mode": "ro"}},
                    working_dir="/work",
                    network_mode=ExecutionConfig.NETWORK_MODE,
                    cpu_quota=int(float(ExecutionConfig.CPUS) * 100000),
                    mem_limit=ExecutionConfig.MEMORY,
                    memswap_limit=ExecutionConfig.MEMORY_SWAP,
                    cap_drop=ExecutionConfig.CAP_DROP,
                    user="1000:1000",  # Non-root user
                    remove=False,
                    detach=True,
                )

                try:
                    wait_result = container.wait(timeout=timeout_seconds)
                except ReadTimeout:
                    logger.warning("Execution timeout exceeded")
                    try:
                        container.kill()
                    except docker.errors.APIError:
                        logger.debug("Execution container had already stopped at timeout")
                    result["status"] = "time_limit_exceeded"
                    result["error"] = f"Time limit exceeded ({timeout_seconds}s)"
                    result["execution_time_ms"] = timeout_seconds * 1000
                    return result

                execution_time_ms = (time.monotonic() - start_time) * 1000

                output_str = self._decode_logs(container.logs(stdout=True, stderr=False))
                error_str = self._decode_logs(container.logs(stdout=False, stderr=True)).strip()

                result["output"] = output_str
                result["execution_time_ms"] = execution_time_ms
                if wait_result.get("StatusCode") == 0:
                    result["status"] = "accepted"
                    logger.debug("Execution successful in %.2fms", execution_time_ms)
                else:
                    result["status"] = "runtime_error"
                    result["error"] = error_str or "The program exited with an error."

            except Exception as e:
                execution_time_ms = (time.monotonic() - start_time) * 1000
                logger.error(f"Execution error: {e}")
                result["status"] = "runtime_error"
                result["error"] = str(e)
                result["execution_time_ms"] = execution_time_ms
            finally:
                if container:
                    try:
                        container.remove(force=True)
                    except docker.errors.NotFound:
                        pass
                    except Exception:
                        logger.exception("Failed to remove execution container")

        except Exception as e:
            logger.error(f"Unexpected execution error: {e}")
            result["error"] = str(e)

        return result

    @staticmethod
    def _decode_logs(logs) -> str:
        """Decode Docker log bytes while preserving program output."""
        if isinstance(logs, bytes):
            return logs.decode("utf-8", errors="replace")
        return logs or ""

    def cleanup(self, working_dir: str) -> bool:
        """
        Clean up temporary files.

        Args:
            working_dir: Working directory to clean

        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove all files in directory
            if os.path.exists(working_dir):
                for filename in os.listdir(working_dir):
                    filepath = os.path.join(working_dir, filename)
                    if os.path.isfile(filepath):
                        os.remove(filepath)

                # Remove directory
                os.rmdir(working_dir)
                logger.debug(f"Cleaned up {working_dir}")
                return True

        except Exception as e:
            logger.error(f"Error cleaning up {working_dir}: {e}")

        return False

    def cleanup_old_containers(self, max_age_minutes: int = 60):
        """
        Clean up old/dangling containers.

        Args:
            max_age_minutes: Remove containers older than this
        """
        try:
            containers = self.client.containers.list(all=True)
            cutoff_time = time.time() - (max_age_minutes * 60)

            for container in containers:
                # Check if container is old and not running
                if container.status != "running":
                    created_time = time.mktime(
                        time.strptime(
                            container.attrs["Created"].split(".")[0],
                            "%Y-%m-%dT%H:%M:%S"
                        )
                    )

                    if created_time < cutoff_time:
                        try:
                            container.remove()
                            logger.debug(f"Removed old container {container.short_id}")
                        except Exception as e:
                            logger.warning(f"Failed to remove container: {e}")

        except Exception as e:
            logger.warning(f"Error cleaning containers: {e}")


class ComparisonService:
    """Service for comparing test case outputs."""

    @staticmethod
    def normalize_output(output: str) -> str:
        """
        Normalize output for comparison.

        Handles whitespace and newline differences.
        """
        # Strip leading/trailing whitespace
        output = output.strip()

        # Normalize line endings
        output = output.replace("\r\n", "\n").replace("\r", "\n")

        # Normalize multiple spaces (but preserve internal structure)
        lines = output.split("\n")
        normalized_lines = [" ".join(line.split()) for line in lines]

        return "\n".join(normalized_lines)

    @staticmethod
    def compare_outputs(actual: str, expected: str) -> bool:
        """
        Compare actual and expected outputs.

        Args:
            actual: Actual program output
            expected: Expected output

        Returns:
            True if outputs match, False otherwise
        """
        actual_norm = ComparisonService.normalize_output(actual)
        expected_norm = ComparisonService.normalize_output(expected)

        return actual_norm == expected_norm

    @staticmethod
    def get_output_difference(actual: str, expected: str) -> str:
        """
        Get difference between outputs for debugging.

        Args:
            actual: Actual output
            expected: Expected output

        Returns:
            String describing the difference
        """
        actual_norm = ComparisonService.normalize_output(actual)
        expected_norm = ComparisonService.normalize_output(expected)

        if actual_norm == expected_norm:
            return "Output matches"

        # Line by line comparison
        actual_lines = actual_norm.split("\n")
        expected_lines = expected_norm.split("\n")

        if len(actual_lines) != len(expected_lines):
            return f"Line count mismatch: got {len(actual_lines)}, expected {len(expected_lines)}"

        for i, (actual_line, expected_line) in enumerate(zip(actual_lines, expected_lines)):
            if actual_line != expected_line:
                return f"Line {i + 1} mismatch:\nGot:      '{actual_line}'\nExpected: '{expected_line}'"

        return "Output matches"
