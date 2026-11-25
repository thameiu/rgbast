from dataclasses import asdict

from app.utils.palette_diff import diff_colors


def changed_colors(base, other):
    return [asdict(change) for change in diff_colors(base, other)]
