# Meta and Feishu field notes

- `instagram_business_manage_insights` is relevant to managed-account Insights API access. It does not by itself grant comprehensive private analytics for a collaborating creator.
- Meta Business Suite UI can surface performance for collaboration content. Capture only fields visible on the active page and retain the retrieval date.
- Feishu synchronization should use the `频道名` + `发布日期` key, then re-read the affected records. Do not use an inferred profile URL as an exact post/video URL.
- Existing Varla Base schema commonly includes `发布日期`, `频道名`, `平台`, `发布车型`, `播放量`, `点赞量`, `评论数量/相关程度`, `视频描述`, `合作/视频问题`, and `视频链接`.
