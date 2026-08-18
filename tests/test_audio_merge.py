from pathlib import Path
from types import SimpleNamespace

import pytest

from ttsforge import audio_merge
from ttsforge.audio_merge import AudioMerger, MergeMeta, _ffconcat_path


def test_ffconcat_path_uses_forward_slashes_and_escapes_quotes(
    tmp_path: Path,
) -> None:
    wav_path = tmp_path / "chapter's file.wav"

    result = _ffconcat_path(wav_path)

    assert result.startswith(tmp_path.absolute().as_posix())
    assert "'\\''" in result


def test_merge_failure_includes_ffmpeg_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commands: list[list[str]] = []

    def fake_create_process(cmd: list[str], **kwargs: object) -> SimpleNamespace:
        commands.append(cmd)
        assert kwargs == {"capture_output": True}
        return SimpleNamespace(returncode=1, stderr="concat input failed")

    monkeypatch.setattr(audio_merge, "get_ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(audio_merge, "create_process", fake_create_process)

    output_path = tmp_path / "book.mp3"
    chapter_file = tmp_path / "chapter 1.wav"
    merger = AudioMerger(log=lambda message, level="info": None)

    with pytest.raises(RuntimeError, match="concat input failed"):
        merger.merge_chapter_wavs(
            [chapter_file],
            [1.0],
            ["Chapter 1"],
            output_path,
            MergeMeta(fmt="mp3", silence_between_chapters=0),
        )

    assert commands
    concat_file = output_path.with_suffix(".concat.txt")
    assert commands[0][7] == str(concat_file)
    assert concat_file.exists()
