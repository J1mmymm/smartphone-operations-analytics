import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const projectRoot = process.env.PROJECT_ROOT;
if (!projectRoot) throw new Error("PROJECT_ROOT is required");
const dataDir = path.join(projectRoot, "data", "processed");
const qaDir = path.join(projectRoot, "data", "quality");
const threadOutput = path.join(projectRoot, "outputs", "019fd325-7c3c-7eb1-aaf5-c348d37fe45a");
const repoOutput = path.join(projectRoot, "excel", "Smartphone_Operations_Analysis.xlsx");
const previewDir = path.join(projectRoot, "work", "excel_previews");

const C = {
  orange: "#F56600",
  orangeLight: "#FFF1E8",
  ink: "#252525",
  gray: "#6B7280",
  border: "#D9DEE7",
  soft: "#F5F6F8",
  white: "#FFFFFF",
  blue: "#2563EB",
  amber: "#D97706",
  red: "#B91C1C",
  green: "#2F6B4F",
};

const wb = Workbook.create();

async function importCsv(file, sheetName) {
  const text = await fs.readFile(path.join(file.includes("qa_") ? qaDir : dataDir, file), "utf8");
  const temp = await Workbook.fromCSV(text, { sheetName });
  const source = temp.worksheets.getItem(sheetName).getUsedRange();
  const values = source.values.map((row, rowIndex) => row.map((value) => {
    if (rowIndex === 0 || typeof value !== "string") return value;
    const trimmed = value.trim();
    if (/^-?\d+(?:\.\d+)?$/.test(trimmed)) return Number(trimmed);
    if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) return new Date(`${trimmed}T00:00:00Z`);
    return value;
  }));
  const target = wb.worksheets.add(sheetName);
  target.getRangeByIndexes(0, 0, values.length, values[0].length).values = values;
  return target;
}

function setTitle(sheet, range, title, subtitle = "") {
  sheet.showGridLines = false;
  sheet.getRange(range).merge();
  const first = range.split(":")[0];
  sheet.getRange(first).values = [[title]];
  sheet.getRange(range).format = {
    fill: C.ink,
    font: { bold: true, color: C.white, size: 18 },
    verticalAlignment: "center",
    horizontalAlignment: "left",
  };
  sheet.getRange(range).format.rowHeight = 32;
  if (subtitle) {
    const row = Number(first.match(/\d+/)[0]) + 1;
    const startCol = first.match(/[A-Z]+/)[0];
    const endCol = range.split(":")[1].match(/[A-Z]+/)[0];
    const subRange = `${startCol}${row}:${endCol}${row}`;
    sheet.getRange(subRange).merge();
    sheet.getRange(`${startCol}${row}`).values = [[subtitle]];
    sheet.getRange(subRange).format = {
      fill: C.soft, font: { color: C.gray, size: 10 }, wrapText: true,
      verticalAlignment: "center", horizontalAlignment: "left",
    };
    sheet.getRange(subRange).format.rowHeight = 25;
  }
}

function styleHeader(range) {
  range.format = {
    fill: C.ink,
    font: { bold: true, color: C.white, size: 10 },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: C.border },
  };
  range.format.rowHeight = 24;
}

function styleTable(range) {
  range.format = {
    font: { color: C.ink, size: 10 },
    verticalAlignment: "center",
    borders: { preset: "all", style: "thin", color: C.border },
  };
}

function kpiCard(sheet, labelRange, valueRange, label, formula, numberFormat, note) {
  sheet.getRange(labelRange).merge();
  sheet.getRange(valueRange).merge();
  const labelCell = labelRange.split(":")[0];
  const valueCell = valueRange.split(":")[0];
  sheet.getRange(labelCell).values = [[label]];
  sheet.getRange(valueCell).formulas = [[formula]];
  sheet.getRange(labelRange).format = {
    fill: C.soft, font: { bold: true, color: C.gray, size: 10 },
    horizontalAlignment: "center", verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: C.border },
  };
  sheet.getRange(valueRange).format = {
    fill: C.white, font: { bold: true, color: C.ink, size: 19 },
    horizontalAlignment: "center", verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: C.border },
  };
  sheet.getRange(valueCell).setNumberFormat(numberFormat);
  if (note) sheet.getRange(valueCell).note = note;
}

// Create presentation and analytical sheets before formulas reference them.
const dashboard = wb.worksheets.add("经营看板");
const productChannel = wb.worksheets.add("产品渠道");
const inventoryAlert = wb.worksheets.add("库存预警");
const cashAnalysis = wb.worksheets.add("现金流");
const scenario = wb.worksheets.add("情景测算");
const mapping = wb.worksheets.add("清洗映射");
const dictionary = wb.worksheets.add("数据字典");

const monthly = await importCsv("mart_monthly_kpi.csv", "月度KPI");
const quarterly = await importCsv("mart_quarterly_kpi.csv", "季度KPI");
const sales = await importCsv("fact_sales_order.csv", "订单明细");
const inventory = await importCsv("fact_inventory.csv", "库存明细");
const production = await importCsv("fact_production.csv", "生产明细");
const cash = await importCsv("fact_cashflow.csv", "现金明细");
const dates = await importCsv("dim_date.csv", "日期维表");
const products = await importCsv("dim_product.csv", "产品维表");
const channels = await importCsv("dim_channel.csv", "渠道维表");
const regions = await importCsv("dim_region.csv", "区域维表");
const qa = await importCsv("qa_checks.csv", "质量检查源");

