"""Shared data models for video breakdown, exports, and Feishu sync."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


TABLE_FIELDS = ["镜号", "景别", "拍摄手法", "画面", "画面说明", "备注", "台词", "英文台词"]
FEISHU_TABLE_FIELDS = ["时间", "画面参考（竖屏9:16）", "画面描述", "角色动作 / 镜头运动", "对话 / 声音", "备注"]
FEISHU_FIELD_MAP = {
    "time": "时间",
    "visual_reference": "画面参考（竖屏9:16）",
    "scene_description": "画面描述",
    "action_camera": "角色动作 / 镜头运动",
    "dialogue_sound": "对话 / 声音",
    "notes": "备注",
}


class VideoInfo(BaseModel):
    file_name: str
    duration: str = "00:00"
    aspect_ratio: str = "Unknown"
    resolution: str = "Unknown"


class Shot(BaseModel):
    shot_id: str
    start_time: str
    end_time: str
    duration: str
    shot_size: str = "中景"
    camera_method: str = "固定机位"
    frame_path: str = ""
    visual_description: str = ""
    notes: str = ""
    dialogue_cn: str = ""
    dialogue_en: str = ""
    sync_status: str = "pending"


class Storyboard(BaseModel):
    job_id: str
    mode: Literal["breakdown", "emoto_reference"] = "breakdown"
    product_model: str = ""
    video_info: VideoInfo
    shots: list[Shot] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    warnings: list[str] = Field(default_factory=list)

    def to_table_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "镜号": shot.shot_id,
                "景别": shot.shot_size,
                "拍摄手法": shot.camera_method,
                "画面": shot.frame_path,
                "画面说明": shot.visual_description,
                "备注": shot.notes,
                "台词": shot.dialogue_cn,
                "英文台词": shot.dialogue_en,
                "开始时间": shot.start_time,
                "结束时间": shot.end_time,
                "时长": shot.duration,
                "视频名称": self.video_info.file_name,
                "状态": "To Do",
                "创建时间": self.created_at,
            }
            for shot in self.shots
        ]

    def to_feishu_payload(self) -> dict[str, Any]:
        return {
            "title": f"{self.video_info.file_name} 分镜脚本",
            "format": self.video_info.aspect_ratio,
            "duration": self.video_info.duration,
            "style": self.mode,
            "rows": [
                {
                    "time": f"{shot.start_time}-{shot.end_time}",
                    "visual_reference": shot.frame_path,
                    "scene_description": shot.visual_description,
                    "action_camera": f"{shot.shot_size}；{shot.camera_method}",
                    "dialogue_sound": shot.dialogue_cn or shot.dialogue_en,
                    "notes": shot.notes,
                }
                for shot in self.shots
            ],
        }


class SyncRequest(BaseModel):
    job_id: str
    keep_job_ids: list[str] = Field(default_factory=list)
    storyboard: Storyboard
    target: Literal["bitable", "doc", "both"] = "both"
    feishu_doc_url: str = ""
    feishu_bitable_url: str = ""
    feishu_user_access_token: str = ""
    cleanup_after_sync: bool = False


class SyncResult(BaseModel):
    ok: bool
    success_count: int = 0
    failed_count: int = 0
    errors: list[str] = Field(default_factory=list)
    bitable_url: str | None = None
    doc_url: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
