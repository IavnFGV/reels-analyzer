from reels_analyzer.reviewer import _normalize_summary, _parse_json_response


def test_parse_json_response_accepts_markdown_fence() -> None:
    content = """```json
{
  "content_type": "social",
  "hook_type": "curiosity"
}
```"""

    parsed = _parse_json_response(content)

    assert parsed == {
        "content_type": "social",
        "hook_type": "curiosity",
    }


def test_normalize_summary_falls_back_to_russian_for_non_russian_output() -> None:
    summary = _normalize_summary("This summary is unexpectedly in English.")

    assert summary == "Короткий ролик без краткого резюме."
