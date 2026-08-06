# Validation Report

## 数据与控制总额

| 检查 | 结果 | 状态 |
|---|---:|---|
| 月份/季度覆盖 | 42 / 14 | PASS |
| 订单主键唯一 | 327 / 327 | PASS |
| 销售回款 | 32,870,200 | PASS |
| L 产品回款 | 26,948,200 | PASS |
| H 产品回款 | 5,922,000 | PASS |
| 现金流入 | 50,130,681 | PASS |
| 现金流出 | 49,777,407 | PASS |
| 期末现金 | 353,274 | PASS |
| 季度现金勾稽 | 14 / 14 | PASS |
| 库存恒等式 | 168 / 168 | PASS |

## MySQL

| 检查 | 结果 | 状态 |
|---|---:|---|
| MySQL 版本 | 8.0.46 | PASS |
| `vw_management_kpi_monthly` | 42 行 | PASS |
| `vw_sales_mix` | 165 行 | PASS |
| `vw_inventory_health` | 168 行 | PASS |
| `vw_fulfillment_efficiency` | 97 行 | PASS |
| `vw_cashflow_analysis` | 237 行 | PASS |
| SQL 业务查询 | 全部执行成功 | PASS |

## Excel

| 检查 | 结果 | 状态 |
|---|---:|---|
| 工作表数量 | 19 | PASS |
| 关键 QA 单元格 | 全部 PASS | PASS |
| 公式错误扫描 | 0 | PASS |
| 主要工作表渲染 | 无空白图表/截断/不可读区域 | PASS |
| 关键 KPI 对账 | 与 CSV/MySQL 一致 | PASS |

## Power BI

| 检查 | 结果 | 状态 |
|---|---:|---|
| 报表页面 | 3 | PASS |
| 视觉对象 | 31 | PASS |
| DAX 指标 | 23 | PASS |
| PBIR 静态校验 | 0 error / 1 schema-fetch warning | PASS |
| Desktop 打开 | PBIP 与 TMDL 可加载 | PASS |
| MySQL 刷新 | Connector/NET + Database authentication | PASS |
| 页面截图 | 3 / 3 | PASS |
| PBIX 打开 | Desktop 当前文件状态为 ready | PASS |
| PDF 渲染 | 3 页 / 3 页，无截断或空白页 | PASS |

> 唯一 PBIR warning 来自校验工具暂时无法获取 Power BI Desktop 生成的 `visualContainer/2.11.0` 在线 JSON Schema；本地结构检查、Desktop 重载和逐页截图均通过，未发现报表定义错误。

## 安全检查

| 检查 | 结果 | 状态 |
|---|---:|---|
| Power BI 临时只读数据库账户 | 导出后已删除 | PASS |
| 仓库明文密码/连接凭据 | 未发现 | PASS |
| 原始课程工作簿/个人信息 | 未纳入仓库 | PASS |

## 跨工具对账

| KPI | CSV QA | MySQL | Excel | Power BI |
|---|---:|---:|---:|---:|
| Total Sales | 32,870,200 | 32,870,200 | 32,870,200 | 32,870,200 |
| Gross Margin | 28.23% | 28.23% | 28.23% | 28.23% |
| Fill Rate | 100.00% | 100.00% | 100.00% | 100.00% |
| On-time Order Rate | 92.05% | 92.05% | 92.05% | 92.05% |
| Q13 Capacity Utilization | 95.33% | 95.33% | 95.33% | 95.33% |
| Closing Cash | 353,274 | 353,274 | 353,274 | 353,274 |

脚本入口：[`scripts/validate_project.ps1`](../scripts/validate_project.ps1)。
