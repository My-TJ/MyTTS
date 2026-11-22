from piper_tts_studio.document import split_text


def test_split_text_preserves_complete_text_content():
    text = "First paragraph. It has two sentences.\n\nSecond paragraph."
    chunks = split_text(text, 100)
    reconstructed = " ".join(chunks)
    assert "First paragraph" in reconstructed
    assert "Second paragraph" in reconstructed


def test_split_text_rejects_empty_and_invalid_chunk_size():
    assert split_text("", 900) == []
    try:
        split_text("text", 99)
    except ValueError:
        return
    raise AssertionError("Invalid chunk size should fail")
