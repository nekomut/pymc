"""Sub-chunk parsing for Minecraft Bedrock Edition.

Decodes the palette-based block storage format used in LevelChunk
and SubChunk packets. Only extracts the top-most non-air block at
each (x, z) column for map rendering.
"""

from __future__ import annotations

import logging
import struct

logger = logging.getLogger(__name__)

AIR = "minecraft:air"


def _read_varint32(data: bytes, offset: int) -> tuple[int, int]:
    """Read a varint32 from *data* at *offset*. Returns (value, new_offset)."""
    result = 0
    for i in range(0, 35, 7):
        if offset >= len(data):
            raise EOFError("unexpected end of data reading varint32")
        b = data[offset]
        offset += 1
        result |= (b & 0x7F) << i
        if (b & 0x80) == 0:
            return result & 0xFFFFFFFF, offset
    raise ValueError("varint32 overflows 5 bytes")


def _parse_block_storage(
    data: bytes, offset: int,
) -> tuple[list[int], int, list[str] | None]:
    """Parse one block storage layer.

    Returns ``(palette_indices[4096], new_offset, local_palette_or_None)``.

    When ``is_runtime`` (header bit 0) is 1, palette entries are varint32
    runtime IDs and *local_palette* is ``None``.  When ``is_runtime`` is 0
    the palette entries are NBT block states; *local_palette* is then a list
    of block names and the returned indices index into it.

    Indices are in XZY order: ``index = (x << 8) | (z << 4) | y``.
    """
    if offset >= len(data):
        raise EOFError("no storage header")
    header = data[offset]
    offset += 1
    bits_per_block = header >> 1
    is_runtime = header & 1

    if bits_per_block == 0:
        # Single-block shortcut: palette has exactly 1 entry.
        if is_runtime:
            palette_size, offset = _read_varint32(data, offset)
            if palette_size >= 1:
                single_id, offset = _read_varint32(data, offset)
                for _ in range(palette_size - 1):
                    _, offset = _read_varint32(data, offset)
            else:
                single_id = 0
            return [single_id] * 4096, offset, None
        else:
            # NBT palette with 1 entry.
            palette_size, offset = _read_varint32(data, offset)
            name = AIR
            for i in range(palette_size):
                tag, offset = _read_nbt_block(data, offset)
                if i == 0:
                    name = tag
            return [0] * 4096, offset, [name]

    blocks_per_word = 32 // bits_per_block
    num_words = -(-4096 // blocks_per_word)  # ceil division
    mask = (1 << bits_per_block) - 1

    # Batch-read uint32 words.
    end = offset + num_words * 4
    if end > len(data):
        raise EOFError(f"not enough data for {num_words} words at offset {offset}")
    words = struct.unpack_from(f"<{num_words}I", data, offset)
    offset = end

    # Unpack palette indices from packed words.
    indices = [0] * 4096
    idx = 0
    for word in words:
        for j in range(blocks_per_word):
            if idx >= 4096:
                break
            indices[idx] = (word >> (j * bits_per_block)) & mask
            idx += 1

    # Read palette.
    palette_size, offset = _read_varint32(data, offset)

    if is_runtime:
        palette = [0] * palette_size
        for i in range(palette_size):
            palette[i], offset = _read_varint32(data, offset)
        # Map indices to runtime IDs.
        runtime_ids = [
            palette[i] if i < palette_size else 0
            for i in indices
        ]
        return runtime_ids, offset, None
    else:
        # NBT palette: each entry is a compound with "name" and "states".
        local_palette: list[str] = []
        for _ in range(palette_size):
            name, offset = _read_nbt_block(data, offset)
            local_palette.append(name)
        return indices, offset, local_palette


def _read_nbt_block(data: bytes, offset: int) -> tuple[str, int]:
    """Read a single NBT block state entry and return (block_name, new_offset)."""
    from io import BytesIO
    from mcbe.nbt.codec import _decode_root, NetworkLittleEndian
    try:
        buf = BytesIO(data[offset:])
        tag = _decode_root(buf, NetworkLittleEndian, allow_zero=False)
        consumed = buf.tell()
        name = tag.get("name", AIR) if isinstance(tag, dict) else AIR
        return name, offset + consumed
    except Exception:
        # Fallback: try to find the next compound tag boundary.
        return AIR, offset + 1


def parse_sub_chunk(
    data: bytes, offset: int = 0,
) -> tuple[list[int], int, list[str] | None] | None:
    """Parse a single versioned sub-chunk (layer 0 only).

    Returns ``(ids[4096], bytes_consumed, local_palette_or_None)`` or
    ``None`` on failure.  When *local_palette* is not ``None``, the ids
    are indices into it (NBT palette mode).  Otherwise they are runtime IDs.
    """
    if offset >= len(data):
        return None

    version = data[offset]
    offset += 1

    if version == 1:
        try:
            ids, offset, lp = _parse_block_storage(data, offset)
            return ids, offset, lp
        except Exception:
            return None

    if version in (8, 9):
        storage_count = 1
        if version == 9:
            if offset >= len(data):
                return None
            storage_count = data[offset]
            offset += 1

        if storage_count < 1:
            return None

        try:
            ids, offset, lp = _parse_block_storage(data, offset)
        except Exception:
            return None

        # Skip remaining layers (waterlog, etc.).
        for _ in range(storage_count - 1):
            try:
                _, offset, _ = _parse_block_storage(data, offset)
            except Exception:
                break

        return ids, offset, lp

    logger.debug("unknown sub-chunk version %d at offset %d", version, offset - 1)
    return None


def parse_level_chunk_top_blocks(
    raw_payload: bytes,
    sub_chunk_count: int,
    block_palette: list[str],
) -> list[str] | None:
    """Parse a LevelChunk raw_payload and return the top-block map.

    Args:
        raw_payload: The raw chunk payload containing sub-chunk storages.
        sub_chunk_count: Number of sub-chunks in the payload.
        block_palette: The block palette from StartGame (index = runtime ID).
            May be empty when ``use_block_network_id_hashes`` is true (each
            sub-chunk carries its own NBT palette in that case).

    Returns:
        A list of 256 block names in ``x * 16 + z`` order, or ``None`` on failure.
    """
    if sub_chunk_count <= 0 or not raw_payload:
        return None

    # Parse all sub-chunks.
    sub_chunks: dict[int, tuple[list[int], list[str] | None]] = {}
    offset = 0
    for y_idx in range(sub_chunk_count):
        result = parse_sub_chunk(raw_payload, offset)
        if result is None:
            break
        ids, offset, lp = result
        sub_chunks[y_idx] = (ids, lp)

    if not sub_chunks:
        return None

    return _extract_top_blocks(sub_chunks, block_palette)


def _extract_top_blocks(
    sub_chunks: dict[int, tuple[list[int], list[str] | None]],
    block_palette: list[str],
) -> list[str]:
    """Find the topmost non-air block at each (x, z) column.

    Args:
        sub_chunks: Mapping of Y index to ``(ids[4096], local_palette_or_None)``.
        block_palette: Global block palette for name resolution (used when
            *local_palette* is ``None``).

    Returns:
        List of 256 block names in ``x * 16 + z`` order.
    """
    global_len = len(block_palette)
    top_blocks = [AIR] * 256
    found = [False] * 256

    for y_idx in sorted(sub_chunks.keys(), reverse=True):
        storage, local_palette = sub_chunks[y_idx]
        if local_palette is not None:
            pal = local_palette
            pal_len = len(pal)
        else:
            pal = block_palette
            pal_len = global_len

        for x in range(16):
            for z in range(16):
                col = x * 16 + z
                if found[col]:
                    continue
                for y in range(15, -1, -1):
                    rid = storage[(x << 8) | (z << 4) | y]
                    name = pal[rid] if rid < pal_len else AIR
                    if name != AIR:
                        top_blocks[col] = name
                        found[col] = True
                        break

        if all(found):
            break

    return top_blocks


# SubChunk entry result codes.
_SC_RESULT_SUCCESS = 1
_SC_RESULT_SUCCESS_ALL_AIR = 6


def parse_sub_chunk_entries(
    data: bytes,
    cache_enabled: bool,
) -> list[tuple[tuple[int, int, int], list[int] | None, list[str] | None]]:
    """Parse SubChunk packet entries.

    Args:
        data: The raw ``sub_chunk_entries`` bytes from a SubChunk packet.
        cache_enabled: Whether blob caching is enabled.

    Returns:
        List of ``((offset_x, offset_y, offset_z), ids_or_None, local_palette_or_None)``.
    """
    if len(data) < 4:
        return []

    count = struct.unpack_from("<I", data, 0)[0]
    offset = 4
    results: list[tuple[tuple[int, int, int], list[int] | None, list[str] | None]] = []

    for _ in range(count):
        if offset + 4 > len(data):
            break

        ox = struct.unpack_from("b", data, offset)[0]
        oy = struct.unpack_from("b", data, offset + 1)[0]
        oz = struct.unpack_from("b", data, offset + 2)[0]
        result_code = data[offset + 3]
        offset += 4

        ids: list[int] | None = None
        lp: list[str] | None = None

        # Raw payload: varuint32 length + data.
        # Present on success; absent for all-air when caching.
        has_payload = False
        if not cache_enabled:
            has_payload = True
        elif result_code != _SC_RESULT_SUCCESS_ALL_AIR:
            has_payload = True

        if has_payload:
            data_len, offset = _read_varint32(data, offset)
            sub_data = data[offset:offset + data_len]
            offset += data_len

            if result_code == _SC_RESULT_SUCCESS:
                parsed = parse_sub_chunk(sub_data)
                if parsed is not None:
                    ids = parsed[0]
                    lp = parsed[2]

        # HeightMapType (uint8) + optional 256-byte heightmap.
        if offset < len(data):
            hm_type = data[offset]
            offset += 1
            if hm_type == 1:  # HasData
                offset += 256

        # RenderHeightMapType (uint8) + optional 256-byte heightmap.
        if offset < len(data):
            rhm_type = data[offset]
            offset += 1
            if rhm_type == 1:
                offset += 256

        # Blob hash (uint64 LE) — only when caching enabled.
        if cache_enabled and offset + 8 <= len(data):
            offset += 8

        results.append(((ox, oy, oz), ids, lp))

    return results
