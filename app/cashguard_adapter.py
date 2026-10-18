"""Bridge the vendored MIT CashGuard pipeline to 8bit's UI/API contract."""
from __future__ import annotations

import os
import json
import uuid
from pathlib import Path

from app.schemas import AnalysisResult, EvidenceFrame, RuleReference, ViolationEvent


class CashGuardAdapter:
    def __init__(self, config):
        # No video processing may cause model downloads or telemetry.
        os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
                          CASHGUARD_VLM="1", CASHGUARD_SAFE_CLF="1", CASHGUARD_MONEY_CLF="1",
                          CASHGUARD_VLM_MODEL=str(config.vlm_model), CASHGUARD_VLM_BACKEND=config.vlm_backend, CASHGUARD_MLX_MODEL=str(config.vlm_model))
        from app.cashguard.pipeline import Analyzer
        self.analyzer = Analyzer(device=config.device)
        missing = [name for name in ("safe_clf", "money_clf", "vlm") if getattr(self.analyzer, name) is None]
        if missing:
            raise RuntimeError("Required CashGuard components unavailable: "+", ".join(missing))
        self.config = config
        from app.cashguard.scene import CACHE
        from app.cashguard.vlm import VLM_CACHE
        for folder in (CACHE, VLM_CACHE):
            folder.mkdir(parents=True, exist_ok=True, mode=0o700)
            folder.chmod(0o700)
            folder.parent.chmod(0o700)

    def analyze(self, path: Path) -> AnalysisResult:
        from app.cashguard.scene import CACHE
        from app.cashguard.vlm import VLM_CACHE
        # Cache is isolated by random job identity, never by original file name.
        identity = uuid.uuid4().hex
        try:
            full = self.analyzer.run(path, job_id=identity)
            result = self.convert(full)
            result.metadata["vlm_backend"] = self.config.vlm_backend
            result.metadata["vlm_model"] = self.config.vlm_model.name
            state_cache = VLM_CACHE / f"{identity}.json"
            if state_cache.exists():
                answers = json.loads(state_cache.read_text())
                allowed = {"laptop": ("screen", {"unlocked", "locked", "off", "closed"}),
                           "door": ("door", {"open", "closed"})}
                unreadable = 0
                for key, answer in answers.items():
                    category = key.split("@", 1)[0]
                    if category in allowed:
                        field, values = allowed[category]
                        unreadable += not isinstance(answer, dict) or answer.get(field) not in values
                result.metadata["unreadable_state_answers"] = unreadable
                if unreadable:
                    result.metadata["warnings"].append("Часть состояний экрана или двери не удалось определить; связанные проверки ограничены.")
            return result
        finally:
            # Keep the result/evidence under 8bit's protected TTL, not indefinite upstream caches.
            for folder in (CACHE, VLM_CACHE):
                (folder / f"{identity}.json").unlink(missing_ok=True)

    @staticmethod
    def convert(full: dict) -> AnalysisResult:
        meta = full.get("meta", {})
        scene = meta.get("scene", {})
        # Upstream optional inference failures must not look like a clean video.
        failed = [key for key in ("safe_classifier", "money_classifier", "vlm") if scene.get(key) in {"off", "error"}]
        if failed:
            raise RuntimeError("Required visual checks failed: "+", ".join(failed))
        explained = full.get("explain", [])
        if len(explained) != len(full["violations"]):
            raise ValueError("CashGuard evidence explanations do not match events")
        violations = []
        for event, explanation in zip(full["violations"], explained):
            references = explanation.get("refs", [])
            if not references:
                raise ValueError("Detected event has no curated regulatory source")
            primary = references[0]
            frames = [EvidenceFrame.model_validate(frame) for frame in event["evidence_frames"]]
            if not 1 <= len(frames) <= 3:
                raise ValueError("Detected event requires 1–3 readable evidence frames")
            # Preserve upstream decisions and timestamps; qualify hidden facts in review text.
            qualifications = {
                "E_unauthorized_person": "Полномочия присутствующих по видео не устанавливаются.",
                "F_bag_no_check": "Полнота проверки сумки вне видимого фрагмента не устанавливается.",
                "C_cash_on_desk_next_client": "Принадлежность денег предыдущей операции требует проверки.",
                "L_workstation_unlocked": "Косвенная нормативная связь: короткий ролик не доказывает нарушение 30-минутного срока автоблокировки.",
            }
            text = event["description"]+" "+qualifications.get(explanation.get("code"), "")
            observed_overrides = {
                "E_unauthorized_person": "В кассовой зоне обнаружен дополнительный человек или человек за рабочим столом кассира. Требуется проверить режим доступа; роли и полномочия по видео не подтверждаются.",
                "F_bag_no_check": "Видна передача сумки и короткий интервал до ухода передавшего её человека. Требуется проверить полноту осмотра сумки и пломб; отсутствие проверки вне видимого фрагмента не устанавливается.",
                "A_unattended_valuables": "После ухода человека на рабочей поверхности обнаружены предметы, похожие на наличные или сумку для ценностей. Требуется проверить режим хранения; содержимое сумки и принадлежность предметов по видео не устанавливаются.",
                "C_cash_on_desk_next_client": "При появлении посетителя на рабочей поверхности обнаружены предметы, похожие на банкноты. Требуется проверить порядок хранения; принадлежность денег предыдущей операции по видео не устанавливается.",
            }
            if explanation.get("code") == "G_personal_items" and explanation.get("details", {}).get("kind") == "drinking":
                text = "В рабочей зоне виден эпизод взаимодействия с предметом, похожим на стакан или бутылку. Требуется проверить порядок организации рабочего места. Нормативная связь с пунктом 12 Правил № 231 косвенная: сам по себе напиток не доказывает нарушение хранения личных вещей."
            if explanation.get("code") in observed_overrides:
                text = observed_overrides[explanation["code"]]+" Нормативная связь для проверки: "+explanation.get("norm", "")
            violations.append(ViolationEvent(type=event["type"], timecode_sec=event["timecode_sec"],
                description=text.strip(), evidence_frames=frames,
                rule=RuleReference(document=primary["doc"], section=primary["label"], url=primary["url"]),
                confidence=explanation.get("score")))
        warnings = []
        for key, label in {"desk": "рабочая поверхность", "safe": "сейф", "door": "дверь", "laptop": "экран"}.items():
            if not scene.get(key):
                warnings.append(f"Не удалось надёжно локализовать объект: {label}. Связанные проверки ограничены.")
        if scene.get("vlm_questions", 0) >= 12:
            warnings.append("Достигнут лимит проверок экрана и двери; часть эпизодов могла остаться непроверенной.")
        meta = dict(meta)
        if "job_id" in meta:
            meta["model_run_id"] = meta.pop("job_id")
        meta = dict(meta, pipeline="cashguard-integrated-v1", local_only=True, warnings=warnings,
                    coverage={"scene":scene, "document_return":"unsupported", "face_identification":False},
                    rule_explanations=[{k:v for k,v in item.items() if k != "refs"} for item in explained])
        return AnalysisResult(verdict="violation" if violations else "no_violation", violations=violations, metadata=meta)