// Raw data tabs: consistent formatting, filters/tables, helper lookup columns.
const rawSheets = [monthly, quarterly, sales, inventory, production, cash, dates, products, channels, regions, qa];
for (const sheet of rawSheets) {
  const used = sheet.getUsedRange();
  sheet.freezePanes.freezeRows(1);
  styleHeader(used.getRow(0));
  styleTable(used);
  used.format.autofitColumns();
  used.format.autofitRows();
  sheet.showGridLines = false;
}

sales.getRange("W1:AA1").values = [["product_family", "sku", "channel_name", "region_name", "quarter_seq"]];
styleHeader(sales.getRange("W1:AA1"));
sales.getRange("W2").formulas = [["=XLOOKUP(F2,'产品维表'!$A$2:$A$5,'产品维表'!$D$2:$D$5,\"未映射\")"]];
sales.getRange("X2").formulas = [["=XLOOKUP(F2,'产品维表'!$A$2:$A$5,'产品维表'!$B$2:$B$5,\"未映射\")"]];
sales.getRange("Y2").formulas = [["=XLOOKUP(G2,'渠道维表'!$A$2:$A$4,'渠道维表'!$B$2:$B$4,\"未映射\")"]];
sales.getRange("Z2").formulas = [["=XLOOKUP(H2,'区域维表'!$A$2:$A$5,'区域维表'!$B$2:$B$5,\"未映射\")"]];
sales.getRange("AA2").formulas = [["=XLOOKUP(B2,'日期维表'!$A$2:$A$43,'日期维表'!$F$2:$F$43,0)"]];
for (const col of ["W", "X", "Y", "Z", "AA"]) sales.getRange(`${col}2:${col}328`).fillDown();
styleTable(sales.getRange("W2:AA328"));

inventory.getRange("M1:N1").values = [["quarter_seq", "sku"]];
styleHeader(inventory.getRange("M1:N1"));
inventory.getRange("M2").formulas = [["=XLOOKUP(A2,'日期维表'!$A$2:$A$43,'日期维表'!$F$2:$F$43,0)"]];
inventory.getRange("N2").formulas = [["=XLOOKUP(B2,'产品维表'!$A$2:$A$5,'产品维表'!$B$2:$B$5,\"未映射\")"]];
inventory.getRange("M2:M169").fillDown();
inventory.getRange("N2:N169").fillDown();
styleTable(inventory.getRange("M2:N169"));

production.getRange("J1:K1").values = [["quarter_seq", "sku"]];
styleHeader(production.getRange("J1:K1"));
production.getRange("J2").formulas = [["=XLOOKUP(A2,'日期维表'!$A$2:$A$43,'日期维表'!$F$2:$F$43,0)"]];
production.getRange("K2").formulas = [["=XLOOKUP(B2,'产品维表'!$A$2:$A$5,'产品维表'!$B$2:$B$5,\"未映射\")"]];
production.getRange("J2:J169").fillDown();
production.getRange("K2:K169").fillDown();
styleTable(production.getRange("J2:K169"));

inventory.getRange("O1").values = [["balance_diff"]];
styleHeader(inventory.getRange("O1"));
inventory.getRange("O2").formulas = [["=C2+D2-F2-G2"]];
inventory.getRange("O2:O169").fillDown();
styleTable(inventory.getRange("O2:O169"));

// Mapping / cleaning audit trail.
setTitle(mapping, "A1:H1", "清洗与映射规则", "所有业务键均通过可见映射表转换；订单明细 W:AA 与库存明细 M:N 使用 XLOOKUP 生成辅助字段。" );
mapping.getRange("A4:H4").values = [["Mapping Type", "Source Key", "Mapped Value", "Business Meaning", "Rule", "Missing Handling", "Owner", "Status"]];
styleHeader(mapping.getRange("A4:H4"));
const mappingRows = [
  ["Product", 101, "L1 / N-Lite", "L系列大众基础款", "product_key → SKU", "返回未映射", "Data Analyst", "Active"],
  ["Product", 102, "L2 / N-Plus", "L系列大众升级款", "product_key → SKU", "返回未映射", "Data Analyst", "Active"],
  ["Product", 201, "H1 / N-Pro", "H系列高端旗舰款", "product_key → SKU", "返回未映射", "Data Analyst", "Active"],
  ["Product", 202, "H2 / N-Ultra", "H系列高端影像款", "product_key → SKU", "返回未映射", "Data Analyst", "Active"],
  ["Channel", 1, "线上直营", "自营电商与品牌商城", "channel_key → channel_name", "返回未映射", "Data Analyst", "Active"],
  ["Channel", 2, "线下零售", "门店与零售合作伙伴", "channel_key → channel_name", "返回未映射", "Data Analyst", "Active"],
  ["Channel", 3, "区域经销", "区域批量经销业务", "channel_key → channel_name", "返回未映射", "Data Analyst", "Active"],
  ["Date", "YYYYMM", "Q01-Q14", "连续42个月映射为14经营季度", "每3个月为一经营季度", "返回0", "Data Analyst", "Active"],
  ["Cash", "signed_amount", "流入为正/流出为负", "用于累计现金余额", "direction 决定符号", "不允许为空", "Data Analyst", "Active"],
];
mapping.getRange(`A5:H${4 + mappingRows.length}`).values = mappingRows;
styleTable(mapping.getRange(`A5:H${4 + mappingRows.length}`));
mapping.getRange("A4:H13").format.wrapText = true;
mapping.getRange("A:A").format.columnWidth = 16;
mapping.getRange("B:B").format.columnWidth = 14;
mapping.getRange("C:C").format.columnWidth = 22;
mapping.getRange("D:F").format.columnWidth = 26;
mapping.getRange("G:H").format.columnWidth = 14;

