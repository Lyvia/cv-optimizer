"""
differ.py — Line-based diff between two text versions, with per-chunk
accept/ignore state, used to drive the CV refine accept/reject UI.
No AI call involved: pure stdlib difflib.
"""

import difflib
from dataclasses import dataclass
from typing import Literal

ChunkType = Literal["equal", "added", "removed", "replaced"]
ChunkStatus = Literal["pending", "accepted", "ignored"]

_TAG_MAP: dict[str, ChunkType] = {
    "equal": "equal",
    "insert": "added",
    "delete": "removed",
    "replace": "replaced",
}


@dataclass
class DiffChunk:
    type: ChunkType
    old_lines: list[str]   # original lines (empty for "added")
    new_lines: list[str]   # new lines (empty for "removed")
    chunk_id: str          # unique id for session state key


def compute_diff(old_text: str, new_text: str, round_id: str) -> list[DiffChunk]:
    """
    Compute a chunked diff between two texts, split by line.

    Args:
        old_text: The current accepted version
        new_text: The new AI-proposed version
        round_id: Unique identifier for this diff round, used to build
            collision-free chunk_ids across successive refine rounds

    Returns:
        list[DiffChunk]: ordered chunks covering the whole text
    """
    old_lines = old_text.split("\n")
    new_lines = new_text.split("\n")
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

    chunks: list[DiffChunk] = []
    idx = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        chunk_type = _TAG_MAP[tag]
        old_part = old_lines[i1:i2]
        new_part = new_lines[j1:j2]

        if chunk_type == "equal" and chunks and chunks[-1].type == "equal":
            chunks[-1].old_lines.extend(old_part)
            chunks[-1].new_lines.extend(new_part)
            continue

        chunks.append(
            DiffChunk(
                type=chunk_type,
                old_lines=old_part,
                new_lines=new_part,
                chunk_id=f"{round_id}_{idx}",
            )
        )
        idx += 1

    return chunks


def rebuild_text(chunks: list[DiffChunk], statuses: dict[str, ChunkStatus]) -> str:
    """
    Rebuild a text from a diff's chunks given the current accept/ignore
    decision for each chunk. Equal chunks are always kept. Any chunk that
    isn't explicitly "accepted" (including untouched "removed" chunks,
    which have no individual button) falls back to its original lines —
    only an accepted chunk contributes its new_lines.

    Args:
        chunks: The diff produced by compute_diff()
        statuses: chunk_id -> "pending" | "accepted" | "ignored"

    Returns:
        str: The merged text
    """
    out_lines: list[str] = []
    for chunk in chunks:
        if chunk.type == "equal":
            out_lines.extend(chunk.old_lines)
        elif statuses.get(chunk.chunk_id, "pending") == "accepted":
            out_lines.extend(chunk.new_lines)
        else:
            out_lines.extend(chunk.old_lines)
    return "\n".join(out_lines)
