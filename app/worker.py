"""Persistent isolated inference process. Parent owns the deadline and can kill it."""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import threading
import time
from pathlib import Path


def inference_worker(connection, config):
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    try:
        import torch
        torch.set_num_threads(2)
        from app.service import InferenceService
        service = InferenceService(config)
        service.load()
        connection.send({"ready": True})
        while True:
            path = connection.recv()
            if path is None:
                break
            try:
                result = service.analyze(Path(path))
                result_path = Path(path).with_suffix(".result.json")
                temporary = result_path.with_suffix(".tmp")
                temporary.write_text(result.model_dump_json())
                temporary.chmod(0o600)
                temporary.replace(result_path)
                # Only send a small control message through the watchdog pipe.
                connection.send({"result_path": str(result_path)})
            except Exception as exc:
                connection.send({"error": f"{type(exc).__name__}: {exc}"[:1000]})
    except EOFError:
        pass
    except Exception as exc:
        connection.send({"error": f"Model worker failed: {type(exc).__name__}: {exc}"})
    finally:
        connection.close()


class ModelWorker:
    def __init__(self, config):
        self.config = config
        self.process = None
        self.connection = None
        self.loaded = False
        self.lock = threading.RLock()

    @property
    def ready(self):
        return self.loaded and self.process is not None and self.process.is_alive()

    def _receive(self, deadline):
        remaining = deadline-time.monotonic()
        if remaining <= 0 or not self.connection.poll(remaining):
            raise TimeoutError("Analysis deadline exceeded; model worker was stopped")
        message = self.connection.recv()
        if "error" in message:
            raise RuntimeError(message["error"])
        return message

    def load(self, deadline=None):
        with self.lock:
            if self.loaded and self.process.is_alive():
                return
            self.stop()
            context = mp.get_context("spawn")
            self.connection, child = context.Pipe()
            self.process = context.Process(target=inference_worker, args=(child, self.config), daemon=True)
            self.process.start()
            child.close()
            try:
                self._receive(deadline or time.monotonic()+self.config.analysis_timeout_seconds)
                self.loaded = True
            except BaseException:
                self.stop()
                raise

    def analyze(self, path, deadline):
        with self.lock:
            try:
                self.load(deadline)
                self.connection.send(str(path))
                message = self._receive(deadline)
                if "result_path" in message:
                    result_path = Path(message["result_path"])
                    expected = Path(path).with_suffix(".result.json")
                    if result_path != expected:
                        raise ValueError("Unexpected model result path")
                    try:
                        return json.loads(result_path.read_text())
                    finally:
                        result_path.unlink(missing_ok=True)
                return message["result"]
            except BaseException:
                self.stop()
                raise

    def stop(self):
        if self.process is not None:
            if self.process.is_alive() and self.loaded and self.connection is not None:
                try:
                    self.connection.send(None)
                    self.process.join(1)
                except (OSError, EOFError):
                    pass
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(2)
                if self.process.is_alive():
                    self.process.kill()
                    self.process.join(2)
            self.process.close()
            self.process = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        self.loaded = False
