"""
Tests for split_chunks — text segmentation for encoding pipeline.

Pure function, no dependencies.
"""

from towow.field.chunker import split_chunks


class TestSplitChunks:

    def test_empty_string(self):
        assert split_chunks("") == []

    def test_whitespace_only(self):
        assert split_chunks("   ") == []

    def test_short_text_single_chunk(self):
        text = "Hello world"
        result = split_chunks(text, max_chars=256)
        assert result == ["Hello world"]

    def test_exact_boundary(self):
        text = "x" * 256
        result = split_chunks(text, max_chars=256)
        assert result == [text]

    def test_long_text_splits(self):
        text = "First sentence. Second sentence. Third sentence."
        result = split_chunks(text, max_chars=20)
        assert len(result) > 1
        # All chunks non-empty
        for chunk in result:
            assert len(chunk) > 0

    def test_chinese_sentence_boundaries(self):
        text = "第一句话。第二句话。第三句话。"
        result = split_chunks(text, max_chars=10)
        assert len(result) > 1

    def test_merges_short_sentences(self):
        """Adjacent short sentences should be merged into one chunk."""
        text = "A. B. C. D. E."
        result = split_chunks(text, max_chars=50)
        # Should merge rather than producing 5 tiny chunks
        assert len(result) < 5

    def test_no_sentence_boundaries_returns_whole(self):
        """Long text without sentence boundaries returns as single chunk."""
        text = "a" * 500
        result = split_chunks(text, max_chars=256)
        # No sentence boundary found → returns whole text
        assert len(result) == 1
        assert result[0] == text

    def test_preserves_all_content(self):
        """Concatenated chunks should contain all original content."""
        text = "First sentence. Second sentence. Third very long sentence that goes on."
        result = split_chunks(text, max_chars=30)
        joined = " ".join(result)
        # Every word from original should appear somewhere
        for word in text.split():
            word_clean = word.strip(".")
            assert any(word_clean in chunk for chunk in result)

    def test_default_max_chars_is_256(self):
        short = "x" * 256
        assert split_chunks(short) == [short]
        long = "a. " * 200  # ~600 chars with sentence boundaries
        assert len(split_chunks(long)) > 1
