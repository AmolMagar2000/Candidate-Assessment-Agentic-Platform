#!/usr/bin/env python3
"""
Working Code Execution Engine
"""

import asyncio
import subprocess
import os
import time
import logging
import tempfile
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

class ExecutionResult:
    def __init__(self, stdout="", stderr="", exit_code=0, execution_time_ms=0, 
                 memory_usage_mb=None, status="Accepted", timeout=False):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.execution_time_ms = execution_time_ms
        self.memory_usage_mb = memory_usage_mb
        self.status = status
        self.timeout = timeout

class CodeExecutor:
    def __init__(self):
        self.languages = {
            "python": {
                "name": "Python",
                "extension": ".py",
                "run_command": ["python3"],
                "timeout": 30,
                "version_cmd": ["python3", "--version"]
            },
            "java": {
                "name": "Java",
                "extension": ".java",
                "compile_command": ["javac"],
                "run_command": ["java"],
                "timeout": 30,
                "version_cmd": ["java", "--version"]
            },
            "cpp": {
                "name": "C++",
                "extension": ".cpp",
                "compile_command": ["g++", "-o", "solution"],
                "run_command": ["./solution"],
                "timeout": 30,
                "version_cmd": ["g++", "--version"]
            },
            "javascript": {
                "name": "JavaScript",
                "extension": ".js",
                "run_command": ["node"],
                "timeout": 30,
                "version_cmd": ["node", "--version"]
            }
        }
    
    async def get_supported_languages(self):
        languages = []
        
        for i, (key, config) in enumerate(self.languages.items()):
            try:
                process = await asyncio.create_subprocess_exec(
                    *config["version_cmd"],
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5)
                
                if process.returncode == 0:
                    version = stdout.decode().strip().split('\n')[0]
                    available = True
                else:
                    version = "Not available"
                    available = False
            except:
                version = "Not available"
                available = False
            
            languages.append({
                "id": i + 1,
                "name": config["name"],
                "key": key,
                "version": version,
                "timeout_seconds": config["timeout"],
                "memory_limit_mb": 256,
                "available": available
            })
        
        return languages
    
    async def execute_code(self, language: str, source_code: str, stdin: str = "", timeout: int = None):
        if language not in self.languages:
            raise ValueError(f"Unsupported language: {language}")
        
        config = self.languages[language]
        timeout = timeout if timeout is not None else config["default_timeout"]
        logger.info(f"Executing {language} code with {timeout}s timeout")
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            try:
                return await self._execute_in_temp_dir(temp_path, config, source_code, stdin, timeout, language)
            except Exception as e:
                logger.error(f"Execution error: {e}")
                return ExecutionResult(
                    stdout="",
                    stderr=str(e),
                    exit_code=1,
                    execution_time_ms=0,
                    status="Runtime Error"
                )
    
    async def _execute_in_temp_dir(self, temp_dir, config, source_code, stdin, timeout, language):
        start_time = time.time()
        
        # Write source code
        source_file = temp_dir / f"Solution{config['extension']}"
        source_file.write_text(source_code, encoding='utf-8')
        
        try:
            if language == "python":
                return await self._run_python(source_file, stdin, timeout, temp_dir)
            elif language == "java":
                return await self._run_java(source_file, stdin, timeout, temp_dir)
            elif language in ["cpp", "c"]:
                return await self._run_compiled(source_file, stdin, timeout, temp_dir, config)
            elif language == "javascript":
                return await self._run_javascript(source_file, stdin, timeout, temp_dir)
            else:
                raise ValueError(f"Language {language} not implemented")
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                stdout="",
                stderr=str(e),
                exit_code=1,
                execution_time_ms=execution_time,
                status="Runtime Error"
            )
    
    async def _run_python(self, source_file, stdin, timeout, cwd):
        start_time = time.time()
        
        process = await asyncio.create_subprocess_exec(
            "python3", str(source_file),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd)
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=stdin.encode('utf-8') if stdin else None),
                timeout=timeout
            )
            timeout_occurred = False
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            timeout_occurred = True
            stdout, stderr = b"", b"Time Limit Exceeded"
        
        execution_time = int((time.time() - start_time) * 1000)
        
        status = "Accepted"
        if timeout_occurred:
            status = "Time Limit Exceeded"
        elif process.returncode != 0:
            status = "Runtime Error"
        
        return ExecutionResult(
            stdout=stdout.decode('utf-8', errors='ignore').strip(),
            stderr=stderr.decode('utf-8', errors='ignore').strip(),
            exit_code=process.returncode or 0,
            execution_time_ms=execution_time,
            status=status,
            timeout=timeout_occurred
        )
    
    async def _run_java(self, source_file, stdin, timeout, cwd):
        start_time = time.time()
        
        # Compile
        compile_process = await asyncio.create_subprocess_exec(
            "javac", str(source_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd)
        )
        
        compile_stdout, compile_stderr = await compile_process.communicate()
        
        if compile_process.returncode != 0:
            execution_time = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                stdout="",
                stderr=compile_stderr.decode('utf-8', errors='ignore'),
                exit_code=compile_process.returncode,
                execution_time_ms=execution_time,
                status="Compilation Error"
            )
        
        # Run
        class_name = source_file.stem
        process = await asyncio.create_subprocess_exec(
            "java", "-cp", str(cwd), class_name,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd)
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=stdin.encode('utf-8') if stdin else None),
                timeout=timeout
            )
            timeout_occurred = False
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            timeout_occurred = True
            stdout, stderr = b"", b"Time Limit Exceeded"
        
        execution_time = int((time.time() - start_time) * 1000)
        
        status = "Accepted"
        if timeout_occurred:
            status = "Time Limit Exceeded"
        elif process.returncode != 0:
            status = "Runtime Error"
        
        return ExecutionResult(
            stdout=stdout.decode('utf-8', errors='ignore').strip(),
            stderr=stderr.decode('utf-8', errors='ignore').strip(),
            exit_code=process.returncode or 0,
            execution_time_ms=execution_time,
            status=status,
            timeout=timeout_occurred
        )
    
    async def _run_compiled(self, source_file, stdin, timeout, cwd, config):
        start_time = time.time()
        
        # Compile
        compile_process = await asyncio.create_subprocess_exec(
            *config["compile_command"], str(source_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd)
        )
        
        compile_stdout, compile_stderr = await compile_process.communicate()
        
        if compile_process.returncode != 0:
            execution_time = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                stdout="",
                stderr=compile_stderr.decode('utf-8', errors='ignore'),
                exit_code=compile_process.returncode,
                execution_time_ms=execution_time,
                status="Compilation Error"
            )
        
        # Run
        process = await asyncio.create_subprocess_exec(
            *config["run_command"],
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd)
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=stdin.encode('utf-8') if stdin else None),
                timeout=timeout
            )
            timeout_occurred = False
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            timeout_occurred = True
            stdout, stderr = b"", b"Time Limit Exceeded"
        
        execution_time = int((time.time() - start_time) * 1000)
        
        status = "Accepted"
        if timeout_occurred:
            status = "Time Limit Exceeded"
        elif process.returncode != 0:
            status = "Runtime Error"
        
        return ExecutionResult(
            stdout=stdout.decode('utf-8', errors='ignore').strip(),
            stderr=stderr.decode('utf-8', errors='ignore').strip(),
            exit_code=process.returncode or 0,
            execution_time_ms=execution_time,
            status=status,
            timeout=timeout_occurred
        )
    
    async def _run_javascript(self, source_file, stdin, timeout, cwd):
        start_time = time.time()
        
        process = await asyncio.create_subprocess_exec(
            "node", str(source_file),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd)
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=stdin.encode('utf-8') if stdin else None),
                timeout=timeout
            )
            timeout_occurred = False
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            timeout_occurred = True
            stdout, stderr = b"", b"Time Limit Exceeded"
        
        execution_time = int((time.time() - start_time) * 1000)
        
        status = "Accepted"
        if timeout_occurred:
            status = "Time Limit Exceeded"
        elif process.returncode != 0:
            status = "Runtime Error"
        
        return ExecutionResult(
            stdout=stdout.decode('utf-8', errors='ignore').strip(),
            stderr=stderr.decode('utf-8', errors='ignore').strip(),
            exit_code=process.returncode or 0,
            execution_time_ms=execution_time,
            status=status,
            timeout=timeout_occurred
        )
