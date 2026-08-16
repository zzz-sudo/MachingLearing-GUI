from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.errors import training_error
from app.models import JobCreate, JobStatus, JobUpdate, TrainingCreate, TrainingResult
from app.storage import WorkspaceStore


class TrainingService:
    """Coordinate isolated local training processes and persist their outcomes."""

    def __init__(self, store: WorkspaceStore) -> None:
        self.store = store
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ml-gui-train")

    def start(self, project_id: str, payload: TrainingCreate) -> TrainingResult:
        dataset = self.store.get_dataset_version(payload.dataset_id)
        if dataset.project_id != project_id:
            raise training_error("数据集不属于当前项目", "training_create", datasetId=payload.dataset_id)
        if payload.method not in {"clustering", "anova"} and not payload.target_column:
            raise training_error("当前分析方法需要选择目标字段", "training_create", method=payload.method)

        project = self.store.get_project(project_id)
        labels = {
            "classification": "分类",
            "regression": "回归",
            "anova": "方差分析",
            "clustering": "聚类",
            "deep-learning": "深度学习",
        }
        job = self.store.create_job(
            JobCreate(
                project_id=project_id,
                title=f"{labels[payload.method]} 分析",
                message="等待本地训练 Worker",
            )
        )
        run_directory = Path(project.path) / "models" / job.id
        run_directory.mkdir(parents=True, exist_ok=True)
        config_path = run_directory / "run.json"
        result_path = run_directory / "result.json"
        config_path.write_text(
            json.dumps(
                {
                    "jobId": job.id,
                    "projectRoot": project.path,
                    "datasetPath": str(Path(project.path) / dataset.parquet_relative_path),
                    "method": payload.method,
                    "targetColumn": payload.target_column,
                    "validationRatio": payload.validation_ratio,
                    "randomSeed": payload.random_seed,
                    "computeMode": payload.compute_mode,
                    "resultPath": str(result_path),
                    "artifactDirectory": str(run_directory),
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        self.executor.submit(self._run, job.id, config_path, result_path)
        return TrainingResult(job_id=job.id, method=payload.method, status=JobStatus.QUEUED, target_column=payload.target_column)

    def get_result(self, job_id: str) -> TrainingResult:
        job = self.store.get_job(job_id)
        project = self.store.get_project(job.project_id)
        result_path = Path(project.path) / "models" / job.id / "result.json"
        if not result_path.is_file():
            return TrainingResult(job_id=job.id, method="unknown", status=job.status)
        try:
            return TrainingResult.model_validate_json(result_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise training_error("无法读取训练结果", "training_result_get", jobId=job.id, reason=str(error)) from error

    def _run(self, job_id: str, config_path: Path, result_path: Path) -> None:
        self.store.update_job(job_id, JobUpdate(status=JobStatus.RUNNING, progress=5, message="正在启动本地训练 Worker"))
        python_executable = self._resolve_python()
        worker_path = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "app" / "training_worker.py"
        if not worker_path.is_file():
            worker_path = Path(__file__).with_name("training_worker.py")
        try:
            process = subprocess.run(
                [str(python_executable), str(worker_path), str(config_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=3600,
                check=False,
            )
            if process.returncode != 0:
                raise RuntimeError(process.stderr.strip() or process.stdout.strip() or "训练 Worker 返回失败状态")
            result = TrainingResult.model_validate_json(result_path.read_text(encoding="utf-8"))
            if result.status == JobStatus.SUCCEEDED:
                self.store.update_job(job_id, JobUpdate(status=JobStatus.SUCCEEDED, progress=100, message="训练完成，结果已保存"))
            else:
                self.store.update_job(job_id, JobUpdate(status=JobStatus.FAILED, progress=100, message=result.error_message or "训练失败"))
        except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError) as error:
            result = TrainingResult(
                job_id=job_id,
                method="unknown",
                status=JobStatus.FAILED,
                error_type=type(error).__name__,
                error_message=str(error),
            )
            result_path.write_text(result.model_dump_json(by_alias=True, indent=2) + "\n", encoding="utf-8")
            self.store.update_job(job_id, JobUpdate(status=JobStatus.FAILED, progress=100, message=result.error_message))

    @staticmethod
    def _resolve_python() -> Path:
        configured = os.environ.get("ML_GUI_TRAINING_PYTHON")
        candidate = Path(configured) if configured else Path(r"D:\Python\python11\python.exe")
        if candidate.is_file():
            return candidate
        if getattr(sys, "frozen", False):
            raise RuntimeError("TrainingRuntimeError: packaged application requires ML_GUI_TRAINING_PYTHON")
        return Path(sys.executable)