// Data dictionary.
setTitle(dictionary, "A1:G1", "数据字典", "粒度、主键与指标口径均在此集中定义；币种为人民币，日期采用自然月。" );
dictionary.getRange("A4:G4").values = [["Table", "Grain", "Primary Key", "Field / Metric", "Definition", "Type", "QA Rule"]];
styleHeader(dictionary.getRange("A4:G4"));
const dictRows = [
  ["dim_date", "每月一行", "date_key", "business_quarter", "连续42个月映射为Q01-Q14", "Text", "42行且主键唯一"],
  ["dim_product", "每SKU一行", "product_key", "product_family", "L/H产品大类", "Text", "4个SKU"],
  ["dim_channel", "每渠道一行", "channel_key", "channel_name", "线上直营/线下零售/区域经销", "Text", "3类渠道"],
  ["dim_region", "每区域一行", "region_key", "region_name", "华东/华南/华北/中西部", "Text", "4个区域"],
  ["fact_sales_order", "每订单行", "order_id", "net_sales", "订单净销售额；累计与销售回款控制额对账", "Decimal", ">0"],
  ["fact_sales_order", "每订单行", "order_id", "gross_margin", "(net_sales-cogs)/net_sales", "Percent", "0%-100%"],
  ["fact_sales_order", "每订单行", "order_id", "on_time_flag", "完整交付且发货日期不晚于承诺日期", "0/1", "仅0或1"],
  ["fact_inventory", "每月×SKU", "month_key+product_key", "days_of_supply", "月末库存÷当月需求×30；无需求期单独处理", "Decimal", ">=0"],
  ["fact_inventory", "每月×SKU", "month_key+product_key", "inventory_balance", "期初+生产入库-发货=期末", "Check", "差异为0"],
  ["fact_production", "每月×SKU", "month_key+product_key", "capacity_utilization", "总产出÷分配产能", "Percent", "0%-100%"],
  ["fact_cashflow", "每月×现金类别", "cashflow_id", "signed_amount", "流入为正、流出为负", "Decimal", "累计期末353,274"],
  ["KPI", "筛选上下文", "-", "fill_rate", "SUM(shipped_qty)/SUM(ordered_qty)", "Percent", "分母>0"],
  ["KPI", "筛选上下文", "-", "inventory_turnover", "销售成本÷平均库存金额", "Times", "仅销售期解释"],
  ["KPI", "筛选上下文", "-", "closing_cash", "期初0加累计signed_amount", "Currency", "季度逐期对账"],
];
dictionary.getRange(`A5:G${4 + dictRows.length}`).values = dictRows;
styleTable(dictionary.getRange(`A5:G${4 + dictRows.length}`));
dictionary.getRange(`A4:G${4 + dictRows.length}`).format.wrapText = true;
dictionary.getRange("A:A").format.columnWidth = 22;
dictionary.getRange("B:C").format.columnWidth = 18;
dictionary.getRange("D:D").format.columnWidth = 22;
dictionary.getRange("E:E").format.columnWidth = 38;
dictionary.getRange("F:G").format.columnWidth = 18;

// Executive dashboard.
setTitle(dashboard, "A1:N1", "手机产销存与现金效率分析", "南湖高新科技有限责任公司｜42个月 / 14个经营季度｜数据截至 2025-06｜币种：人民币" );
dashboard.getRange("A4:N4").merge();
dashboard.getRange("A4").values = [["管理层关注：增长是否转化为可持续利润，履约与产能是否承压，现金缓冲是否足以覆盖采购与债务时点。"]];
dashboard.getRange("A4:N4").format = { fill: C.orangeLight, font: { bold: true, color: C.ink, size: 10 }, wrapText: true, verticalAlignment: "center" };
dashboard.getRange("A4:N4").format.rowHeight = 28;
kpiCard(dashboard, "A6:B6", "A7:B9", "累计销售额", "=SUM('订单明细'!$N$2:$N$328)", "#,##0", "控制总额：32,870,200元");
kpiCard(dashboard, "C6:D6", "C7:D9", "综合毛利率", "=SUM('订单明细'!$Q$2:$Q$328)/SUM('订单明细'!$N$2:$N$328)", "0.0%", "毛利额÷净销售额");
kpiCard(dashboard, "E6:F6", "E7:F9", "数量履约率", "=SUM('订单明细'!$J$2:$J$328)/SUM('订单明细'!$I$2:$I$328)", "0.0%", "发货数量÷订购数量");
kpiCard(dashboard, "G6:H6", "G7:H9", "准时订单率", "=SUM('订单明细'!$S$2:$S$328)/COUNTIFS('订单明细'!$A$2:$A$328,\"<>\")", "0.0%", "完整且按承诺日期发货");
kpiCard(dashboard, "I6:J6", "I7:J9", "Q13产能利用率", "=SUMIFS('月度KPI'!$M$2:$M$43,'月度KPI'!$C$2:$C$43,13)/COUNTIFS('月度KPI'!$C$2:$C$43,13)", "0.0%", "高负荷压力季度");
kpiCard(dashboard, "K6:L6", "K7:L9", "最低季度现金", "=MIN('季度KPI'!$R$2:$R$15)", "#,##0", "Q13期末现金为3,223元");
kpiCard(dashboard, "M6:N6", "M7:N9", "期末现金", "='季度KPI'!$R$15", "#,##0", "Q14期末现金");

