from pathlib import Path

from ttsforge.conversion import ConversionOptions, ConversionResult, TTSConverter
from ttsforge.input_reader import InputReader
from ttsforge.text_postprocessing import (
    TextPostprocessOptions,
    postprocess_extracted_text,
    resolve_text_postprocess_options,
)


def test_strips_epub_chapter_marker_with_leading_whitespace() -> None:
    text = " <<CHAPTER: Test Chapter>>\n\nThis is the content."
    result = postprocess_extracted_text(text)
    assert result == "This is the content."


def test_replaces_literal_ellipsis_without_touching_ssmd_breaks() -> None:
    text = "Wait... Then pause...c Next...s Here...p Done...500ms End..."
    result = postprocess_extracted_text(text)
    expected = "Wait\u2026 Then pause...c Next...s Here...p Done...500ms End\u2026"
    assert result == expected


def test_subchapter_markers_are_inert_by_default() -> None:
    text = "Before\n***\nAfter"
    result = postprocess_extracted_text(text)
    assert result == text


def test_subchapter_marker_lines_become_paragraph_pauses() -> None:
    text = "Before\n  section, break  \nAfter"
    result = postprocess_extracted_text(
        text,
        TextPostprocessOptions(subchapter_markers=("section, break",)),
    )
    assert result == "Before\n...p\nAfter"


def test_cli_markers_override_config_markers() -> None:
    options = resolve_text_postprocess_options(
        {"subchapter_markers": ["***"]},
        subchapter_markers=("# # #",),
    )
    assert options.subchapter_markers == ("# # #",)
def test_replaces_non_book_abbreviations_when_enabled() -> None:
    options = TextPostprocessOptions(replace_non_book_abbreviations=True)

    result = postprocess_extracted_text(
        "No. 5 was missing.\nno. 6 waited. No.",
        options,
    )

    assert result == "No–. 5 was missing.\nno–. 6 waited. No–."


def test_replaces_quoted_non_book_abbreviations_when_enabled() -> None:
    options = TextPostprocessOptions(replace_non_book_abbreviations=True)

    result = postprocess_extracted_text(
        '"No." Cadvan smiled. No." The Hull moved closer.',
        options,
    )

    assert result == '"No–." Cadvan smiled. No–." The Hull moved closer.'


def test_leaves_non_book_abbreviations_when_disabled() -> None:
    assert postprocess_extracted_text("No. 10") == "No. 10"


def test_non_book_abbreviation_replacement_requires_standalone_word() -> None:
    options = TextPostprocessOptions(replace_non_book_abbreviations=True)

    result = postprocess_extracted_text(
        "No.5 and Nobody. Piano. no.one knows.",
        options,
    )

    assert result == "No.5 and Nobody. Piano. no.one knows."


def test_direct_ssmd_input_is_not_postprocessed(tmp_path) -> None:
    content = "One step.\n***\nWait..."
    ssmd_file = tmp_path / "chapter.ssmd"
    ssmd_file.write_text(content, encoding="utf-8")

    reader = InputReader(
        ssmd_file,
        postprocess_options=TextPostprocessOptions(subchapter_markers=("***",)),
    )

    chapters = reader.get_chapters()
    assert chapters[0].is_ssmd is True
    assert chapters[0].text == content


def test_input_reader_applies_non_book_abbreviation_replacement(
    tmp_path: Path,
) -> None:
    input_file = tmp_path / "sample.txt"
    input_file.write_text("Title: Test\n\nNo. 3 waited.", encoding="utf-8")
    options = TextPostprocessOptions(replace_non_book_abbreviations=True)

    reader = InputReader(input_file, postprocess_options=options)

    assert reader.get_chapters()[0].text.endswith("No–. 3 waited.")


def test_converter_convert_text_uses_postprocess_options(
    monkeypatch,
    tmp_path: Path,
) -> None:
    converter = TTSConverter(
        ConversionOptions(
            text_postprocess_options=TextPostprocessOptions(
                replace_non_book_abbreviations=True
            )
        )
    )
    captured_content: list[str] = []

    def fake_convert_chapters(chapters, output_path):
        captured_content.append(chapters[0].content)
        return ConversionResult(success=True, output_path=output_path)

    monkeypatch.setattr(converter, "convert_chapters", fake_convert_chapters)

    converter.convert_text("No. 8", tmp_path / "out.wav")

    assert captured_content == ["No–. 8"]
