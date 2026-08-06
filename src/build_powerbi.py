"""Build the version-controlled Power BI Project (PBIP) source tree.

The project uses MySQL import-mode partitions. Credentials are intentionally
not embedded; Power BI Desktop prompts for them and stores them in the local
Power BI credential store.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
POWERBI_DIR = ROOT / "powerbi"
PROJECT_NAME = "SmartphoneOperationsAnalytics"
REPORT_DIR = POWERBI_DIR / f"{PROJECT_NAME}.Report"
MODEL_DIR = POWERBI_DIR / f"{PROJECT_NAME}.SemanticModel"
REPORT_DEFINITION = REPORT_DIR / "definition"
MODEL_DEFINITION = MODEL_DIR / "definition"
VISUAL_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/visualContainer/2.9.0/schema.json"
)
THEME_FILE = "SmartphoneOperationsTheme-20260806.json"

DISPLAY_NAMES = {
    "business_quarter": "经营季度",
    "month_label": "月份",
    "product_name": "产品 / SKU",
    "channel_name": "销售渠道",
    "region_name": "销售区域",
    "flow_category_cn": "现金用途",
    "sku": "SKU",
    "product_family": "产品家族",
    "Total Sales": "销售额",
    "Gross Profit": "毛利额",
    "Gross Margin": "毛利率",
    "COGS": "销售成本",
    "Ordered Units": "下单数量",
    "Shipped Units": "发货数量",
    "Fill Rate": "数量履约率",
    "On-time Order Rate": "按时订单率",
    "Average Delivery Days": "平均交付天数",
    "Average Selling Price": "平均成交价",
    "Produced Units": "实际投产量",
    "Capacity Units": "分配产能",
    "Capacity Utilization": "产能利用率",
    "Ending Inventory": "期末库存",
    "Inventory Value": "库存金额",
    "Days of Supply": "库存覆盖天数",
    "Stockout Units": "缺货数量",
    "Inventory Turnover": "库存周转",
    "Cash Inflow": "现金流入",
    "Cash Outflow": "现金流出",
    "Net Cashflow": "净现金流",
    "Closing Cash": "期末现金",
    "Sales QoQ": "销售环比",
}


def stable_hex(label: str, length: int = 20) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()[:length]


def stable_uuid(label: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"nanhu-mobile-analytics/{label}"))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, content: Any) -> None:
    write_text(path, json.dumps(content, ensure_ascii=False, indent=2))


def literal(value: Any) -> dict[str, Any]:
    if isinstance(value, bool):
        encoded = "true" if value else "false"
    elif isinstance(value, int):
        encoded = f"{value}L"
    elif isinstance(value, float):
        encoded = f"{value}D"
    else:
        encoded = f"'{str(value).replace(chr(39), chr(39) * 2)}'"
    return {"expr": {"Literal": {"Value": encoded}}}


def color(hex_value: str) -> dict[str, Any]:
    return {"solid": {"color": {"expr": {"Literal": {"Value": f"'{hex_value}'"}}}}}


def field_column(table: str, column_name: str) -> dict[str, Any]:
    return {
        "Column": {
            "Expression": {"SourceRef": {"Entity": table}},
            "Property": column_name,
        }
    }


def field_measure(measure_name: str) -> dict[str, Any]:
    return {
        "Measure": {
            "Expression": {"SourceRef": {"Entity": "_Measures"}},
            "Property": measure_name,
        }
    }


def column_projection(table: str, column_name: str, active: bool | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "field": field_column(table, column_name),
        "queryRef": f"{table}.{column_name}",
        "nativeQueryRef": DISPLAY_NAMES.get(column_name, column_name),
    }
    if active is not None:
        result["active"] = active
    return result


def measure_projection(measure_name: str) -> dict[str, Any]:
    return {
        "field": field_measure(measure_name),
        "queryRef": f"_Measures.{measure_name}",
        "nativeQueryRef": DISPLAY_NAMES.get(measure_name, measure_name),
    }


def visual_container(title: str | None = None, show_title: bool = True) -> dict[str, Any]:
    objects: dict[str, Any] = {
        "background": [
            {"properties": {"show": literal(True), "color": color("#FFFFFF"), "transparency": literal(0.0)}}
        ],
        "border": [
            {
                "properties": {
                    "show": literal(True),
                    "color": color("#E6E6E6"),
                    "width": literal(1.0),
                    "radius": literal(6.0),
                }
            }
        ],
        "visualHeader": [{"properties": {"show": literal(True)}}],
        "padding": [
            {
                "properties": {
                    "top": literal(6.0),
                    "bottom": literal(6.0),
                    "left": literal(8.0),
                    "right": literal(8.0),
                }
            }
        ],
    }
    if title is not None:
        objects["title"] = [
            {
                "properties": {
                    "show": literal(show_title),
                    "text": literal(title),
                    "fontSize": literal(12.0),
                    "fontFamily": literal("Segoe UI Semibold"),
                    "fontColor": color("#2B2B2B"),
                    "titleWrap": literal(True),
                }
            }
        ]
    return objects


def make_visual(
    page_name: str,
    label: str,
    x: float,
    y: float,
    width: float,
    height: float,
    z: int,
    visual: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    visual_id = stable_hex(f"{page_name}/{label}")
    payload = {
        "$schema": VISUAL_SCHEMA,
        "name": visual_id,
        "position": {
            "x": x,
            "y": y,
            "z": z,
            "height": height,
            "width": width,
            "tabOrder": z,
        },
        "visual": visual,
    }
    return visual_id, payload


def textbox(text: str, size_pt: int, font_weight: str = "normal", color_hex: str = "#242424") -> dict[str, Any]:
    return {
        "visualType": "textbox",
        "objects": {
            "general": [
                {
                    "properties": {
                        "paragraphs": [
                            {
                                "textRuns": [
                                    {
                                        "value": text,
                                        "textStyle": {
                                            "fontFamily": "Segoe UI",
                                            "fontSize": f"{size_pt}pt",
                                            "fontWeight": font_weight,
                                            "color": color_hex,
                                        },
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        },
        "visualContainerObjects": {
            "background": [{"properties": {"show": literal(False)}}],
            "visualHeader": [{"properties": {"show": literal(False)}}],
        },
    }


def slicer(table: str, column_name: str, title: str) -> dict[str, Any]:
    return {
        "visualType": "slicer",
        "query": {
            "queryState": {"Values": {"projections": [column_projection(table, column_name)]}},
            "sortDefinition": {
                "sort": [{"field": field_column(table, column_name), "direction": "Ascending"}],
                "isDefaultSort": True,
            },
        },
        "objects": {
            "data": [{"properties": {"mode": literal("Dropdown")}}],
            "header": [{"properties": {"show": literal(False), "showRestatement": literal(False)}}],
            "selection": [
                {
                    "properties": {
                        "selectAllCheckboxEnabled": literal(True),
                        "singleSelect": literal(False),
                        "strictSingleSelect": literal(False),
                    }
                }
            ],
        },
        "visualContainerObjects": visual_container(title),
        "drillFilterOtherVisuals": True,
    }


def card(measures: Iterable[str]) -> dict[str, Any]:
    projections = [measure_projection(name) for name in measures]
    count = len(projections)
    return {
        "visualType": "cardVisual",
        "query": {"queryState": {"Data": {"projections": projections}}},
        "objects": {
            "value": [
                {
                    "properties": {
                        "fontSize": literal(22.0),
                        "fontFamily": literal("Segoe UI Semibold"),
                        "fontColor": color("#F56600"),
                        "horizontalAlignment": literal("left"),
                    },
                    "selector": {"id": "default"},
                }
            ],
            "label": [
                {
                    "properties": {
                        "position": literal("aboveValue"),
                        "fontSize": literal(9.0),
                        "fontColor": color("#686868"),
                    },
                    "selector": {"id": "default"},
                }
            ],
            "layout": [
                {
                    "properties": {
                        "style": literal("Cards"),
                        "rowCount": literal(1),
                        "columnCount": literal(count),
                        "maxTiles": literal(count),
                        "autoGrid": literal(False),
                        "cellPadding": literal(5),
                        "backgroundShow": literal(False),
                    }
                }
            ],
            "fillCustom": [{"properties": {"show": literal(False)}}],
        },
        "visualContainerObjects": visual_container(None),
    }


SERIES_COLORS = ["#F56600", "#3D3D3D", "#5B8FF9", "#2D7D46", "#D64545"]


def cartesian_chart(
    visual_type: str,
    category_table: str,
    category_column: str,
    measures: list[str],
    title: str,
    sort_by: str = "category",
    show_labels: bool = False,
) -> dict[str, Any]:
    query: dict[str, Any] = {
        "queryState": {
            "Category": {"projections": [column_projection(category_table, category_column, active=True)]},
            "Y": {"projections": [measure_projection(name) for name in measures]},
        }
    }
    sort_field = field_column(category_table, category_column) if sort_by == "category" else field_measure(measures[0])
    query["sortDefinition"] = {
        "sort": [
            {
                "field": sort_field,
                "direction": "Ascending" if sort_by == "category" else "Descending",
            }
        ],
        "isDefaultSort": True,
    }

    data_points = []
    line_styles = []
    for idx, name in enumerate(measures):
        series_color = SERIES_COLORS[idx % len(SERIES_COLORS)]
        point_properties = {"fill": color(series_color)}
        point_properties["transparency" if visual_type == "lineChart" else "fillTransparency"] = literal(0.0)
        data_points.append(
            {
                "properties": point_properties,
                "selector": {"metadata": f"_Measures.{name}"},
            }
        )
        line_styles.append(
            {
                "properties": {
                    "strokeShow": literal(True),
                    "strokeWidth": literal(3.0),
                    "strokeColor": color(series_color),
                    "showMarker": literal(True),
                    "markerSize": literal(5.0),
                    "markerShape": literal("circle"),
                },
                "selector": {"metadata": f"_Measures.{name}"},
            }
        )

    objects: dict[str, Any] = {
        "categoryAxis": [
            {
                "properties": {
                    "show": literal(True),
                    "fontSize": literal(9.0),
                    "labelColor": color("#686868"),
                    "showAxisTitle": literal(False),
                    "preferredCategoryWidth": literal(20.0),
                }
            }
        ],
        "valueAxis": [
            {
                "properties": {
                    "show": literal(True),
                    "fontSize": literal(9.0),
                    "labelColor": color("#686868"),
                    "gridlineStyle": literal("dotted"),
                    "gridlineColor": color("#E8E8E8"),
                    "showAxisTitle": literal(False),
                }
            }
        ],
        "legend": [
            {"properties": {"show": literal(len(measures) > 1), "position": literal("TopCenter")}}
        ],
        "dataPoint": data_points,
        "labels": [{"properties": {"show": literal(show_labels), "fontSize": literal(8.0)}}],
    }
    if visual_type == "lineChart":
        objects["lineStyles"] = line_styles

    return {
        "visualType": visual_type,
        "query": query,
        "objects": objects,
        "visualContainerObjects": visual_container(title),
        "drillFilterOtherVisuals": True,
    }


def table_visual(fields: list[tuple[str, str, str]], title: str) -> dict[str, Any]:
    projections: list[dict[str, Any]] = []
    for kind, table, name in fields:
        projections.append(column_projection(table, name) if kind == "column" else measure_projection(name))
    return {
        "visualType": "tableEx",
        "query": {"queryState": {"Values": {"projections": projections}}},
        "objects": {
            "columnHeaders": [
                {
                    "properties": {
                        "autoSizeColumnWidth": literal(True),
                        "columnAdjustment": literal("growToFit"),
                        "fontColor": color("#FFFFFF"),
                        "backColor": color("#3D3D3D"),
                        "bold": literal(True),
                    }
                }
            ],
            "values": [
                {
                    "properties": {
                        "fontColorPrimary": color("#2B2B2B"),
                        "fontColorSecondary": color("#2B2B2B"),
                        "backColorPrimary": color("#FFFFFF"),
                        "backColorSecondary": color("#FFF5EE"),
                        "wordWrap": literal(False),
                    }
                }
            ],
        },
        "visualContainerObjects": {
            **visual_container(title),
            "stylePreset": [{"properties": {"name": literal("None")}}],
        },
    }


def column_tmdl(
    name: str,
    data_type: str,
    *,
    source: str | None = None,
    hidden: bool = False,
    key: bool = False,
    fmt: str | None = None,
    sort_by: str | None = None,
) -> str:
    quote = "'" if any(ch in name for ch in " .-()/%") else ""
    display = f"{quote}{name}{quote}"
    lines = [f"\tcolumn {display}", f"\t\tdataType: {data_type}"]
    if hidden:
        lines.append("\t\tisHidden")
    if key:
        lines.append("\t\tisKey")
    lines.append("\t\tsummarizeBy: none")
    if fmt:
        lines.append(f"\t\tformatString: {fmt}")
    if sort_by:
        sort_quote = "'" if any(ch in sort_by for ch in " .-()/%") else ""
        lines.append(f"\t\tsortByColumn: {sort_quote}{sort_by}{sort_quote}")
    lines.append(f"\t\tsourceColumn: {source or name}")
    return "\n".join(lines)


TABLES: dict[str, list[dict[str, Any]]] = {
    "dim_date": [
        {"name": "date_key", "type": "int64", "hidden": True, "key": True},
        {"name": "month_start", "type": "dateTime", "fmt": "yyyy-mm-dd"},
        {"name": "year", "type": "int64"},
        {"name": "month_number", "type": "int64", "hidden": True},
        {"name": "month_label", "type": "string", "sort_by": "date_key"},
        {"name": "quarter_seq", "type": "int64", "hidden": True},
        {"name": "business_quarter", "type": "string", "sort_by": "quarter_seq"},
        {"name": "year_quarter", "type": "string", "sort_by": "quarter_seq"},
        {"name": "month_in_quarter", "type": "int64"},
    ],
    "dim_product": [
        {"name": "product_key", "type": "int64", "hidden": True, "key": True},
        {"name": "sku", "type": "string"},
        {"name": "product_name", "type": "string"},
        {"name": "product_family", "type": "string"},
        {"name": "positioning", "type": "string"},
        {"name": "list_price", "type": "decimal", "fmt": "¥#,##0.00"},
        {"name": "standard_unit_cost", "type": "decimal", "fmt": "¥#,##0.00"},
        {"name": "launch_month_key", "type": "int64", "hidden": True},
    ],
    "dim_channel": [
        {"name": "channel_key", "type": "int64", "hidden": True, "key": True},
        {"name": "channel_name", "type": "string"},
        {"name": "channel_type", "type": "string"},
        {"name": "price_factor", "type": "decimal", "fmt": "0.0000"},
    ],
    "dim_region": [
        {"name": "region_key", "type": "int64", "hidden": True, "key": True},
        {"name": "region_name", "type": "string"},
        {"name": "region_tier", "type": "string"},
    ],
    "fact_sales_order": [
        {"name": "order_id", "type": "string", "key": True},
        {"name": "order_date_key", "type": "int64", "hidden": True},
        {"name": "order_date", "type": "dateTime", "fmt": "yyyy-mm-dd"},
        {"name": "promised_date", "type": "dateTime", "fmt": "yyyy-mm-dd"},
        {"name": "shipped_date", "type": "dateTime", "fmt": "yyyy-mm-dd"},
        {"name": "product_key", "type": "int64", "hidden": True},
        {"name": "channel_key", "type": "int64", "hidden": True},
        {"name": "region_key", "type": "int64", "hidden": True},
        {"name": "ordered_qty", "type": "int64"},
        {"name": "shipped_qty", "type": "int64"},
        {"name": "unit_price", "type": "decimal", "fmt": "¥#,##0.00"},
        {"name": "gross_sales", "type": "decimal", "fmt": "¥#,##0.00"},
        {"name": "discount_amount", "type": "decimal", "fmt": "¥#,##0.00"},
        {"name": "net_sales", "type": "decimal", "fmt": "¥#,##0.00"},
        {"name": "unit_cost", "type": "decimal", "fmt": "¥#,##0.00"},
        {"name": "cogs", "type": "decimal", "fmt": "¥#,##0.00"},
        {"name": "gross_profit", "type": "decimal", "fmt": "¥#,##0.00"},
        {"name": "delivery_days", "type": "int64"},
        {"name": "on_time_flag", "type": "int64", "hidden": True},
        {"name": "full_fill_flag", "type": "int64", "hidden": True},
        {"name": "order_status", "type": "string"},
        {"name": "payment_term_days", "type": "int64"},
    ],
    "fact_production": [
        {"name": "month_key", "type": "int64", "hidden": True},
        {"name": "product_key", "type": "int64", "hidden": True},
        {"name": "planned_units", "type": "int64"},
        {"name": "actual_good_units", "type": "int64"},
        {"name": "defect_units", "type": "int64"},
        {"name": "capacity_allocated_units", "type": "int64"},
        {"name": "downtime_hours", "type": "decimal", "fmt": "#,##0.0"},
        {"name": "overtime_hours", "type": "decimal", "fmt": "#,##0.0"},
        {"name": "capacity_utilization", "type": "decimal", "fmt": "0.00%"},
    ],
    "fact_inventory": [
        {"name": "month_key", "type": "int64", "hidden": True},
        {"name": "product_key", "type": "int64", "hidden": True},
        {"name": "beginning_inventory_qty", "type": "int64"},
        {"name": "production_receipts_qty", "type": "int64"},
        {"name": "demand_qty", "type": "int64"},
        {"name": "shipped_qty", "type": "int64"},
        {"name": "ending_inventory_qty", "type": "int64"},
        {"name": "stockout_qty", "type": "int64"},
        {"name": "inventory_value", "type": "decimal", "fmt": "¥#,##0.00"},
        {"name": "warehouse_capacity_qty", "type": "int64"},
        {"name": "days_of_supply", "type": "decimal", "fmt": "#,##0.0"},
        {"name": "inventory_status", "type": "string"},
    ],
    "fact_cashflow": [
        {"name": "cashflow_id", "type": "string", "key": True},
        {"name": "date_key", "type": "int64", "hidden": True},
        {"name": "transaction_date", "type": "dateTime", "fmt": "yyyy-mm-dd"},
        {"name": "quarter_seq", "type": "int64", "hidden": True},
        {"name": "flow_direction", "type": "string"},
        {"name": "flow_category", "type": "string"},
        {"name": "flow_category_cn", "type": "string"},
        {"name": "amount", "type": "decimal", "fmt": "¥#,##0.00"},
        {"name": "signed_amount", "type": "decimal", "fmt": "¥#,##0.00;[Red]-¥#,##0.00"},
        {"name": "control_source", "type": "string"},
    ],
}


MEASURES: list[tuple[str, str, str, str]] = [
    ("Total Sales", "SUM(fact_sales_order[net_sales])", "¥#,##0", "销售订单净额；与经营流水中的销售回款控制总额对账。"),
    ("Gross Profit", "SUM(fact_sales_order[gross_profit])", "¥#,##0", "净销售额减销售成本。"),
    ("Gross Margin", "DIVIDE([Gross Profit], [Total Sales])", "0.00%", "毛利额占净销售额的比例。"),
    ("COGS", "SUM(fact_sales_order[cogs])", "¥#,##0", "已发货订单的销售成本。"),
    ("Ordered Units", "SUM(fact_sales_order[ordered_qty])", "#,##0", "客户下单数量。"),
    ("Shipped Units", "SUM(fact_sales_order[shipped_qty])", "#,##0", "实际发货数量。"),
    ("Fill Rate", "DIVIDE([Shipped Units], [Ordered Units])", "0.00%", "发货数量除以下单数量。"),
    ("On-time Order Rate", "DIVIDE(SUM(fact_sales_order[on_time_flag]), COUNTROWS(fact_sales_order))", "0.00%", "按订单口径计算的承诺期内交付率。"),
    ("Average Delivery Days", "AVERAGE(fact_sales_order[delivery_days])", "0.0", "订单从下单到发货的平均天数。"),
    ("Average Selling Price", "DIVIDE([Total Sales], [Shipped Units])", "¥#,##0", "净销售额除以发货数量。"),
    ("Produced Units", "SUM(fact_production[actual_good_units]) + SUM(fact_production[defect_units])", "#,##0", "良品与不良品合计的实际投产数量。"),
    ("Capacity Units", "SUM(fact_production[capacity_allocated_units])", "#,##0", "可用产能分配数量。"),
    ("Capacity Utilization", "DIVIDE([Produced Units], [Capacity Units])", "0.00%", "实际投产数量除以分配产能。"),
    ("Ending Inventory", "VAR LastMonth = MAX(dim_date[date_key]) RETURN CALCULATE(SUM(fact_inventory[ending_inventory_qty]), dim_date[date_key] = LastMonth)", "#,##0", "当前筛选范围最后一个月的期末库存快照。"),
    ("Inventory Value", "VAR LastMonth = MAX(dim_date[date_key]) RETURN CALCULATE(SUM(fact_inventory[inventory_value]), dim_date[date_key] = LastMonth)", "¥#,##0", "当前筛选范围最后一个月的库存金额快照。"),
    ("Days of Supply", "VAR LastMonth = MAX(dim_date[date_key]) RETURN CALCULATE(AVERAGE(fact_inventory[days_of_supply]), dim_date[date_key] = LastMonth)", "0.0", "当前筛选范围最后一个月、所选SKU的平均库存覆盖天数。"),
    ("Stockout Units", "SUM(fact_inventory[stockout_qty])", "#,##0", "需求超过可供货量形成的缺货数量。"),
    ("Inventory Turnover", "DIVIDE([COGS], AVERAGEX(VALUES(dim_date[date_key]), CALCULATE(SUM(fact_inventory[inventory_value]))))", "0.00x", "销售成本除以月末库存金额平均值。"),
    ("Cash Inflow", "CALCULATE(SUM(fact_cashflow[amount]), fact_cashflow[flow_direction] = \"Inflow\")", "¥#,##0", "现金流入金额。"),
    ("Cash Outflow", "CALCULATE(SUM(fact_cashflow[amount]), fact_cashflow[flow_direction] = \"Outflow\")", "¥#,##0", "现金流出金额，按正数展示。"),
    ("Net Cashflow", "SUM(fact_cashflow[signed_amount])", "¥#,##0;[Red]-¥#,##0", "现金流入减现金流出。"),
    ("Closing Cash", "VAR LastMonth = MAX(dim_date[date_key]) RETURN CALCULATE([Net Cashflow], FILTER(ALL(dim_date), dim_date[date_key] <= LastMonth))", "¥#,##0", "从首月累计至当前筛选末月的现金余额。"),
    ("Sales QoQ", "VAR CurrentQuarter = MAX(dim_date[quarter_seq]) VAR PreviousSales = CALCULATE([Total Sales], FILTER(ALL(dim_date), dim_date[quarter_seq] = CurrentQuarter - 1)) RETURN DIVIDE([Total Sales] - PreviousSales, PreviousSales)", "0.00%", "当前经营季度相对上一经营季度的销售额增速。"),
]


def build_model() -> None:
    write_json(
        MODEL_DIR / ".platform",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "SemanticModel", "displayName": "Smartphone Operations Analytics"},
            "config": {"version": "2.0", "logicalId": stable_uuid("semantic-model")},
        },
    )
    write_json(
        MODEL_DIR / "definition.pbism",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
            "version": "4.2",
            "settings": {"qnaEnabled": False},
        },
    )
    write_text(MODEL_DEFINITION / "database.tmdl", "database\n\tcompatibilityLevel: 1600")
    write_text(
        MODEL_DEFINITION / "expressions.tmdl",
        "expression MySQL_Server = \"127.0.0.1:3306\" meta [IsParameterQuery=true, Type=\"Text\", IsParameterQueryRequired=true]\n\n"
        "expression MySQL_Database = \"nanhu_mobile_analytics\" meta [IsParameterQuery=true, Type=\"Text\", IsParameterQueryRequired=true]",
    )
    model_lines = [
        "model Model",
        "\tculture: zh-CN",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tdiscourageImplicitMeasures",
        "\tsourceQueryCulture: en-US",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
        "annotation __PBI_TimeIntelligenceEnabled = 0",
        "",
    ]
    for table_name in [*TABLES.keys(), "_Measures"]:
        model_lines.append(f"ref table {table_name}")
    write_text(MODEL_DEFINITION / "model.tmdl", "\n".join(model_lines))

    for table_name, columns in TABLES.items():
        lines = [f"/// MySQL import table: {table_name}", f"table {table_name}", ""]
        for spec in columns:
            lines.append(
                column_tmdl(
                    spec["name"],
                    spec["type"],
                    hidden=spec.get("hidden", False),
                    key=spec.get("key", False),
                    fmt=spec.get("fmt"),
                    sort_by=spec.get("sort_by"),
                )
            )
            lines.append("")
        select_list = ", ".join(f"`{spec['name']}`" for spec in columns)
        query = f"SELECT {select_list} FROM `{table_name}`"
        lines.extend(
            [
                f"\tpartition {table_name} = m",
                "\t\tmode: import",
                "\t\tsource =",
                "\t\t\tlet",
                f"\t\t\t\tSource = MySQL.Database(MySQL_Server, MySQL_Database, [Query=\"{query}\"])",
                "\t\t\tin",
                "\t\t\t\tSource",
            ]
        )
        write_text(MODEL_DEFINITION / "tables" / f"{table_name}.tmdl", "\n".join(lines))

    measure_lines = ["/// Central DAX measure table", "table _Measures", ""]
    for name, dax, fmt, description in MEASURES:
        measure_lines.extend(
            [
                f"\t/// {description}",
                f"\tmeasure '{name}' = {dax}",
                f"\t\tformatString: {fmt}",
                "",
            ]
        )
    measure_lines.extend(
        [
            "\tcolumn Dummy",
            "\t\tdataType: string",
            "\t\tisHidden",
            "\t\tsummarizeBy: none",
            "\t\tsourceColumn: Dummy",
            "",
            "\tpartition _Measures = calculated",
            "\t\tmode: import",
            "\t\tsource = ROW(\"Dummy\", BLANK())",
        ]
    )
    write_text(MODEL_DEFINITION / "tables" / "_Measures.tmdl", "\n".join(measure_lines))

    relationships = [
        ("sales_date", "fact_sales_order.order_date_key", "dim_date.date_key"),
        ("sales_product", "fact_sales_order.product_key", "dim_product.product_key"),
        ("sales_channel", "fact_sales_order.channel_key", "dim_channel.channel_key"),
        ("sales_region", "fact_sales_order.region_key", "dim_region.region_key"),
        ("production_date", "fact_production.month_key", "dim_date.date_key"),
        ("production_product", "fact_production.product_key", "dim_product.product_key"),
        ("inventory_date", "fact_inventory.month_key", "dim_date.date_key"),
        ("inventory_product", "fact_inventory.product_key", "dim_product.product_key"),
        ("cashflow_date", "fact_cashflow.date_key", "dim_date.date_key"),
    ]
    rel_lines: list[str] = []
    for label, source, target in relationships:
        rel_lines.extend(
            [
                f"relationship {stable_uuid(label)}",
                f"\tfromColumn: {source}",
                f"\ttoColumn: {target}",
                "",
            ]
        )
    write_text(MODEL_DEFINITION / "relationships.tmdl", "\n".join(rel_lines))

    dax_export = ["-- Smartphone Operations Analytics: DAX measures", ""]
    for name, dax, fmt, description in MEASURES:
        dax_export.extend([f"-- {description}", f"MEASURE '_Measures'[{name}] = {dax}", f"-- Format: {fmt}", ""])
    write_text(POWERBI_DIR / "dax_measures.dax", "\n".join(dax_export))


def page_specs() -> list[dict[str, Any]]:
    filters = [
        ("quarter", "dim_date", "business_quarter", "经营季度", 20, 92, 180),
        ("product", "dim_product", "product_name", "产品 / SKU", 210, 92, 230),
        ("channel", "dim_channel", "channel_name", "销售渠道", 450, 92, 220),
        ("region", "dim_region", "region_name", "销售区域", 680, 92, 220),
    ]
    pages: list[dict[str, Any]] = []

    p1 = {
        "key": "overview",
        "display": "1 经营总览",
        "title": "经营总览 | Smartphone Operations Analytics",
        "subtitle": "销售增长、盈利质量、履约效率、产能负荷与现金安全的联动监控",
        "filters": filters,
        "cards": ["Total Sales", "Gross Margin", "Fill Rate", "On-time Order Rate", "Capacity Utilization", "Closing Cash"],
        "visuals": [
            ("monthly_sales", 20, 288, 400, 402, cartesian_chart("lineChart", "dim_date", "business_quarter", ["Total Sales", "Gross Profit"], "季度销售额与毛利额", "category")),
            ("quarterly_sales", 440, 288, 400, 402, cartesian_chart("clusteredColumnChart", "dim_date", "business_quarter", ["Total Sales"], "经营季度销售额", "category", True)),
            ("closing_cash", 860, 288, 400, 402, cartesian_chart("lineChart", "dim_date", "business_quarter", ["Closing Cash"], "季末现金余额", "category")),
        ],
    }
    pages.append(p1)

    p2 = {
        "key": "mix",
        "display": "2 产品与渠道",
        "title": "产品与渠道 | 结构贡献与盈利质量",
        "subtitle": "按 SKU、渠道和区域拆解销售贡献，并同时观察价格与毛利结构",
        "filters": filters,
        "cards": ["Total Sales", "Gross Profit", "Gross Margin", "Average Selling Price", "Ordered Units", "On-time Order Rate"],
        "visuals": [
            ("product_sales", 20, 288, 400, 175, cartesian_chart("clusteredBarChart", "dim_product", "product_name", ["Total Sales", "Gross Profit"], "SKU 销售额与毛利额", "measure", True)),
            ("channel_sales", 440, 288, 400, 175, cartesian_chart("clusteredBarChart", "dim_channel", "channel_name", ["Total Sales"], "渠道销售贡献", "measure", True)),
            ("region_sales", 860, 288, 400, 175, cartesian_chart("clusteredBarChart", "dim_region", "region_name", ["Total Sales"], "区域销售贡献", "measure", True)),
            (
                "product_detail",
                20,
                473,
                1240,
                217,
                table_visual(
                    [
                        ("column", "dim_product", "sku"),
                        ("column", "dim_product", "product_name"),
                        ("column", "dim_product", "product_family"),
                        ("measure", "_Measures", "Total Sales"),
                        ("measure", "_Measures", "Gross Profit"),
                        ("measure", "_Measures", "Gross Margin"),
                        ("measure", "_Measures", "Average Selling Price"),
                    ],
                    "SKU 经营明细",
                ),
            ),
        ],
    }
    pages.append(p2)

    p3 = {
        "key": "supply_cash",
        "display": "3 供应链与现金",
        "title": "供应链与现金 | 履约、库存、产能与资金用途",
        "subtitle": "验证销售放量是否转化为缺货、交付压力、产能瓶颈或现金时点风险",
        "filters": filters,
        "cards": ["On-time Order Rate", "Capacity Utilization", "Ending Inventory", "Days of Supply", "Stockout Units", "Closing Cash"],
        "visuals": [
            ("service_capacity", 20, 288, 400, 402, cartesian_chart("lineChart", "dim_date", "business_quarter", ["Capacity Utilization", "On-time Order Rate"], "季度产能利用率与按时交付率", "category")),
            ("inventory_product", 440, 288, 400, 402, cartesian_chart("clusteredColumnChart", "dim_product", "product_name", ["Ending Inventory", "Stockout Units"], "期末库存与缺货数量", "measure", True)),
            ("cash_usage", 860, 288, 400, 402, cartesian_chart("clusteredBarChart", "fact_cashflow", "flow_category_cn", ["Cash Outflow"], "现金流出用途", "measure", True)),
        ],
    }
    pages.append(p3)
    return pages


def build_report() -> None:
    theme = {
        "name": THEME_FILE,
        "dataColors": ["#F56600", "#3D3D3D", "#5B8FF9", "#2D7D46", "#D64545", "#FFB27D", "#7A7A7A"],
        "good": "#2D7D46",
        "neutral": "#D9A400",
        "bad": "#D64545",
        "maximum": "#F56600",
        "center": "#FFB27D",
        "minimum": "#FFF2E8",
        "null": "#C8C8C8",
        "firstLevelElements": "#242424",
        "secondLevelElements": "#686868",
        "thirdLevelElements": "#E8E8E8",
        "fourthLevelElements": "#A6A6A6",
        "background": "#FFFFFF",
        "secondaryBackground": "#F5F5F5",
        "tableAccent": "#F56600",
        "textClasses": {
            "callout": {"fontSize": 24, "fontFace": "Segoe UI Semibold", "color": "#F56600"},
            "title": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#242424"},
            "header": {"fontSize": 11, "fontFace": "Segoe UI Semibold", "color": "#242424"},
            "label": {"fontSize": 9, "fontFace": "Segoe UI", "color": "#242424"},
        },
        "visualStyles": {
            "*": {
                "*": {
                    "background": [{"show": True, "color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}],
                    "border": [{"show": True, "color": {"solid": {"color": "#E6E6E6"}}, "radius": 6, "width": 1}],
                    "title": [{"show": True, "fontFamily": "Segoe UI Semibold", "fontSize": 12, "fontColor": {"solid": {"color": "#242424"}}}],
                }
            },
            "tableEx": {
                "*": {
                    "columnHeaders": [{"autoSizeColumnWidth": True, "columnAdjustment": "growToFit"}]
                }
            },
        },
    }
    write_json(POWERBI_DIR / "theme" / THEME_FILE, theme)
    write_json(REPORT_DIR / "StaticResources" / "RegisteredResources" / THEME_FILE, theme)

    write_json(
        REPORT_DIR / ".platform",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "Report", "displayName": "Smartphone Operations Analytics"},
            "config": {"version": "2.0", "logicalId": stable_uuid("report")},
        },
    )
    write_json(
        REPORT_DIR / "definition.pbir",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
            "version": "4.0",
            "datasetReference": {"byPath": {"path": f"../{PROJECT_NAME}.SemanticModel"}},
        },
    )
    write_json(
        REPORT_DEFINITION / "version.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
            "version": "2.0.0",
        },
    )
    write_json(
        REPORT_DEFINITION / "report.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.0.0/schema.json",
            "themeCollection": {
                "customTheme": {
                    "name": THEME_FILE,
                    "reportVersionAtImport": {"visual": "1.8.99", "report": "2.0.99", "page": "1.3.99"},
                    "type": "RegisteredResources",
                }
            },
            "objects": {"outspacePane": [{"properties": {"expanded": literal(False)}}]},
            "resourcePackages": [
                {
                    "name": "RegisteredResources",
                    "type": "RegisteredResources",
                    "items": [{"name": THEME_FILE, "path": THEME_FILE, "type": "CustomTheme"}],
                }
            ],
            "settings": {
                "useStylableVisualContainerHeader": True,
                "allowChangeFilterTypes": True,
                "allowInlineExploration": False,
                "useEnhancedTooltips": True,
                "queryLimitOption": "None",
            },
        },
    )

    page_order: list[str] = []
    for page_index, spec in enumerate(page_specs()):
        page_id = stable_hex(f"page/{spec['key']}")
        page_order.append(page_id)
        page_dir = REPORT_DEFINITION / "pages" / page_id
        write_json(
            page_dir / "page.json",
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json",
                "name": page_id,
                "displayName": spec["display"],
                "displayOption": "FitToPage",
                "height": 720,
                "width": 1280,
                "filterConfig": {"filters": [], "filterSortOrder": "Custom"},
            },
        )

        visual_specs: list[tuple[str, float, float, float, float, dict[str, Any]]] = [
            ("page_title", 20, 8, 1240, 48, textbox(spec["title"], 20, "bold", "#242424")),
            ("page_subtitle", 20, 56, 1240, 34, textbox(spec["subtitle"], 10, "normal", "#686868")),
        ]
        for key, table, column_name, title, x, y, width in spec["filters"]:
            visual_specs.append((f"slicer_{key}", x, y, width, 76, slicer(table, column_name, title)))
        card_y = 178
        card_height = 100 if spec["key"] == "mix" else 110
        visual_specs.append(("kpi_cards", 20, card_y, 1240, card_height, card(spec["cards"])))
        for label, x, y, width, height, visual_payload in spec["visuals"]:
            visual_specs.append((label, x, y, width, height, visual_payload))

        for z, (label, x, y, width, height, visual_payload) in enumerate(visual_specs, start=1):
            visual_id, payload = make_visual(page_id, label, x, y, width, height, z * 1000, visual_payload)
            write_json(page_dir / "visuals" / visual_id / "visual.json", payload)

    write_json(
        REPORT_DEFINITION / "pages" / "pages.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
            "pageOrder": page_order,
            "activePageName": page_order[0],
        },
    )

    write_json(
        POWERBI_DIR / f"{PROJECT_NAME}.pbip",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{PROJECT_NAME}.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )


def main() -> None:
    for generated in [REPORT_DIR, MODEL_DIR]:
        if generated.exists():
            shutil.rmtree(generated)
    build_model()
    build_report()
    print(f"Built PBIP: {POWERBI_DIR / f'{PROJECT_NAME}.pbip'}")


if __name__ == "__main__":
    main()
