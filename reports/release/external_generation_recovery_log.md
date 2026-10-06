# External Generation：有限环境恢复记录

本轮最多3次；旧轮两次失败保留不改。只操作本项目确认的 Ollama 服务及其直属 runner；不终止其他 GPU 应用、不改驱动/模型/量化/API/generation 参数。

## 本轮 Attempt 1

时间：2026-10-07T01:45:08.963306+08:00

结果：FAILED

GPU state：

```text
NVIDIA GeForce RTX 4060 Laptop GPU, 616.92, 1311 MiB, 8188 MiB
```

Ollama：0.35.1；Gemma digest：ff02c3702f322b9e075e9568332d96c0a7028002f1a5a056e0a6784320a4db0b

计划命令：按原 binary/cache/startup 设置恢复 task-owned serve；只有环境步骤成功且digest匹配才执行原外测请求。实际执行阶段见返回码与下列错误，环境命令超时不冒充CUDA模型请求。

```text
Initial PowerShell environment discovery exceeded 30-second bound; PID stayed 30064, no new service/probe log existed. Counted as attempt 1, not silently retried.
```

## 本轮 Attempt 2

时间：2026-10-07T01:45:45.391025+08:00

结果：FAILED

GPU state：

```text
NVIDIA GeForce RTX 4060 Laptop GPU, 616.92, 1293 MiB, 8188 MiB
```

Ollama：0.35.1；Gemma digest：ff02c3702f322b9e075e9568332d96c0a7028002f1a5a056e0a6784320a4db0b

计划命令：按原 binary/cache/startup 设置恢复 task-owned serve；只有环境步骤成功且digest匹配才执行原外测请求。实际执行阶段见返回码与下列错误，环境命令超时不冒充CUDA模型请求。

```text
{"command": ["powershell", "-NoProfile", "-Command", "\n$ReleaseRoot = (Get-Location).Path\n$ReleaseExe = (Resolve-Path -LiteralPath '.runtime\\ollama\\bin\\ollama.exe').Path\n$ReleaseKnownId = [int](Get-Content -LiteralPath '.runtime\\ollama\\server.pid')\n$ReleaseServers = @(Get-CimInstance Win32_Process -Filter \"ProcessId=$ReleaseKnownId\")\nif ($ReleaseServers.Count -ne 1 -or $ReleaseServers[0].ExecutablePath -ne $ReleaseExe -or $ReleaseServers[0].CommandLine -notmatch '\\bserve\\b') { throw 'Known service PID is not the task-owned Ollama; refusing termination' }\n$ReleaseOwned = @(Get-CimInstance Win32_Process -Filter \"ParentProcessId=$ReleaseKnownId\" | Where-Object { $_.ExecutablePath -like (Join-Path $ReleaseRoot '.runtime\\ollama\\bin\\*') })\nforeach ($ReleaseRunner in $ReleaseOwned) { Stop-Process -Id $ReleaseRunner.ProcessId -ErrorAction SilentlyContinue }\nforeach ($ReleaseServer in $ReleaseServers) { Stop-Process -Id $ReleaseServer.ProcessId -ErrorAction Stop }\n$env:OLLAMA_MODELS = Join-Path $ReleaseRoot '.runtime\\ollama\\models'\n$env:OLLAMA_HOST = '127.0.0.1:11434'\n$env:OLLAMA_KEEP_ALIVE = '1h'\n$env:OLLAMA_NUM_PARALLEL = '1'\n$env:OLLAMA_MAX_LOADED_MODELS = '1'\n$env:OLLAMA_CONTEXT_LENGTH = '2048'\n$ReleaseLog = Join-Path $ReleaseRoot 'reports\\release\\recovery'\n$ReleaseNew = Start-Process -FilePath $ReleaseExe -ArgumentList 'serve' -WorkingDirectory $ReleaseRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $ReleaseLog 'attempt_2.stdout.log') -RedirectStandardError (Join-Path $ReleaseLog 'attempt_2.stderr.log')\n$ReleaseNew.Id | Set-Content -LiteralPath '.runtime\\ollama\\server.pid' -Encoding ASCII\n$ReleaseNew.Id\n"], "returncode": 124, "stdout": "", "stderr": "Bounded environment command exceeded 30 seconds; no unrecorded retry."}
```

## 本轮 Attempt 3

时间：2026-10-07T01:46:19.936925+08:00

结果：FAILED

GPU state：

```text
NVIDIA GeForce RTX 4060 Laptop GPU, 616.92, 1297 MiB, 8188 MiB
```

Ollama：0.35.1；Gemma digest：ff02c3702f322b9e075e9568332d96c0a7028002f1a5a056e0a6784320a4db0b

计划命令：按原 binary/cache/startup 设置恢复 task-owned serve；只有环境步骤成功且digest匹配才执行原外测请求。实际执行阶段见返回码与下列错误，环境命令超时不冒充CUDA模型请求。

```text
{"command": ["powershell", "-NoProfile", "-Command", "\n$ReleaseRoot = (Get-Location).Path\n$ReleaseExe = (Resolve-Path -LiteralPath '.runtime\\ollama\\bin\\ollama.exe').Path\n$ReleaseKnownId = [int](Get-Content -LiteralPath '.runtime\\ollama\\server.pid')\n$ReleaseServers = @(Get-CimInstance Win32_Process -Filter \"ProcessId=$ReleaseKnownId\")\nif ($ReleaseServers.Count -ne 1 -or $ReleaseServers[0].ExecutablePath -ne $ReleaseExe -or $ReleaseServers[0].CommandLine -notmatch '\\bserve\\b') { throw 'Known service PID is not the task-owned Ollama; refusing termination' }\n$ReleaseOwned = @(Get-CimInstance Win32_Process -Filter \"ParentProcessId=$ReleaseKnownId\" | Where-Object { $_.ExecutablePath -like (Join-Path $ReleaseRoot '.runtime\\ollama\\bin\\*') })\nforeach ($ReleaseRunner in $ReleaseOwned) { Stop-Process -Id $ReleaseRunner.ProcessId -ErrorAction SilentlyContinue }\nforeach ($ReleaseServer in $ReleaseServers) { Stop-Process -Id $ReleaseServer.ProcessId -ErrorAction Stop }\n$env:OLLAMA_MODELS = Join-Path $ReleaseRoot '.runtime\\ollama\\models'\n$env:OLLAMA_HOST = '127.0.0.1:11434'\n$env:OLLAMA_KEEP_ALIVE = '1h'\n$env:OLLAMA_NUM_PARALLEL = '1'\n$env:OLLAMA_MAX_LOADED_MODELS = '1'\n$env:OLLAMA_CONTEXT_LENGTH = '2048'\n$ReleaseLog = Join-Path $ReleaseRoot 'reports\\release\\recovery'\n$ReleaseNew = Start-Process -FilePath $ReleaseExe -ArgumentList 'serve' -WorkingDirectory $ReleaseRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $ReleaseLog 'attempt_3.stdout.log') -RedirectStandardError (Join-Path $ReleaseLog 'attempt_3.stderr.log')\n$ReleaseNew.Id | Set-Content -LiteralPath '.runtime\\ollama\\server.pid' -Encoding ASCII\n$ReleaseNew.Id\n"], "returncode": 124, "stdout": "", "stderr": "Bounded environment command exceeded 30 seconds; no unrecorded retry."}
```

最终状态：**BLOCKED**。完整前后 GPU/process/inventory、command、digest 和错误保存在 recovery/*.json。

不会用 API 失败充当拒答，不替换正式模型补数字。DLL/driver 根因没有单因素实验确认。
