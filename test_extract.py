import sys
from unittest.mock import MagicMock

# Mock out external dependencies that are not available in the air-gapped environment
sys.modules['httpx'] = MagicMock()
sys.modules['fitz'] = MagicMock()
sys.modules['playwright'] = MagicMock()
sys.modules['playwright.async_api'] = MagicMock()

import pytest
from extract import chunk_text

def test_chunk_text_empty_string():
    """Test that an empty string returns an empty list."""
    assert chunk_text("", chunk_size=10, overlap=5) == []

def test_chunk_text_none():
    """Test that None returns an empty list."""
    assert chunk_text(None, chunk_size=10, overlap=5) == []

def test_chunk_text_smaller_than_chunk_size():
    """Test when the text is smaller than the chunk size."""
    text = "hello"
    chunks = chunk_text(text, chunk_size=10, overlap=5)
    assert len(chunks) == 1
    assert chunks[0] == "hello"

def test_chunk_text_exact_chunk_size():
    """Test when the text is exactly the chunk size."""
    text = "hello12345"
    chunks = chunk_text(text, chunk_size=10, overlap=5)
    assert len(chunks) == 1
    assert chunks[0] == "hello12345"

def test_chunk_text_no_overlap():
    """Test chunking with 0 overlap."""
    text = "abcdefghij"
    chunks = chunk_text(text, chunk_size=5, overlap=0)
    assert len(chunks) == 2
    assert chunks[0] == "abcde"
    assert chunks[1] == "fghij"

def test_chunk_text_with_overlap():
    """Test chunking with overlap."""
    text = "abcdefghij"
    chunks = chunk_text(text, chunk_size=6, overlap=2)

    # Chunk 1: 'abcdef'
    # Next start: end - overlap = 6 - 2 = 4 -> index 4 is 'e'
    # Chunk 2: 'efghij'
    assert len(chunks) == 2
    assert chunks[0] == "abcdef"
    assert chunks[1] == "efghij"

def test_chunk_text_multiple_chunks():
    """Test when text needs to be split into multiple chunks."""
    text = "1234567890abcdef"
    # chunk_size = 5, overlap = 2
    # c1: 0-5  -> '12345'   (start=0, end=5) -> next_start = 5-2 = 3
    # c2: 3-8  -> '45678'   (start=3, end=8) -> next_start = 8-2 = 6
    # c3: 6-11 -> '7890a'   (start=6, end=11) -> next_start = 11-2 = 9
    # c4: 9-14 -> '0abcd'   (start=9, end=14) -> next_start = 14-2 = 12
    # c5: 12-16 -> 'cdef'   (start=12, end=17, bounded to length 16)

    chunks = chunk_text(text, chunk_size=5, overlap=2)
    assert len(chunks) == 5
    assert chunks[0] == "12345"
    assert chunks[1] == "45678"
    assert chunks[2] == "7890a"
    assert chunks[3] == "0abcd"
    assert chunks[4] == "cdef"

def test_chunk_text_default_parameters():
    """Test using the default parameters for chunk_size and overlap."""
    text = "A" * 1500
    chunks = chunk_text(text)
    assert len(chunks) == 2
    assert len(chunks[0]) == 1000
    assert len(chunks[1]) == 700
