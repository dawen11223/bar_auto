# 1D-CSP 工业切割优化模块

该模块面向钢筋加工等工业场景的 **一维下料问题（1D-CSP）**，支持常见约束：

- 多种原料长度与库存数量
- 切割锯缝（kerf）
- 最小余料长度（min remnant）
- 需求优先级
- 可选超产控制

## 设计目标

- **工业可用性**：对大长度和大批量场景采用启发式，避免 DP 爆炸。
- **多目标优化**：废料、库存成本、换型成本等目标可用权重扩展。
- **场景适配**：在可控长度范围内使用精确 DP；否则使用 BFD 启发式。

## 快速开始

```python
from bar_auto import CutItem, Stock, ConstraintProfile, optimize_cutting

stocks = [
    Stock(length=12000, quantity=10, min_remnant=50),
    Stock(length=9000, quantity=None),
]

demands = [
    CutItem(length=3500, quantity=6, priority=2),
    CutItem(length=2200, quantity=8),
]

plan = optimize_cutting(
    stocks,
    demands,
    constraints=ConstraintProfile(kerf=5, allow_overproduction=False),
)

for pattern in plan.patterns:
    print(pattern)

print("waste:", plan.total_waste())
print("unfulfilled:", plan.unfulfilled)
```

## 模块结构

- `CutItem`：单个需求长度、数量与优先级
- `Stock`：可用原料长度/数量/成本
- `ConstraintProfile`：锯缝、最小余料、是否允许超产等
- `CuttingOptimizer`：自动选择算法并输出 `CuttingPlan`
- `CutPattern`：单根原料的切割方案与废料

## 适用场景建议

- **库存长度固定且长度较短**：DP 模式更优
- **长度范围大且需求量多**：启发式更稳定

后续可扩展：列生成、线性规划求解器、班次换型成本等。
