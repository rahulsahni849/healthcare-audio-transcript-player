import pytest

from app.services.media import ByteRange, UnsatisfiableRange, parse_range

SIZE = 1000


def test_no_header_returns_none():
    assert parse_range(None, SIZE) is None
    assert parse_range("", SIZE) is None


def test_simple_range():
    assert parse_range("bytes=0-99", SIZE) == ByteRange(0, 99)


def test_open_ended_range():
    assert parse_range("bytes=500-", SIZE) == ByteRange(500, 999)


def test_end_clamped_to_file_size():
    assert parse_range("bytes=900-5000", SIZE) == ByteRange(900, 999)


def test_suffix_range():
    assert parse_range("bytes=-500", SIZE) == ByteRange(500, 999)


def test_suffix_larger_than_file_returns_whole_file():
    assert parse_range("bytes=-5000", SIZE) == ByteRange(0, 999)


def test_suffix_zero_unsatisfiable():
    with pytest.raises(UnsatisfiableRange):
        parse_range("bytes=-0", SIZE)


def test_start_beyond_file_unsatisfiable():
    with pytest.raises(UnsatisfiableRange):
        parse_range("bytes=1000-", SIZE)
    with pytest.raises(UnsatisfiableRange):
        parse_range("bytes=2000-3000", SIZE)


def test_invalid_unit_returns_none():
    assert parse_range("items=0-99", SIZE) is None
    assert parse_range("garbage", SIZE) is None


def test_empty_groups_returns_none():
    assert parse_range("bytes=-", SIZE) is None


def test_zero_byte_file_unsatisfiable():
    with pytest.raises(UnsatisfiableRange):
        parse_range("bytes=0-", 0)
