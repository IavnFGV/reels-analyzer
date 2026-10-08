from reels_analyzer.insights import ChannelInsightsAnalyzer


def test_analyze_rows_adds_performance_and_hook_fields() -> None:
    analyzer = ChannelInsightsAnalyzer()
    rows = [
        {
            "video_id": "1",
            "upload_date": "20250201",
            "view_count": "1000",
            "duration_sec": "80",
            "scene_count": "3",
            "words_per_second": "1.5",
            "first_phrase": "Где взять силы и энергию сегодня?",
            "title": "",
            "summary": "",
            "transcription_skipped_reason": "",
        },
        {
            "video_id": "2",
            "upload_date": "20250202",
            "view_count": "9000",
            "duration_sec": "150",
            "scene_count": "9",
            "words_per_second": "2.8",
            "first_phrase": "Что произойдет очень скоро между вами?",
            "title": "",
            "summary": "",
            "transcription_skipped_reason": "",
        },
        {
            "video_id": "3",
            "upload_date": "20250301",
            "view_count": "2000",
            "duration_sec": "20",
            "scene_count": "1",
            "words_per_second": "0.0",
            "first_phrase": "",
            "title": "Кто вас тайно любит",
            "summary": "",
            "transcription_skipped_reason": "feature_disabled",
        },
    ]

    enriched = analyzer.analyze_rows(rows)

    assert enriched[0]["performance_cohort"] == "2025-02"
    assert enriched[0]["performance_baseline_view_count"] == "5000.00"
    assert enriched[0]["performance_bucket"] == "underperformer"
    assert enriched[0]["hook_subject"] == "energy"
    assert enriched[0]["hook_format"] == "timeline"
    assert enriched[0]["hook_emotion"] in {"neutral", "hope", "curiosity"}

    assert enriched[1]["performance_bucket"] == "winner"
    assert enriched[1]["hook_subject"] in {"relationship", "future"}
    assert enriched[1]["hook_specificity"] in {"medium", "high"}
    assert "strong_hook" in enriched[1]["insight_tags"]
    assert "high_scene_count" in enriched[1]["insight_tags"]
    assert "dense_speech" in enriched[1]["insight_tags"]

    assert enriched[2]["performance_cohort"] == "2025-03"
    assert enriched[2]["hook_format"] == "reveal"
    assert enriched[2]["hook_emotion"] == "hope"
    assert "no_transcript" in enriched[2]["insight_tags"]


def test_analyze_rows_uses_global_baseline_when_month_unknown() -> None:
    analyzer = ChannelInsightsAnalyzer()
    rows = [
        {
            "video_id": "1",
            "upload_date": "",
            "view_count": "1000",
            "first_phrase": "Что будет дальше?",
        },
        {
            "video_id": "2",
            "upload_date": "",
            "view_count": "4000",
            "first_phrase": "Что будет дальше?",
        },
    ]

    enriched = analyzer.analyze_rows(rows)

    assert enriched[0]["performance_cohort"] == "unknown"
    assert enriched[0]["performance_baseline_view_count"] == "2500.00"
    assert enriched[1]["performance_bucket"] == "winner"