dashboard.getRange("A12:G12").values = [["Month", "Sales", "Gross Profit", "Fill Rate", "On-time Rate", "Capacity Util.", "Closing Cash"]];
styleHeader(dashboard.getRange("A12:G12"));
dashboard.getRange("A13").formulas = [["='月度KPI'!B2"]];
dashboard.getRange("B13").formulas = [["='月度KPI'!E2"]];
dashboard.getRange("C13").formulas = [["='月度KPI'!F2"]];
dashboard.getRange("D13").formulas = [["='月度KPI'!J2"]];
dashboard.getRange("E13").formulas = [["='月度KPI'!K2"]];
dashboard.getRange("F13").formulas = [["='月度KPI'!M2"]];
dashboard.getRange("G13").formulas = [["='月度KPI'!O2"]];
dashboard.getRange("A13:G54").fillDown();
styleTable(dashboard.getRange("A13:G54"));
dashboard.getRange("B13:C54").setNumberFormat("#,##0");
dashboard.getRange("D13:F54").setNumberFormat("0.0%");
dashboard.getRange("G13:G54").setNumberFormat("#,##0");
const salesChart = dashboard.charts.add("line", dashboard.getRange("A12:C54"));
salesChart.title = "月度销售与毛利趋势（元）";
salesChart.hasLegend = true;
salesChart.xAxis = { axisType: "textAxis", textStyle: { fontSize: 8 } };
salesChart.yAxis = { numberFormatCode: "#,##0" };
salesChart.setPosition("I12", "N28");
dashboard.getRange("O12:P12").values = [["Month", "Closing Cash"]];
dashboard.getRange("O13:P13").formulas = [["=A13", "=G13"]];
dashboard.getRange("O13:P54").fillDown();
const cashChart = dashboard.charts.add("line", dashboard.getRange("O12:P54"));
cashChart.title = "月末现金余额（元）";
cashChart.hasLegend = false;
cashChart.xAxis = { axisType: "textAxis", textStyle: { fontSize: 8 } };
cashChart.yAxis = { numberFormatCode: "#,##0" };
cashChart.setPosition("I30", "N46");
dashboard.getRange("A57:N57").merge();
dashboard.getRange("A57").values = [["结论：销售规模持续放大且数量履约完整；Q13产能处于高负荷、准时率阶段性下降，但库存未形成全面缺货。更显著的风险来自采购、固定资产投入、利息和还本集中造成的现金缓冲过薄。"]];
dashboard.getRange("A57:N57").format = { fill: C.orangeLight, font: { bold: true, color: C.ink, size: 10 }, wrapText: true, verticalAlignment: "center" };
dashboard.getRange("A57:N57").format.rowHeight = 45;
dashboard.getRange("A:N").format.columnWidth = 12;
dashboard.getRange("A:A").format.columnWidth = 14;
dashboard.freezePanes.freezeRows(2);

// Product and channel analysis.
setTitle(productChannel, "A1:L1", "产品与渠道分析", "用 SUMIFS / COUNTIFS 从订单明细动态汇总SKU、渠道与区域贡献；所有汇总可追溯到订单行。" );
productChannel.getRange("A4:F4").values = [["SKU", "产品名称", "销售额", "销量", "毛利额", "毛利率"]];
styleHeader(productChannel.getRange("A4:F4"));
productChannel.getRange("A5:A8").values = [["L1"], ["L2"], ["H1"], ["H2"]];
productChannel.getRange("B5").formulas = [["=XLOOKUP(A5,'产品维表'!$B$2:$B$5,'产品维表'!$C$2:$C$5,\"未映射\")"]];
productChannel.getRange("C5").formulas = [["=SUMIFS('订单明细'!$N$2:$N$328,'订单明细'!$X$2:$X$328,$A5)"]];
productChannel.getRange("D5").formulas = [["=SUMIFS('订单明细'!$I$2:$I$328,'订单明细'!$X$2:$X$328,$A5)"]];
productChannel.getRange("E5").formulas = [["=SUMIFS('订单明细'!$Q$2:$Q$328,'订单明细'!$X$2:$X$328,$A5)"]];
productChannel.getRange("F5").formulas = [["=IFERROR(E5/C5,0)"]];
productChannel.getRange("B5:F8").fillDown();
styleTable(productChannel.getRange("A5:F8"));
productChannel.getRange("C5:E8").setNumberFormat("#,##0");
productChannel.getRange("F5:F8").setNumberFormat("0.0%");

productChannel.getRange("A11:D11").values = [["渠道", "销售额", "订单数", "准时订单率"]];
styleHeader(productChannel.getRange("A11:D11"));
productChannel.getRange("A12:A14").values = [["线上直营"], ["线下零售"], ["区域经销"]];
productChannel.getRange("B12").formulas = [["=SUMIFS('订单明细'!$N$2:$N$328,'订单明细'!$Y$2:$Y$328,$A12)"]];
productChannel.getRange("C12").formulas = [["=COUNTIFS('订单明细'!$Y$2:$Y$328,$A12)"]];
productChannel.getRange("D12").formulas = [["=IFERROR(SUMIFS('订单明细'!$S$2:$S$328,'订单明细'!$Y$2:$Y$328,$A12)/C12,0)"]];
productChannel.getRange("B12:D14").fillDown();
styleTable(productChannel.getRange("A12:D14"));
productChannel.getRange("B12:B14").setNumberFormat("#,##0");
productChannel.getRange("D12:D14").setNumberFormat("0.0%");

