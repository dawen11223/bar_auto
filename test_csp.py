import pytest

from csp import ConstraintProfile, CutItem, Stock, optimize_cutting


def test_optimize_basic_dp():
    stocks = [Stock(length=12000, quantity=2, min_remnant=0)]
    demands = [CutItem(length=3000, quantity=4), CutItem(length=2000, quantity=2)]
    plan = optimize_cutting(stocks, demands, ConstraintProfile(kerf=0))
    assert plan.unfulfilled == {}
    assert plan.total_waste() >= 0
    assert sum(p.total_cuts() for p in plan.patterns) == 6


def test_optimize_with_kerf_and_remnant():
    stocks = [Stock(length=10000, quantity=1, min_remnant=100)]
    demands = [CutItem(length=4500, quantity=2)]
    plan = optimize_cutting(stocks, demands, ConstraintProfile(kerf=10))
    assert plan.unfulfilled == {}
    pattern = plan.patterns[0]
    assert pattern.waste >= 100


def test_optimize_overproduction_not_allowed():
    stocks = [Stock(length=6000, quantity=1)]
    demands = [CutItem(length=2500, quantity=1)]
    plan = optimize_cutting(stocks, demands, ConstraintProfile(kerf=0, allow_overproduction=False))
    assert plan.overproduced == {}
