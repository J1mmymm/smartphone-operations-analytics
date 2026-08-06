# v1.0.0 - Initial portfolio release

首个完整作品集版本，交付手机产销存与现金效率分析的可复现数据、Excel、MySQL 和 Power BI 成品。

## Included

- 42 个月、14 个经营季度的公开项目数据及固定种子生成脚本。
- 4 张维表、4 张事实表、月/季 KPI mart 和自动质量报告。
- MySQL 8.0 建库、建表、导入、5 个分析视图、质量检查和业务查询。
- 19 个工作表的可审计 Excel 分析模型与经营情景测算。
- 三页 Power BI 看板、PBIP/PBIR/TMDL 源码、23 个 DAX 指标、PBIX、PDF 和页面截图。
- 中文详细 README、简历项目描述和面试讲解提纲。

## Validated controls

- 销售回款：32,870,200 元。
- L/H 产品回款：26,948,200 / 5,922,000 元。
- 现金流入/流出：50,130,681 / 49,777,407 元。
- 期末现金：353,274 元。
- 14/14 季度现金勾稽通过；库存恒等式全部通过。
- PBIR：0 error；1 条在线 `visualContainer/2.11.0` Schema 暂不可达的 schema-fetch warning。

## Main finding

销售放量后的产能与现金风险得到数据支持，但仓储拥堵和普遍缺货假设未得到事实支持。
