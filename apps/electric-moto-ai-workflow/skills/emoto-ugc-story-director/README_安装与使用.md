# 电摩 UGC 剧情导演 Skill

## 已安装位置

```text
C:\Users\<your-user>\.codex\skills\emoto-ugc-story-director
```

## 使用方式

直接在 Codex 中提出类似需求：

```text
用电摩 UGC 剧情导演，给 VARLA M7S 写一个双10秒家庭礼物反转。
```

也可以只说：

```text
再来一个电摩剧情，按之前的强表情、多镜头、自然移动衔接来。
```

Skill 会自动输出人物三视图、场景选择、首帧、完整视频提示词、对白锁定、产品强绑定以及 TikTok/Instagram 文案。

## 结构检查

```powershell
python "C:\Users\<your-user>\.codex\skills\emoto-ugc-story-director\scripts\validate_prompt.py" "C:\完整路径\提示词.md"
```

检查内容包括时间轴、镜头数量、对白锁定、产品引用、iPhone质感、面部表演、小动作、身体反应和镜头移动连续性。
