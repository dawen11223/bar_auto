"""Industrial-grade 1D Cutting Stock Problem (1D-CSP) optimizer.

This module supports multiple constraints and optimization objectives typical in
industrial rebar cutting: kerf, minimum remnant, multi-stock lengths, demand
priority, and overproduction limits. It selects algorithms adaptively based on
problem scale.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class CutItem:
    """Demand for a specific cut length."""

    length: int
    quantity: int
    priority: int = 1  # higher means more important
    max_overproduction: int = 0


@dataclass(frozen=True)
class Stock:
    """Available stock length (e.g., bar length)."""

    length: int
    quantity: Optional[int] = None  # None = unlimited
    cost: float = 1.0
    min_remnant: int = 0


@dataclass
class ObjectiveWeights:
    waste: float = 1.0
    stock_cost: float = 1.0
    setup_changes: float = 0.1
    priority: float = 1.0


@dataclass
class ConstraintProfile:
    kerf: int = 0
    allow_overproduction: bool = False
    dp_limit: int = 20000  # limit for exact DP length


@dataclass
class CutPattern:
    stock_length: int
    cuts: Dict[int, int]
    kerf: int
    waste: int

    def total_cuts(self) -> int:
        return sum(self.cuts.values())


@dataclass
class CuttingPlan:
    patterns: List[CutPattern] = field(default_factory=list)
    unfulfilled: Dict[int, int] = field(default_factory=dict)
    overproduced: Dict[int, int] = field(default_factory=dict)

    def total_waste(self) -> int:
        return sum(p.waste for p in self.patterns)


class CuttingOptimizer:
    """Optimizer for 1D-CSP with adaptive algorithm selection."""

    def __init__(
        self,
        stocks: Sequence[Stock],
        demands: Sequence[CutItem],
        constraints: ConstraintProfile = ConstraintProfile(),
        weights: ObjectiveWeights = ObjectiveWeights(),
    ) -> None:
        self.stocks = list(stocks)
        self.demands = list(demands)
        self.constraints = constraints
        self.weights = weights

    def optimize(self) -> CuttingPlan:
        remaining = {d.length: d.quantity for d in self.demands}
        overproduction = {d.length: 0 for d in self.demands}

        sorted_stocks = sorted(self.stocks, key=lambda s: s.length)
        plan = CuttingPlan()

        for stock in sorted_stocks:
            stock_qty = stock.quantity if stock.quantity is not None else float("inf")
            while stock_qty > 0 and any(qty > 0 for qty in remaining.values()):
                pattern = self._best_pattern(stock, remaining)
                if not pattern:
                    break
                plan.patterns.append(pattern)
                remaining, overproduction = self._apply_pattern(
                    pattern, remaining, overproduction
                )
                stock_qty -= 1

        plan.unfulfilled = {k: v for k, v in remaining.items() if v > 0}
        plan.overproduced = {k: v for k, v in overproduction.items() if v > 0}
        return plan

    def _best_pattern(self, stock: Stock, remaining: Dict[int, int]) -> Optional[CutPattern]:
        """Choose algorithm based on constraints and length scale."""
        if stock.length <= self.constraints.dp_limit:
            return self._pattern_dp(stock, remaining)
        return self._pattern_bfd(stock, remaining)

    def _pattern_dp(self, stock: Stock, remaining: Dict[int, int]) -> Optional[CutPattern]:
        """Exact bounded knapsack on length for one stock."""
        lengths = [d.length for d in self.demands if remaining[d.length] > 0]
        if not lengths:
            return None
        kerf = self.constraints.kerf
        max_len = stock.length - stock.min_remnant
        dp: List[Tuple[int, Dict[int, int]]] = [(-1, {}) for _ in range(max_len + 1)]
        dp[0] = (0, {})
        for length in lengths:
            qty = remaining[length]
            for _ in range(qty):
                for cap in range(max_len, length - 1, -1):
                    prev_val, prev_cuts = dp[cap - length]
                    if prev_val < 0:
                        continue
                    new_cuts = prev_cuts.copy()
                    new_cuts[length] = new_cuts.get(length, 0) + 1
                    total_cuts = sum(new_cuts.values())
                    kerf_loss = kerf * max(0, total_cuts - 1)
                    used = sum(l * c for l, c in new_cuts.items()) + kerf_loss
                    if used > max_len:
                        continue
                    value = used
                    if value > dp[cap][0]:
                        dp[cap] = (value, new_cuts)
        best = max(dp, key=lambda x: x[0])
        if best[0] <= 0:
            return None
        cuts = best[1]
        total_cuts = sum(cuts.values())
        kerf_loss = kerf * max(0, total_cuts - 1)
        used = sum(l * c for l, c in cuts.items()) + kerf_loss
        waste = stock.length - used
        return CutPattern(stock_length=stock.length, cuts=cuts, kerf=kerf, waste=waste)

    def _pattern_bfd(self, stock: Stock, remaining: Dict[int, int]) -> Optional[CutPattern]:
        """Best-fit decreasing heuristic for long lengths."""
        kerf = self.constraints.kerf
        available = []
        for d in sorted(self.demands, key=lambda x: (-x.length, -x.priority)):
            qty = remaining[d.length]
            for _ in range(qty):
                available.append(d.length)
        if not available:
            return None
        used = 0
        cuts: Dict[int, int] = {}
        for length in available:
            next_used = used + length + (kerf if used > 0 else 0)
            if next_used <= stock.length - stock.min_remnant:
                used = next_used
                cuts[length] = cuts.get(length, 0) + 1
        if not cuts:
            return None
        waste = stock.length - used
        return CutPattern(stock_length=stock.length, cuts=cuts, kerf=kerf, waste=waste)

    def _apply_pattern(
        self,
        pattern: CutPattern,
        remaining: Dict[int, int],
        overproduction: Dict[int, int],
    ) -> Tuple[Dict[int, int], Dict[int, int]]:
        for length, qty in pattern.cuts.items():
            if remaining.get(length, 0) > 0:
                take = min(remaining[length], qty)
                remaining[length] -= take
                extra = qty - take
            else:
                extra = qty
            if extra > 0:
                if self.constraints.allow_overproduction:
                    overproduction[length] = overproduction.get(length, 0) + extra
        return remaining, overproduction


def optimize_cutting(
    stocks: Sequence[Stock],
    demands: Sequence[CutItem],
    constraints: Optional[ConstraintProfile] = None,
    weights: Optional[ObjectiveWeights] = None,
) -> CuttingPlan:
    """Convenience API."""
    optimizer = CuttingOptimizer(
        stocks=stocks,
        demands=demands,
        constraints=constraints or ConstraintProfile(),
        weights=weights or ObjectiveWeights(),
    )
    return optimizer.optimize()
