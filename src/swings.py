"""Detección de swing highs / swing lows (fractales) sobre una serie de velas."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Pivot:
    idx: int          # posición entera dentro del DataFrame
    timestamp: pd.Timestamp
    price: float
    kind: str          # "high" o "low"


def find_pivots(df: pd.DataFrame, window: int = 3) -> list[Pivot]:
    """Fractales simples: una vela i es swing high si su high es el máximo
    estricto entre [i-window, i+window]; swing low análogo con el mínimo.
    Devuelve los pivotes en orden cronológico.
    """
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)
    pivots: list[Pivot] = []

    for i in range(window, n - window):
        seg_h = highs[i - window : i + window + 1]
        if highs[i] == seg_h.max() and (seg_h == highs[i]).sum() == 1:
            pivots.append(Pivot(i, df.index[i], float(highs[i]), "high"))

        seg_l = lows[i - window : i + window + 1]
        if lows[i] == seg_l.min() and (seg_l == lows[i]).sum() == 1:
            pivots.append(Pivot(i, df.index[i], float(lows[i]), "low"))

    pivots.sort(key=lambda p: p.idx)
    return pivots


def nearest_levels(
    pivots: list[Pivot], kind: str, reference_price: float, side: str, n: int = 2
) -> list[float]:
    """Devuelve hasta n precios de pivotes del tipo `kind` ("high"/"low")
    más cercanos a `reference_price`, del lado indicado:
      side="above" -> solo precios > reference_price, ordenados ascendente (más cercano primero)
      side="below" -> solo precios < reference_price, ordenados descendente (más cercano primero)
    """
    prices = [p.price for p in pivots if p.kind == kind]
    if side == "above":
        candidates = sorted(p for p in prices if p > reference_price)
    else:
        candidates = sorted((p for p in prices if p < reference_price), reverse=True)
    return candidates[:n]


def nearest_pivots(
    pivots: list[Pivot], kind: str, reference_price: float, side: str, n: int = 2
) -> list[Pivot]:
    """Igual que `nearest_levels` pero devuelve los objetos Pivot completos
    (con su posición en el DataFrame), necesario cuando además del precio
    hace falta consultar otro dato de esa vela (p.ej. el volumen, para el
    filtro de liquidez)."""
    candidates = [p for p in pivots if p.kind == kind and (p.price > reference_price if side == "above" else p.price < reference_price)]
    candidates.sort(key=lambda p: p.price, reverse=(side == "below"))
    return candidates[:n]

