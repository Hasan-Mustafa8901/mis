from nicegui import ui


def render_line_chart(
    series_data: list[tuple[str, list[float]]],
    categories: list[str],
    colors: list[str] | None = None,
    height: int = 240,
) -> None:
    """Smooth multi-series line chart via ui.echart()."""
    default_colors = ["#6366F1", "#EF4444", "#10B981", "#F59E0B"]
    used_colors = colors or default_colors

    series = [
        {
            "name": name,
            "type": "line",
            "smooth": True,
            "data": [round(v) for v in vals],
            "itemStyle": {"color": used_colors[i % len(used_colors)]},
            "lineStyle": {"width": 2, "color": used_colors[i % len(used_colors)]},
            "areaStyle": {"opacity": 0.06, "color": used_colors[i % len(used_colors)]},
            "symbolSize": 6,
        }
        for i, (name, vals) in enumerate(series_data)
    ]

    ui.echart(
        {
            "backgroundColor": "transparent",
            "animation": True,
            "legend": {
                "show": True,
                "top": 0,
                "left": "left",
                "textStyle": {"fontSize": 11, "color": "#6B7280"},
            },
            "grid": {
                "left": 60,
                "right": 16,
                "top": 36,
                "bottom": 36,
                "containLabel": False,
            },
            "xAxis": {
                "type": "category",
                "data": categories,
                "axisLine": {"lineStyle": {"color": "#E5E7EB"}},
                "axisLabel": {"color": "#9CA3AF", "fontSize": 10},
                "boundaryGap": False,
            },
            "yAxis": {
                "type": "value",
                "splitLine": {"lineStyle": {"type": "dashed", "color": "#F3F4F6"}},
                "axisLabel": {"color": "#9CA3AF", "fontSize": 10},
            },
            "tooltip": {
                "trigger": "axis",
                "backgroundColor": "rgba(15, 22, 35, 0.9)",
                "borderColor": "#1F2937",
                "textStyle": {"color": "#FFF", "fontSize": 12},
                "axisPointer": {"lineStyle": {"color": "#6366F1", "width": 1}},
            },
            "series": series,
        }
    ).style(f"height: {height}px; width: 100%")


def render_bar_chart(
    items: list[tuple[str, float]],
    color: str = "#6366F1",
    value_fmt: str = "K",  # "K"→₹XK  "N"→count  "raw"→₹X,000
    height: int = 240,
    empty_msg: str = "No data yet",
) -> None:
    """Horizontal bar chart via ui.echart()."""
    if not items:
        ui.label(empty_msg).style(
            "color:#9CA3AF;font-size:12px;padding:20px 0;display:block;text-align:center"
        )
        return

    # ECharts horizontal bar: categories on yAxis, values on xAxis
    categories = [lbl for lbl, _ in items]
    values = [round(val) for _, val in items]

    axis_fmt = "{value}"
    if value_fmt == "K":

        def label_fmt(v):
            return f"₹{v / 1000:.1f}K"

        tt_fmt = "{b}: ₹{c}"  # ECharts template — {b}=category {c}=value
    elif value_fmt == "raw":

        def label_fmt(v):
            return f"₹{v:,.0f}"

        tt_fmt = "{b}: ₹{c}"
    else:  # N — plain count

        def label_fmt(v):
            return str(int(v))

        tt_fmt = "{b}: {c}"

    # Pre-compute label strings in Python — no JS formatter needed
    labels = [label_fmt(v) for v in values]

    ui.echart(
        {
            "backgroundColor": "transparent",
            "animation": True,
            "grid": {
                "left": 120,
                "right": 48,
                "top": 8,
                "bottom": 8,
                "containLabel": False,
            },
            "xAxis": {
                "type": "value",
                "axisLabel": {
                    "fontSize": 10,
                    "color": "#9CA3AF",
                    "formatter": axis_fmt,
                },
                "splitLine": {"lineStyle": {"color": "#F3F4F6", "type": "dashed"}},
                "axisLine": {"show": False},
                "axisTick": {"show": False},
            },
            "yAxis": {
                "type": "category",
                "data": categories,
                "axisLabel": {"fontSize": 11, "color": "#374151"},
                "axisLine": {"lineStyle": {"color": "#E5E7EB"}},
                "axisTick": {"show": False},
                "inverse": False,
            },
            "tooltip": {
                "trigger": "item",
                "backgroundColor": "#1F2937",
                "borderColor": "#1F2937",
                "textStyle": {"color": "#F9FAFB", "fontSize": 12},
                "formatter": tt_fmt,
            },
            "series": [
                {
                    "type": "bar",
                    "data": [
                        {
                            "value": v,
                            "label": {
                                "show": True,
                                "position": "right",
                                "formatter": lbl,
                                "fontSize": 10,
                                "color": "#6B7280",
                            },
                            "itemStyle": {"color": color, "borderRadius": [0, 3, 3, 0]},
                        }
                        for v, lbl in zip(values, labels)
                    ],
                    "barMaxWidth": 28,
                }
            ],
        }
    ).style(f"height:{height}px;width:100%")
