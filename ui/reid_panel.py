import time
from typing import Any, Optional

import config
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)


def _fmt_bbox(bbox: Any) -> str:
    if bbox is None:
        return "—"
    try:
        x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
        return f"({int(x1)},{int(y1)})-({int(x2)},{int(y2)})"
    except (TypeError, IndexError, ValueError):
        return str(bbox)


class ReIDStitchPanel(QGroupBox):
    """
    Панель мониторинга Re-ID: состояние галереи, пороги из конфига, журнал склеек и near-miss.
    """

    _LOG_LIMIT = 150
    _PENDING_PREVIEW_MAX = 24

    def __init__(self, parent=None):
        super().__init__("Re-ID / Identity", parent)
        root = QVBoxLayout(self)

        self._summary_gallery = QLabel()
        self._summary_counts = QLabel()
        self._summary_pending = QLabel()
        self._summary_config = QLabel()

        mono = "font-family: 'Menlo','Consolas','Courier New',monospace; font-size: 11px;"
        for lb in (
            self._summary_gallery,
            self._summary_counts,
            self._summary_pending,
            self._summary_config,
        ):
            lb.setWordWrap(True)
            lb.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            lb.setStyleSheet(mono)

        root.addWidget(self._summary_gallery)
        root.addWidget(self._summary_counts)
        root.addWidget(self._summary_pending)
        root.addWidget(self._summary_config)

        row = QHBoxLayout()
        self._stats_success = QLabel("Склейки в лог (сессия): 0")
        self._stats_rejected = QLabel("Near-miss в лог (сессия): 0")
        for s in (self._stats_success, self._stats_rejected):
            s.setStyleSheet(mono)
            row.addWidget(s)
        row.addStretch()
        root.addLayout(row)

        self._hint_stats = QLabel(
            "Подсказка: «Склейки в лог» — только новые события SUCCESS в этой сессии "
            "(дедупликация пар трекер→канон в VideoWorker). "
            "«alias_map» в блоке «Память» — фактическое число склеек, хранимых галереей сейчас."
        )
        self._hint_stats.setWordWrap(True)
        self._hint_stats.setStyleSheet("font-size: 10px; color: #888;")
        self._hint_stats.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(self._hint_stats)

        self._stats_success.setToolTip(
            "Счётчик увеличивается при каждом уникальном событии склейки, "
            "отправленном в UI с этого запуска приложения. Не равен размеру alias_map."
        )
        self._stats_rejected.setToolTip(
            "Число записей NEAR-MISS в лог панели за сессию (с прореживанием кадров в воркере)."
        )

        self.log_list = QListWidget()
        self.log_list.setStyleSheet(
            "background-color: #1e1e1e; color: #dcdcdc; "
            "font-family: 'Menlo','Consolas','Courier New',monospace; font-size: 11px;"
        )
        root.addWidget(self.log_list, stretch=1)

        self.setMinimumHeight(280)
        self.setMaximumHeight(520)

        self._count_success = 0
        self._count_rejected = 0
        self._refresh_static_config_summary()
        self._summary_gallery.setText(
            "Снимок галереи придёт с видеопотока (периодически, ~каждые 50 кадров обработки)."
        )
        self._summary_counts.setText("")
        self._summary_pending.setText("")

    def _refresh_static_config_summary(self) -> None:
        g = config.settings.tracker.gallery
        self._summary_config.setText(
            f"Конфиг: sim≥{g.similarity_threshold:.3f} | "
            f"пространств. вес={g.spatial_penalty_weight:.2f} | "
            f"история emb={g.embedding_history} | "
            f"max dead={g.max_gallery_size} | "
            f"TTL={g.max_age_seconds:.0f}s | "
            f"min conf галереи={g.min_conf_for_gallery:.2f}"
        )

    def _update_gallery_header(self, event_data: dict) -> None:
        enabled = event_data.get("enabled", True)
        if not enabled:
            self._summary_gallery.setText("Галерея Re-ID: выключена (config.tracker.gallery.enabled=False)")
            self._summary_counts.setText("")
            self._summary_pending.setText("")
            return

        dead = event_data.get("dead_pool_count", 0)
        live = event_data.get("live_embeddings_count", 0)
        aliases = event_data.get("alias_map_count", 0)
        rev = event_data.get("reversed_map_count", 0)
        skip_emb = event_data.get("skipped_lost_no_embedding", 0)
        thr = event_data.get("similarity_threshold")
        spw = event_data.get("spatial_penalty_weight")
        thr_s = f"{thr:.3f}" if isinstance(thr, (int, float)) else "—"
        spw_s = f"{spw:.2f}" if isinstance(spw, (int, float)) else "—"

        self._summary_gallery.setText(
            f"Галерея: вкл | порог кадра: sim≥{thr_s} | пространств. вес={spw_s}"
        )
        self._summary_counts.setText(
            f"Память: живые emb={live} | dead_pool={dead} | "
            f"alias_map (склейки в памяти)={aliases} | reversed={rev} | "
            f"lost без emb (не в dead)={skip_emb}"
        )

        pending = event_data.get("pending_ids") or []
        if not pending:
            self._summary_pending.setText("Ожидают склейки (dead_pool): —")
        else:
            preview = pending[: self._PENDING_PREVIEW_MAX]
            extra = len(pending) - len(preview)
            tail = f" … +{extra} id" if extra > 0 else ""
            self._summary_pending.setText(
                "Ожидают склейки (dead_pool): " + ", ".join(str(i) for i in preview) + tail
            )

    @staticmethod
    def _resolve_ids(event_data: dict) -> tuple[Optional[int], Optional[int]]:
        """Возвращает (канонический/целевой ID, ID трекера BoxMOT)."""
        status = event_data.get("status", "")
        if status == "SUCCESS":
            c = event_data.get("canonical_id")
            t = event_data.get("tracker_id")
            if c is None:
                c = event_data.get("old_id")
            if t is None:
                t = event_data.get("new_id")
            return c, t
        if status == "REJECTED":
            return event_data.get("potential_old_id"), event_data.get("tracker_id")
        return event_data.get("old_id"), event_data.get("new_id")

    @staticmethod
    def _resolve_score(event_data: dict) -> float:
        v = event_data.get("stitch_score", event_data.get("score", 0.0))
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    @pyqtSlot(dict)
    def add_event(self, event_data: dict):
        status = event_data.get("status", "")

        if status == "GALLERY_UPDATE":
            self._update_gallery_header(event_data)
            self.setTitle(
                f"Re-ID / Identity | dead={event_data.get('dead_pool_count', 0)} "
                f"live={event_data.get('live_embeddings_count', 0)}"
            )
            return

        ts = time.strftime("%H:%M:%S")
        score = self._resolve_score(event_data)
        thr = event_data.get("similarity_threshold")
        thr_f: Optional[float] = None
        if isinstance(thr, (int, float)):
            thr_f = float(thr)

        ptype = str(event_data.get("type", "person")).upper()
        frame_id = event_data.get("frame_id")
        fr_s = str(frame_id) if frame_id is not None else "—"
        conf = event_data.get("conf")
        conf_s = f"{float(conf):.2f}" if isinstance(conf, (int, float)) else "—"
        cam = event_data.get("camera_id", "—")
        bbox_s = _fmt_bbox(event_data.get("bbox"))
        rs = event_data.get("reid_status", status)

        id_a, id_b = self._resolve_ids(event_data)

        if status == "SUCCESS":
            self._count_success += 1
            self._stats_success.setText(f"Склейки в лог (сессия): {self._count_success}")
            thr_part = ""
            if thr_f is not None:
                ok = "да" if score >= thr_f else "нет"
                thr_part = f" | порог {thr_f:.3f} (выше порога: {ok})"
            msg = (
                f"[{ts}] OK fr={fr_s} | трек #{id_b} → канон #{id_a} | "
                f"score={score:.3f}{thr_part} | {ptype} conf={conf_s} | cam={cam} | bbox {bbox_s} | {rs}"
            )
            item = QListWidgetItem(msg)
            item.setForeground(Qt.GlobalColor.green)
        elif status == "REJECTED":
            self._count_rejected += 1
            self._stats_rejected.setText(f"Near-miss в лог (сессия): {self._count_rejected}")
            thr_part = ""
            if thr_f is not None:
                thr_part = f" (порог {thr_f:.3f}, не хватает {thr_f - score:.3f})"
            msg = (
                f"[{ts}] NEAR-MISS fr={fr_s} | трек #{id_b} ≈ dead #{id_a} | "
                f"score={score:.3f}{thr_part} | {ptype} conf={conf_s} | cam={cam} | bbox {bbox_s} | {rs}"
            )
            item = QListWidgetItem(msg)
            if score > 0.6:
                item.setForeground(Qt.GlobalColor.yellow)
            else:
                item.setForeground(Qt.GlobalColor.gray)
        else:
            return

        self.log_list.insertItem(0, item)
        while self.log_list.count() > self._LOG_LIMIT:
            self.log_list.takeItem(self.log_list.count() - 1)
