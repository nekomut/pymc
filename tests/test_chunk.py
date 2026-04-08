"""Tests for src/mcbe/chunk.py — sub-chunk parsing."""

from __future__ import annotations

import struct

import pytest

from mcbe.chunk import (
    _parse_block_storage,
    _read_varint32,
    parse_level_chunk_top_blocks,
    parse_sub_chunk,
)


# ── Helpers ──────────────────────────────────────────────────────


def _write_varint32(value: int) -> bytes:
    """Encode a varint32."""
    out = bytearray()
    value &= 0xFFFFFFFF
    while value > 0x7F:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def _build_block_storage(
    runtime_ids: list[int],
    bits_per_block: int,
) -> bytes:
    """Build a raw block storage layer from runtime IDs.

    *runtime_ids* must have exactly 4096 entries.
    """
    assert len(runtime_ids) == 4096

    # Deduplicate to build palette.
    seen: dict[int, int] = {}
    indices: list[int] = []
    for rid in runtime_ids:
        if rid not in seen:
            seen[rid] = len(seen)
        indices.append(seen[rid])
    palette = list(seen.keys())

    header = (bits_per_block << 1) | 1  # is_runtime=1
    out = bytearray([header])

    if bits_per_block == 0:
        # Single-block shortcut.
        out += _write_varint32(1)
        out += _write_varint32(palette[0])
        return bytes(out)

    # Pack indices into uint32 words.
    blocks_per_word = 32 // bits_per_block
    num_words = -(-4096 // blocks_per_word)
    mask = (1 << bits_per_block) - 1

    for w in range(num_words):
        word = 0
        for j in range(blocks_per_word):
            idx = w * blocks_per_word + j
            if idx < 4096:
                word |= (indices[idx] & mask) << (j * bits_per_block)
        out += struct.pack("<I", word)

    # Write palette.
    out += _write_varint32(len(palette))
    for rid in palette:
        out += _write_varint32(rid)

    return bytes(out)


# ── Tests ────────────────────────────────────────────────────────


class TestReadVarint32:
    def test_single_byte(self):
        val, off = _read_varint32(b"\x05", 0)
        assert val == 5
        assert off == 1

    def test_two_bytes(self):
        val, off = _read_varint32(b"\x80\x01", 0)
        assert val == 128
        assert off == 2

    def test_with_offset(self):
        val, off = _read_varint32(b"\xff\x03\x00", 1)
        assert val == 3
        assert off == 2


class TestParseBlockStorage:
    def test_single_block(self):
        """bitsPerBlock=0 → all blocks are the same."""
        ids = [42] * 4096
        raw = _build_block_storage(ids, bits_per_block=0)
        result, _, _ = _parse_block_storage(raw, 0)
        assert len(result) == 4096
        assert all(r == 42 for r in result)

    def test_two_palette_entries(self):
        """bitsPerBlock=1 → two block types."""
        # Even x -> 0, odd x -> 1
        ids = []
        for x in range(16):
            for z in range(16):
                for y in range(16):
                    ids.append(10 if x % 2 == 0 else 20)
        raw = _build_block_storage(ids, bits_per_block=1)
        result, _, _ = _parse_block_storage(raw, 0)
        assert len(result) == 4096
        # Verify pattern: index = (x << 8) | (z << 4) | y
        for x in range(16):
            for z in range(16):
                for y in range(16):
                    idx = (x << 8) | (z << 4) | y
                    expected = 10 if x % 2 == 0 else 20
                    assert result[idx] == expected, f"mismatch at x={x} z={z} y={y}"

    def test_four_bits(self):
        """bitsPerBlock=4 → up to 16 palette entries."""
        ids = [i % 10 for i in range(4096)]
        raw = _build_block_storage(ids, bits_per_block=4)
        result, _, _ = _parse_block_storage(raw, 0)
        assert result == ids


class TestParseSubChunk:
    def test_version_8(self):
        """Version 8: single storage layer."""
        ids = [7] * 4096
        storage = _build_block_storage(ids, bits_per_block=0)
        data = bytes([8]) + storage
        result = parse_sub_chunk(data)
        assert result is not None
        rids, _, _ = result
        assert len(rids) == 4096
        assert all(r == 7 for r in rids)

    def test_version_9(self):
        """Version 9: storage_count + layers."""
        ids = [3] * 4096
        storage = _build_block_storage(ids, bits_per_block=0)
        # storage_count=1
        data = bytes([9, 1]) + storage
        result = parse_sub_chunk(data)
        assert result is not None
        rids, _, _ = result
        assert all(r == 3 for r in rids)

    def test_version_9_two_layers(self):
        """Version 9 with 2 layers: only layer 0 is returned."""
        layer0 = _build_block_storage([5] * 4096, bits_per_block=0)
        layer1 = _build_block_storage([99] * 4096, bits_per_block=0)
        data = bytes([9, 2]) + layer0 + layer1
        result = parse_sub_chunk(data)
        assert result is not None
        rids, _, _ = result
        assert all(r == 5 for r in rids)

    def test_unknown_version(self):
        """Unknown version returns None."""
        assert parse_sub_chunk(bytes([255, 0, 0, 0])) is None

    def test_empty_data(self):
        assert parse_sub_chunk(b"") is None


class TestParseLevelChunkTopBlocks:
    def test_single_sub_chunk_all_stone(self):
        """Single sub-chunk filled with stone → top = stone everywhere."""
        palette = ["minecraft:air", "minecraft:stone"]
        ids = [1] * 4096  # all stone (runtime ID 1)
        storage = _build_block_storage(ids, bits_per_block=1)
        raw_payload = bytes([8]) + storage

        top = parse_level_chunk_top_blocks(raw_payload, 1, palette)
        assert top is not None
        assert len(top) == 256
        assert all(b == "minecraft:stone" for b in top)

    def test_two_sub_chunks_top_wins(self):
        """Higher sub-chunk's blocks take priority."""
        palette = ["minecraft:air", "minecraft:stone", "minecraft:dirt"]

        # Sub-chunk 0: all stone
        ids0 = [1] * 4096
        sc0 = _build_block_storage(ids0, bits_per_block=2)

        # Sub-chunk 1: air except y=0 which is dirt
        ids1 = [0] * 4096
        for x in range(16):
            for z in range(16):
                ids1[(x << 8) | (z << 4) | 0] = 2  # dirt at y=0
        sc1 = _build_block_storage(ids1, bits_per_block=2)

        raw_payload = bytes([8]) + sc0 + bytes([8]) + sc1

        top = parse_level_chunk_top_blocks(raw_payload, 2, palette)
        assert top is not None
        # Sub-chunk 1 has dirt at y=0, which is higher than sub-chunk 0.
        assert all(b == "minecraft:dirt" for b in top)

    def test_empty_payload(self):
        assert parse_level_chunk_top_blocks(b"", 0, ["minecraft:air"]) is None