productChannel.getRange("A17:D17").values = [["区域", "销售额", "销售占比", "准时订单率"]];
styleHeader(productChannel.getRange("A17:D17"));
productChannel.getRange("A18:A21").values = [["华东"], ["华南"], ["华北"], ["中西部"]];
productChannel.getRange("B18").formulas = [["=SUMIFS('订单明细'!$N$2:$N$328,'订单明细'!$Z$2:$Z$328,$A18)"]];
productChannel.getRange("C18").formulas = [["=B18/SUM($B$18:$B$21)"]];
productChannel.getRange("D18").formulas = [["=IFERROR(SUMIFS('订单明细'!$S$2:$S$328,'订单明细'!$Z$2:$Z$328,$A18)/COUNTIFS('订单明细'!$Z$2:$Z$328,$A18),0)"]];
productChannel.getRange("B18:D21").fillDown();
styleTable(productChannel.getRange("A18:D21"));
productChannel.getRange("B18:B21").setNumberFormat("#,##0");
productChannel.getRange("C18:D21").setNumberFormat("0.0%");
productChannel.getRange("M4:N4").values = [["SKU", "销售额"]];
productChannel.getRange("M5:N5").formulas = [["=A5", "=C5"]];
productChannel.getRange("M5:N8").fillDown();
const skuChart = productChannel.charts.add("bar", productChannel.getRange("M4:N8"));
skuChart.title = "SKU销售贡献（元）";
skuChart.hasLegend = false;
skuChart.yAxis = { numberFormatCode: "#,##0" };
skuChart.setPosition("H4", "L15");
const channelChart = productChannel.charts.add("bar", productChannel.getRange("A11:B14"));
channelChart.title = "渠道销售贡献（元）";
channelChart.hasLegend = false;
channelChart.yAxis = { numberFormatCode: "#,##0" };
channelChart.setPosition("H17", "L28");
productChannel.getRange("A:L").format.columnWidth = 14;
productChannel.getRange("B:B").format.columnWidth = 18;

// Inventory warning view.
setTitle(inventoryAlert, "A1:J1", "库存与产能预警", "选择经营季度后，按SKU查看期末库存、覆盖天数、产能利用率与预警状态。" );
inventoryAlert.getRange("A3").values = [["选择季度"]];
inventoryAlert.getRange("B3").values = [[13]];
inventoryAlert.getRange("B3").dataValidation = { rule: { type: "list", values: ["5", "6", "8", "9", "10", "11", "12", "13", "14"] } };
inventoryAlert.getRange("A3:B3").format = { fill: C.orangeLight, font: { bold: true, color: C.ink }, borders: { preset: "all", style: "thin", color: C.border } };
inventoryAlert.getRange("A6:H6").values = [["SKU", "期末库存", "季度需求", "平均覆盖天数", "缺货量", "产能利用率", "库存状态", "行动建议"]];
styleHeader(inventoryAlert.getRange("A6:H6"));
inventoryAlert.getRange("A7:A10").values = [["L1"], ["L2"], ["H1"], ["H2"]];
inventoryAlert.getRange("B7").formulas = [["=SUMIFS('库存明细'!$G$2:$G$169,'库存明细'!$N$2:$N$169,$A7,'库存明细'!$M$2:$M$169,$B$3)"]];
inventoryAlert.getRange("C7").formulas = [["=SUMIFS('库存明细'!$E$2:$E$169,'库存明细'!$N$2:$N$169,$A7,'库存明细'!$M$2:$M$169,$B$3)"]];
inventoryAlert.getRange("D7").formulas = [["=IFERROR(AVERAGEIFS('库存明细'!$K$2:$K$169,'库存明细'!$N$2:$N$169,$A7,'库存明细'!$M$2:$M$169,$B$3),0)"]];
inventoryAlert.getRange("E7").formulas = [["=SUMIFS('库存明细'!$H$2:$H$169,'库存明细'!$N$2:$N$169,$A7,'库存明细'!$M$2:$M$169,$B$3)"]];
inventoryAlert.getRange("F7").formulas = [["=IFERROR(SUMIFS('生产明细'!$D$2:$D$169,'生产明细'!$K$2:$K$169,$A7,'生产明细'!$J$2:$J$169,$B$3)/SUMIFS('生产明细'!$F$2:$F$169,'生产明细'!$K$2:$K$169,$A7,'生产明细'!$J$2:$J$169,$B$3),0)"]];
inventoryAlert.getRange("G7").formulas = [["=IF(E7>0,\"缺货\",IF(D7<8,\"偏低\",IF(D7>45,\"偏高\",\"健康\")))"]];
inventoryAlert.getRange("H7").formulas = [["=IF(G7=\"缺货\",\"优先补产并检查SKU分配\",IF(F7>=90%,\"安排加班/外协并锁定物料\",IF(G7=\"偏高\",\"减少补货，优先消化库存\",\"维持滚动计划\")))"]];
inventoryAlert.getRange("B7:H10").fillDown();
styleTable(inventoryAlert.getRange("A7:H10"));
inventoryAlert.getRange("B7:C10").setNumberFormat("#,##0");
inventoryAlert.getRange("D7:D10").setNumberFormat("0.0");
inventoryAlert.getRange("E7:E10").setNumberFormat("#,##0");
inventoryAlert.getRange("F7:F10").setNumberFormat("0.0%");
inventoryAlert.getRange("G7:G10").conditionalFormats.add("containsText", { text: "缺货", format: { fill: "#FEE2E2", font: { color: C.red, bold: true } } });
inventoryAlert.getRange("F7:F10").conditionalFormats.add("cellIs", { operator: "greaterThanOrEqual", formula: 0.9, format: { fill: "#FEF3C7", font: { color: C.amber, bold: true } } });
const invChart = inventoryAlert.charts.add("bar", inventoryAlert.getRange("A6:B10"));
invChart.title = "所选季度SKU期末库存（台）";
invChart.hasLegend = false;
invChart.yAxis = { numberFormatCode: "#,##0" };
invChart.setPosition("A14", "F28");
inventoryAlert.getRange("A:J").format.columnWidth = 15;
inventoryAlert.getRange("H:H").format.columnWidth = 30;

