"""At most three original-runtime recovery attempts; no model substitution."""

import argparse
import json
import os
import subprocess
import sys
import time

import requests

from ragbase.config import load_config
from ragbase.evaluation.artifacts import write_json
from ragbase.evaluation.benchmark import read_jsonl, sha256_file
from scripts.release.common import ROOT, RELEASE, begin, verify, now, write_md

HOST = "http://127.0.0.1:11434"


def command(args):
    try:
        result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    except subprocess.TimeoutExpired:
        return {"command": args, "returncode": 124, "stdout": "", "stderr": "Bounded environment command exceeded 30 seconds; no unrecorded retry."}
    return {"command": args, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def state():
    recorded = json.loads((ROOT / "docs/model_artifacts.json").read_text(encoding="utf-8"))
    status = {"timestamp": now(), "gpu": command(["nvidia-smi", "--query-gpu=name,driver_version,memory.used,memory.total", "--format=csv,noheader"]),
              "gpu_compute_processes": command(["nvidia-smi", "--query-compute-apps=pid,process_name,used_gpu_memory", "--format=csv,noheader"]),
              "client_version": command([str(ROOT / ".runtime/ollama/bin/ollama.exe"), "--version"]),
              "inventory": command([str(ROOT / ".runtime/ollama/bin/ollama.exe"), "list"]),
              "launch_environment": {key: os.environ.get(key) for key in ["CUDA_VISIBLE_DEVICES", "OLLAMA_HOST", "OLLAMA_MODELS", "OLLAMA_CONTEXT_LENGTH", "OLLAMA_LLM_LIBRARY"]},
              "expected_digest": recorded["llm"]["digest"], "expected_ollama": recorded["ollama"]["version"]}
    try:
        status["server_version"] = requests.get(HOST + "/api/version", timeout=5).json()["version"]
        models = requests.get(HOST + "/api/tags", timeout=5).json()["models"]
        model = next(row for row in models if row["name"] == recorded["llm"]["name"])
        status["model_digest"] = model["digest"]
        status["frozen_model_matches"] = model["digest"] == recorded["llm"]["digest"] and status["server_version"] == recorded["ollama"]["version"]
        status["loaded_models"] = requests.get(HOST + "/api/ps", timeout=5).json()
    except (requests.RequestException, ValueError, KeyError, StopIteration) as error:
        status["server_error"] = str(error)
        status["frozen_model_matches"] = False
    return status


def restart(number):
    # Constant script, static paths: only the previously task-owned executable.
    script = r"""
$ReleaseRoot = (Get-Location).Path
$ReleaseExe = (Resolve-Path -LiteralPath '.runtime\ollama\bin\ollama.exe').Path
$ReleaseKnownId = [int](Get-Content -LiteralPath '.runtime\ollama\server.pid')
$ReleaseServers = @(Get-CimInstance Win32_Process -Filter "ProcessId=$ReleaseKnownId")
if ($ReleaseServers.Count -ne 1 -or $ReleaseServers[0].ExecutablePath -ne $ReleaseExe -or $ReleaseServers[0].CommandLine -notmatch '\bserve\b') { throw 'Known service PID is not the task-owned Ollama; refusing termination' }
$ReleaseOwned = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$ReleaseKnownId" | Where-Object { $_.ExecutablePath -like (Join-Path $ReleaseRoot '.runtime\ollama\bin\*') })
foreach ($ReleaseRunner in $ReleaseOwned) { Stop-Process -Id $ReleaseRunner.ProcessId -ErrorAction SilentlyContinue }
foreach ($ReleaseServer in $ReleaseServers) { Stop-Process -Id $ReleaseServer.ProcessId -ErrorAction Stop }
$env:OLLAMA_MODELS = Join-Path $ReleaseRoot '.runtime\ollama\models'
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_KEEP_ALIVE = '1h'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$env:OLLAMA_CONTEXT_LENGTH = '2048'
$ReleaseLog = Join-Path $ReleaseRoot 'reports\release\recovery'
$ReleaseNew = Start-Process -FilePath $ReleaseExe -ArgumentList 'serve' -WorkingDirectory $ReleaseRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $ReleaseLog 'attempt_NUMBER.stdout.log') -RedirectStandardError (Join-Path $ReleaseLog 'attempt_NUMBER.stderr.log')
$ReleaseNew.Id | Set-Content -LiteralPath '.runtime\ollama\server.pid' -Encoding ASCII
$ReleaseNew.Id
""".replace("NUMBER", str(number))
    result = command(["powershell", "-NoProfile", "-Command", script])
    if result["returncode"]:
        return result
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            requests.get(HOST + "/api/version", timeout=1).raise_for_status()
            break
        except requests.RequestException:
            time.sleep(0.5)
    return result


def probe():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from ragbase.generation.generator import AnswerGenerator
    from ragbase.schema import RetrievalResult
    config = load_config(ROOT / "configs/v2/dense_reranker.yaml")
    row = read_jsonl(ROOT / "experiments/final_validation/external/retrieval_only/retrieval_predictions.jsonl")[0]
    chunks = {chunk["chunk_id"]: chunk for chunk in read_jsonl(ROOT / "experiments/final_validation/external/run/chunks.jsonl")}
    results = [RetrievalResult(**result, text=chunks[result["chunk_id"]]["text"]) for result in row["results"]]
    output = AnswerGenerator(config).generate(row["question"], results)
    write_json(RELEASE / "recovery/probe_success.json", {"id": row["id"], "config": config.to_dict(), **output.to_dict()})
    print("Identical frozen external generation request succeeded.")


def render(attempts, status):
    lines = ["# External Generation：有限环境恢复记录", "", "本轮最多3次；旧轮两次失败保留不改。只操作本项目确认的 Ollama 服务及其直属 runner；不终止其他 GPU 应用、不改驱动/模型/量化/API/generation 参数。", ""]
    for attempt in attempts:
        lines += [f"## 本轮 Attempt {attempt['attempt']}", "", f"时间：{attempt['timestamp']}", "",
                  f"结果：{attempt['status']}", "", "GPU state：", "", "```text", attempt["before"]["gpu"]["stdout"].strip(), "```", "",
                  f"Ollama：{attempt['after'].get('server_version', 'unavailable')}；Gemma digest：{attempt['after'].get('model_digest', 'unavailable')}", "",
                  "计划命令：按原 binary/cache/startup 设置恢复 task-owned serve；只有环境步骤成功且digest匹配才执行原外测请求。实际执行阶段见返回码与下列错误，环境命令超时不冒充CUDA模型请求。", "",
                  "```text", attempt.get("error", "No error"), "```", ""]
    lines += [f"最终状态：**{status}**。完整前后 GPU/process/inventory、command、digest 和错误保存在 recovery/*.json。", "",
              "不会用 API 失败充当拒答，不替换正式模型补数字。DLL/driver 根因没有单因素实验确认。"]
    write_md(RELEASE / "external_generation_recovery_log.md", "\n".join(lines))
    if status == "BLOCKED":
        write_md(RELEASE / "EXTERNAL_GENERATION_BLOCKED.md", "# External Generation：BLOCKED\n\n历史两次原模型请求发生CUDA初始化失败；本轮三次受控恢复没有恢复可用生成。GPU可见、原Ollama版本与Gemma digest匹配，但本轮环境/进程恢复命令超过30秒时限，没有进入新的模型probe。不能将三次环境超时写成三次CUDA请求失败。完整GPU/process/inventory/command/error保留在恢复日志与JSON。\n\n正式模型与generation config保持原样，没有升级/降级、换模型/API/量化或调整num_ctx/temperature。本轮已达到最多三次恢复上限，停止诊断。自然检索完成，生成所有指标N/A，API/环境异常不冒充拒答。项目按真实阻塞状态封版。\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    begin()
    directory = RELEASE / "recovery"
    directory.mkdir(exist_ok=True)
    if args.probe:
        probe()
        return
    attempts = []
    for number in range(1, 4):
        path = directory / f"attempt_{number}.json"
        if path.exists():
            attempts.append(json.loads(path.read_text(encoding="utf-8")))
            if attempts[-1]["status"] == "RECOVERED":
                break
            continue
        before = state()
        if not before["frozen_model_matches"]:
            raise ValueError("Pinned model/version inventory differs; do not substitute")
        write_json(path, {"attempt": number, "timestamp": now(), "before": before, "status": "STARTED"})
        restart_result = restart(number)
        after = state()
        if restart_result["returncode"] or not after["frozen_model_matches"]:
            error = json.dumps(restart_result, ensure_ascii=False)
            outcome = "FAILED"
        else:
            try:
                result = subprocess.run([sys.executable, "-u", "-m", "scripts.release.recovery", "--probe"], cwd=ROOT,
                                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=150)
                outcome = "RECOVERED" if result.returncode == 0 else "FAILED"
                error = result.stderr if result.returncode else ""
            except subprocess.TimeoutExpired as exception:
                outcome, error = "FAILED", "Original frozen request exceeded bounded 150s recovery probe: " + str(exception)
        attempt = {"attempt": number, "timestamp": now(), "before": before, "after": after, "restart_command": restart_result,
                   "probe_command": "python -m scripts.release.recovery --probe", "status": outcome, "error": error,
                   "config_sha256": sha256_file(ROOT / "configs/v2/dense_reranker.yaml")}
        write_json(path, attempt)
        attempts.append(attempt)
        verify()
        print(f"Release recovery {number}/3: {outcome}", flush=True)
        if outcome == "RECOVERED":
            break
    status = "RECOVERED" if any(attempt["status"] == "RECOVERED" for attempt in attempts) else "BLOCKED"
    write_json(RELEASE / "external_generation_status.json", {"status": status, "attempts": len(attempts), "maximum_attempts": 3,
               "same_frozen_model_and_config": True, "historical_failure_attempts": 2})
    render(attempts, status)
    verify()


if __name__ == "__main__":
    main()
