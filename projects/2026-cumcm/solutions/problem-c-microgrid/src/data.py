"""Tariff, load and PV share the right endpoint of each interval."""
from dataclasses import dataclass
from datetime import date, time, timedelta
from pathlib import Path

import numpy as np
from openpyxl import load_workbook

PROJECT = Path(__file__).resolve().parents[1]
INPUT = PROJECT.parents[1] / "problem-statements" / "attachments" / "problem-c"
DT_H = 1 / 6
SLOTS = 144


def minutes(value):
    if isinstance(value, time):
        return value.hour * 60 + value.minute
    if value == "0:00+1":
        return 1440
    h, m = map(int, value.split(":"))
    return h * 60 + m


def interval_label(k):
    """Slot k=0 is 00:00--00:10, represented by the 00:10 sample."""
    a, b = k * 10, (k + 1) * 10
    return f"{a//60:02d}:{a%60:02d}-{b//60:02d}:{b%60:02d}"


def _rows(name, sheet=None):
    w = load_workbook(INPUT / name, read_only=True, data_only=True)
    s = w.active if sheet is None else w[sheet]
    result = list(s.values)
    w.close()
    return result


def _wide(name, sheet=None):
    rows = _rows(name, sheet)
    assert [minutes(x) for x in rows[0][1:]] == list(range(10, 1441, 10))
    dates = [r[0].date() for r in rows[1:]]
    assert dates == [date(2025, 1, 1) + timedelta(days=i) for i in range(365)]
    x = np.array([r[1:] for r in rows[1:]], dtype=float)
    assert x.shape == (365, 144) and np.isfinite(x).all() and (x >= 0).all()
    return x


@dataclass
class Dataset:
    fixed_price: np.ndarray
    q1_load: np.ndarray
    q1_pv: np.ndarray
    load: np.ndarray
    pv: np.ndarray


def read_inputs():
    rows = _rows("附件1.xlsx")
    assert [minutes(r[0]) for r in rows[1:]] == list(range(10, 1441, 10))
    first = np.array([r[1:] for r in rows[1:]], dtype=float)
    return Dataset(first[:, 0], first[:, 1], first[:, 2],
                   _wide("附件2.xlsx", "小区负载"),
                   _wide("附件2.xlsx", "光伏发电实际功率"))