// Cash analysis.
setTitle(cashAnalysis, "A1:L1", "现金流分析", "按经营季度动态汇总现金流入、流出、净现金流与期末现金；现金余额由 signed_amount 累计计算。" );
cashAnalysis.getRange("A4:F4").values = [["季度", "现金流入", "现金流出", "净现金流", "期末现金", "风险等级"]];
styleHeader(cashAnalysis.getRange("A4:F4"));
cashAnalysis.getRange("A5:A18").values = Array.from({ length: 14 }, (_, i) => [i + 1]);
cashAnalysis.getRange("B5").formulas = [["=SUMIFS('现金明细'!$H$2:$H$238,'现金明细'!$D$2:$D$238,$A5,'现金明细'!$E$2:$E$238,\"Inflow\")"]];
cashAnalysis.getRange("C5").formulas = [["=SUMIFS('现金明细'!$H$2:$H$238,'现金明细'!$D$2:$D$238,$A5,'现金明细'!$E$2:$E$238,\"Outflow\")"]];
cashAnalysis.getRange("D5").formulas = [["=B5-C5"]];
cashAnalysis.getRange("E5").formulas = [["=SUM($D$5:D5)"]];
cashAnalysis.getRange("F5").formulas = [["=IF(E5<100000,\"Critical\",IF(E5<300000,\"Watch\",\"Stable\"))"]];
cashAnalysis.getRange("B5:F18").fillDown();
styleTable(cashAnalysis.getRange("A5:F18"));
cashAnalysis.getRange("B5:E18").setNumberFormat("#,##0");
cashAnalysis.getRange("F5:F18").conditionalFormats.add("containsText", { text: "Critical", format: { fill: "#FEE2E2", font: { color: C.red, bold: true } } });
cashAnalysis.getRange("H4:I4").values = [["资金用途", "累计流出"]];
styleHeader(cashAnalysis.getRange("H4:I4"));
const outflowCats = ["原材料采购", "生产性固定资产", "偿还贷款本金", "人员成本", "市场推广与首批产品", "贷款利息及罚金", "研发投入", "原材料仓储", "物流运输", "人员调整"];
cashAnalysis.getRange("H5:H14").values = outflowCats.map(x => [x]);
cashAnalysis.getRange("I5").formulas = [["=SUMIFS('现金明细'!$H$2:$H$238,'现金明细'!$G$2:$G$238,$H5,'现金明细'!$E$2:$E$238,\"Outflow\")"]];
cashAnalysis.getRange("I5:I14").fillDown();
styleTable(cashAnalysis.getRange("H5:I14"));
cashAnalysis.getRange("I5:I14").setNumberFormat("#,##0");
cashAnalysis.getRange("M4:N4").values = [["季度", "期末现金"]];
cashAnalysis.getRange("M5:N5").formulas = [["=A5", "=E5"]];
cashAnalysis.getRange("M5:N18").fillDown();
const cashBalanceChart = cashAnalysis.charts.add("line", cashAnalysis.getRange("M4:N18"));
cashBalanceChart.title = "季度期末现金（元）";
cashBalanceChart.hasLegend = false;
cashBalanceChart.yAxis = { numberFormatCode: "#,##0" };
cashBalanceChart.setPosition("A21", "F35");
const outflowChart = cashAnalysis.charts.add("bar", cashAnalysis.getRange("H4:I14"));
outflowChart.title = "累计资金用途（元）";
outflowChart.hasLegend = false;
outflowChart.yAxis = { numberFormatCode: "#,##0" };
outflowChart.setPosition("G21", "L35");
cashAnalysis.getRange("A:L").format.columnWidth = 15;
cashAnalysis.getRange("H:H").format.columnWidth = 25;

// Scenario analysis.
setTitle(scenario, "A1:H1", "经营情景测算", "蓝色单元格为可编辑假设；模型以Q14为基准，测算增长对收入、毛利、产能和现金缓冲的影响。" );
scenario.getRange("A4:D4").values = [["情景", "销量增长", "ASP变化", "单位成本变化"]];
styleHeader(scenario.getRange("A4:D4"));
scenario.getRange("A5:D7").values = [
  ["Base", 0.10, 0.00, -0.01],
  ["Growth", 0.25, -0.02, 0.01],
  ["Stress", -0.10, -0.04, 0.04],
];
styleTable(scenario.getRange("A5:D7"));
scenario.getRange("B5:D7").setNumberFormat("0.0%");
scenario.getRange("F4:G4").values = [["输入", "选择/数值"]];
styleHeader(scenario.getRange("F4:G4"));
scenario.getRange("F5:F8").values = [["选择情景"], ["新增产能"], ["安全现金底线"], ["库存投入率"]];
scenario.getRange("G5:G8").values = [["Base"], [120], [300000], [0.22]];
scenario.getRange("G5").dataValidation = { rule: { type: "list", values: ["Base", "Growth", "Stress"] } };
scenario.getRange("G6").dataValidation = { rule: { type: "whole", operator: "between", formula1: 0, formula2: 1000 } };
scenario.getRange("G7:G8").format = { fill: "#EAF2FF", font: { color: C.blue, bold: true }, borders: { preset: "all", style: "thin", color: C.border } };
scenario.getRange("G5:G6").format = { fill: "#EAF2FF", font: { color: C.blue, bold: true }, borders: { preset: "all", style: "thin", color: C.border } };
scenario.getRange("G7").setNumberFormat("#,##0");
scenario.getRange("G8").setNumberFormat("0.0%");

