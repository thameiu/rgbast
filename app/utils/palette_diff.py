"""Pure palette diff shared by snapshot persistence and change previews."""
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Protocol, Sequence


class ColorLike(Protocol):
    hex: str
    label: str | None


@dataclass(frozen=True)
class ColorChange:
    old_index: int | None
    new_index: int | None
    fields: tuple[str, ...] = ()


def diff_colors(old: Sequence[ColorLike], new: Sequence[ColorLike]) -> list[ColorChange]:
    def identity(color: ColorLike) -> tuple[str, str | None]:
        return color.hex.upper(), color.label or None

    matches: dict[int, int] = {}
    anchored: set[int] = set()
    matcher = SequenceMatcher(None, list(map(identity, old)), list(map(identity, new)), autojunk=False)
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            matches[block.b + offset] = block.a + offset
            anchored.add(block.b + offset)

    remaining_old = set(range(len(old))) - set(matches.values())
    remaining_new = set(range(len(new))) - set(matches)
    # Pair moved colors before replacements, then label-only edits. Consume each
    # occurrence once so duplicate colors cannot reuse the same previous row.
    for same in (
        lambda a, b: identity(a) == identity(b),
        lambda a, b: a.hex.upper() == b.hex.upper(),
    ):
        for j in sorted(remaining_new):
            candidates = [i for i in remaining_old if same(old[i], new[j])]
            if candidates:
                i = min(candidates, key=lambda i: (abs(i - j), i))
                matches[j] = i
                remaining_old.remove(i)
                remaining_new.remove(j)

    for i, j in zip(sorted(remaining_old), sorted(remaining_new)):
        matches[j] = i
    remaining_old -= set(matches.values())

    changes = []
    for j, color in enumerate(new):
        i = matches.get(j)
        fields = []
        if i is not None:
            if old[i].hex.upper() != color.hex.upper():
                fields.append("hex")
            if (old[i].label or None) != (color.label or None):
                fields.append("label")
            if j not in anchored and (i != j or not fields):
                fields.append("position")
        changes.append(ColorChange(i, j, tuple(fields)))
    changes.extend(ColorChange(i, None) for i in sorted(remaining_old))
    return changes