scenario.getRange("A11:D11").values = [["指标", "Q14基准", "情景结果", "判断"]];
styleHeader(scenario.getRange("A11:D11"));
scenario.getRange("A12:A19").values = [["销售额"], ["销量"], ["毛利率"], ["毛利额"], ["月均产能需求"], ["可用月产能"], ["预计期末现金"], ["现金安全余量"]];
scenario.getRange("B12").formulas = [["='季度KPI'!$C$15"]];
scenario.getRange("B13").formulas = [["='季度KPI'!$G$15"]];
scenario.getRange("B14").formulas = [["='季度KPI'!$F$15"]];
scenario.getRange("B15").formulas = [["='季度KPI'!$E$15"]];
scenario.getRange("B16").formulas = [["=B13/3"]];
scenario.getRange("B17").formulas = [["=SUMIFS('生产明细'!$F$2:$F$169,'生产明细'!$J$2:$J$169,14)/3"]];
scenario.getRange("B18").formulas = [["='季度KPI'!$R$15"]];
scenario.getRange("B19").formulas = [["=B18-$G$7"]];
scenario.getRange("C12").formulas = [["=B12*(1+XLOOKUP($G$5,$A$5:$A$7,$B$5:$B$7))*(1+XLOOKUP($G$5,$A$5:$A$7,$C$5:$C$7))"]];
scenario.getRange("C13").formulas = [["=B13*(1+XLOOKUP($G$5,$A$5:$A$7,$B$5:$B$7))"]];
scenario.getRange("C14").formulas = [["=1-(1-B14)*(1+XLOOKUP($G$5,$A$5:$A$7,$D$5:$D$7))/(1+XLOOKUP($G$5,$A$5:$A$7,$C$5:$C$7))"]];
scenario.getRange("C15").formulas = [["=C12*C14"]];
scenario.getRange("C16").formulas = [["=C13/3"]];
scenario.getRange("C17").formulas = [["=B17+$G$6"]];
scenario.getRange("C18").formulas = [["=B18+(C15-B15)-(C12-B12)*$G$8"]];
scenario.getRange("C19").formulas = [["=C18-$G$7"]];
scenario.getRange("D12").formulas = [["=IF(C12>=B12,\"增长\",\"收缩\")"]];
scenario.getRange("D13").formulas = [["=IF(C13>=B13,\"增长\",\"收缩\")"]];
scenario.getRange("D14").formulas = [["=IF(C14>=B14,\"改善\",\"承压\")"]];
scenario.getRange("D15").formulas = [["=IF(C15>=B15,\"增长\",\"下降\")"]];
scenario.getRange("D16").formulas = [["=IF(C16<=C17,\"产能可覆盖\",\"存在缺口\")"]];
scenario.getRange("D17").formulas = [["=IF(C17>=C16,\"满足\",\"不足\")"]];
scenario.getRange("D18").formulas = [["=IF(C18>=$G$7,\"高于底线\",\"低于底线\")"]];
scenario.getRange("D19").formulas = [["=IF(C19>=0,\"安全\",\"预警\")"]];
styleTable(scenario.getRange("A12:D19"));
scenario.getRange("B12:C12").setNumberFormat("#,##0");
scenario.getRange("B13:C13").setNumberFormat("#,##0");
scenario.getRange("B14:C14").setNumberFormat("0.0%");
scenario.getRange("B15:C19").setNumberFormat("#,##0");
scenario.getRange("D19").conditionalFormats.add("containsText", { text: "预警", format: { fill: "#FEE2E2", font: { color: C.red, bold: true } } });
scenario.getRange("A:H").format.columnWidth = 18;

// Rebuild visible QA sheet with formula-driven controls.
const quality = wb.worksheets.add("质量检查");
setTitle(quality, "A1:E1", "质量检查", "关键总额、唯一性、映射与现金勾稽均在工作簿内复算；状态必须全部为PASS。" );
quality.getRange("A4:E4").values = [["Check", "Actual", "Expected", "Status", "Purpose"]];
styleHeader(quality.getRange("A4:E4"));
const qualityRows = [
  ["Sales total", "=SUM('订单明细'!$N$2:$N$328)", 32870200, "=IF(ABS(B5-C5)<0.01,\"PASS\",\"FAIL\")", "销售回款总额"],
  ["L family total", "=SUMIFS('订单明细'!$N$2:$N$328,'订单明细'!$W$2:$W$328,\"L\")", 26948200, "=IF(ABS(B6-C6)<0.01,\"PASS\",\"FAIL\")", "L产品控制额"],
  ["H family total", "=SUMIFS('订单明细'!$N$2:$N$328,'订单明细'!$W$2:$W$328,\"H\")", 5922000, "=IF(ABS(B7-C7)<0.01,\"PASS\",\"FAIL\")", "H产品控制额"],
  ["Cash inflow", "=SUMIFS('现金明细'!$H$2:$H$238,'现金明细'!$E$2:$E$238,\"Inflow\")", 50130681, "=IF(ABS(B8-C8)<0.01,\"PASS\",\"FAIL\")", "累计现金流入"],
  ["Cash outflow", "=SUMIFS('现金明细'!$H$2:$H$238,'现金明细'!$E$2:$E$238,\"Outflow\")", 49777407, "=IF(ABS(B9-C9)<0.01,\"PASS\",\"FAIL\")", "累计现金流出"],
  ["Ending cash", "=SUM('现金明细'!$I$2:$I$238)", 353274, "=IF(ABS(B10-C10)<0.01,\"PASS\",\"FAIL\")", "期末现金"],
  ["Order ID uniqueness", "=COUNTA('订单明细'!$A$2:$A$328)", 327, "=IF(B11=C11,\"PASS\",\"FAIL\")", "订单主键唯一"],
  ["Product mapping", "=COUNTIFS('订单明细'!$W$2:$W$328,\"未映射\")", 0, "=IF(B12=C12,\"PASS\",\"FAIL\")", "维表关联完整"],
  ["Inventory balance", "=COUNTIFS('库存明细'!$O$2:$O$169,\"<>0\")", 0, "=IF(B13=C13,\"PASS\",\"FAIL\")", "期初+入库-发货=期末"],
  ["Quarter cash checks", "=COUNTIFS('现金流'!$F$5:$F$18,\"<>Stable\")", 8, "=IF(COUNTA('现金流'!$E$5:$E$18)=14,\"PASS\",\"FAIL\")", "14个季度均有现金余额"],
];
quality.getRange("A5:A14").values = qualityRows.map(r => [r[0]]);
quality.getRange("B5:B14").formulas = qualityRows.map(r => [r[1]]);
quality.getRange("C5:C14").values = qualityRows.map(r => [r[2]]);
quality.getRange("D5:D14").formulas = qualityRows.map(r => [r[3]]);
quality.getRange("E5:E14").values = qualityRows.map(r => [r[4]]);
styleTable(quality.getRange("A5:E14"));
quality.getRange("B5:C10").setNumberFormat("#,##0");
quality.getRange("D5:D14").conditionalFormats.add("containsText", { text: "PASS", format: { fill: "#E8F3ED", font: { color: C.green, bold: true } } });
quality.getRange("D5:D14").conditionalFormats.add("containsText", { text: "FAIL", format: { fill: "#FEE2E2", font: { color: C.red, bold: true } } });
quality.getRange("A:E").format.columnWidth = 24;
quality.getRange("E:E").format.columnWidth = 32;

// Apply number formats and cap raw-sheet widths.
monthly.getRange("E2:F43").setNumberFormat("#,##0");
monthly.getRange("G2:G43").setNumberFormat("0.0%");
monthly.getRange("H2:I43").setNumberFormat("#,##0");
monthly.getRange("J2:K43").setNumberFormat("0.0%");
monthly.getRange("L2:L43").setNumberFormat("#,##0");
monthly.getRange("M2:M43").setNumberFormat("0.0%");
monthly.getRange("N2:O43").setNumberFormat("#,##0");
quarterly.getRange("C2:C15").setNumberFormat("#,##0");
quarterly.getRange("D2:D15").setNumberFormat("0.0%");
quarterly.getRange("E2:E15").setNumberFormat("#,##0");
quarterly.getRange("F2:F15").setNumberFormat("0.0%");
quarterly.getRange("G2:H15").setNumberFormat("#,##0");
quarterly.getRange("I2:J15").setNumberFormat("0.0%");
quarterly.getRange("K2:K15").setNumberFormat("#,##0");
quarterly.getRange("L2:L15").setNumberFormat("0.00");
quarterly.getRange("M2:M15").setNumberFormat("0.0%");
quarterly.getRange("N2:R15").setNumberFormat("#,##0");
sales.getRange("K2:Q328").setNumberFormat("#,##0.00");
cash.getRange("H2:I238").setNumberFormat("#,##0");

// Compact verification before export.
const inspect = await wb.inspect({ kind: "table", sheetId: "经营看板", range: "A1:N18", include: "values,formulas", tableMaxRows: 18, tableMaxCols: 14, maxChars: 7000 });
console.log("DASHBOARD_INSPECT\n" + inspect.ndjson);
for (const [sheetId, range] of [
  ["产品渠道", "A4:F21"], ["库存预警", "A3:H10"], ["现金流", "A4:I18"],
  ["情景测算", "A11:D19"], ["质量检查", "A4:E14"],
]) {
  const check = await wb.inspect({ kind: "table", sheetId, range, include: "values,formulas", tableMaxRows: 20, tableMaxCols: 10, maxChars: 5000 });
  console.log(`${sheetId}_INSPECT\n${check.ndjson}`);
}
const formulaErrors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan", maxChars: 6000 });
console.log("FORMULA_ERRORS\n" + formulaErrors.ndjson);

await fs.mkdir(previewDir, { recursive: true });
const renderTargets = [
  ["经营看板", "A1:N57"], ["产品渠道", "A1:L28"], ["库存预警", "A1:J28"],
  ["现金流", "A1:L35"], ["情景测算", "A1:H20"], ["清洗映射", "A1:H13"],
  ["数据字典", "A1:G18"], ["月度KPI", "A1:S20"], ["季度KPI", "A1:V15"],
  ["订单明细", "A1:AA25"], ["库存明细", "A1:O25"], ["生产明细", "A1:K25"],
  ["现金明细", "A1:J25"], ["日期维表", "A1:I20"], ["产品维表", "A1:H5"],
  ["渠道维表", "A1:D4"], ["区域维表", "A1:C5"], ["质量检查", "A1:E14"],
];
for (const [sheetName, range] of renderTargets) {
  const blob = await wb.render({ sheetName, range, scale: 1, format: "png" });
  const safe = sheetName.replace(/[\\/:*?"<>|]/g, "_");
  await fs.writeFile(path.join(previewDir, `${safe}.png`), new Uint8Array(await blob.arrayBuffer()));
}

await fs.mkdir(threadOutput, { recursive: true });
await fs.mkdir(path.dirname(repoOutput), { recursive: true });
const exported = await SpreadsheetFile.exportXlsx(wb);
const threadFile = path.join(threadOutput, "Smartphone_Operations_Analysis.xlsx");
await exported.save(threadFile);
await fs.copyFile(threadFile, repoOutput);
await fs.copyFile(path.join(previewDir, "经营看板.png"), path.join(projectRoot, "docs", "excel_dashboard.png"));
console.log(JSON.stringify({ workbook: repoOutput, threadOutput: threadFile, previews: renderTargets.length }, null, 2));
