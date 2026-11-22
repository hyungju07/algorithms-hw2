"""외부 라이브러리 없이 꺾은선 그래프를 SVG로 그린다."""
import math
from xml.sax.saxutils import escape

WIDTH, HEIGHT = 760, 480
LEFT, RIGHT, TOP, BOTTOM = 70, 250, 50, 60   # 오른쪽 여백에 범례를 둔다


def ticks(lo, hi, about=6):
    """lo~hi를 about개쯤으로 나누는 보기 좋은 눈금 (1, 2, 5의 배수)."""
    raw = (hi - lo) / about
    power = 10 ** math.floor(math.log10(raw))
    step = min((s * power for s in (1, 2, 5, 10)), key=lambda s: abs(s - raw))
    values, v = [], math.ceil(lo / step) * step
    while v <= hi + step * 1e-9:
        values.append(round(v, 10))
        v += step
    return values


def log_ticks(lo, hi):
    values, power = [], 10 ** math.floor(math.log10(lo))
    while power <= hi:
        values.extend(v for v in (power, 2 * power, 5 * power) if lo <= v <= hi)
        power *= 10
    return values


def line_chart(path, title, x_label, y_label, series, x_range, y_range, log_y=False, note=""):
    """series: (이름, 색, 종류, 점들)의 목록.

    종류는 "line"(실선), "dash"(점선), "dot"(채운 점), "ring"(빈 점). 점들은 (x, y)의 목록.
    """
    x0, x1 = x_range
    y0, y1 = y_range
    plot_w, plot_h = WIDTH - LEFT - RIGHT, HEIGHT - TOP - BOTTOM
    fy = math.log10 if log_y else (lambda v: v)

    def px(x):
        return LEFT + (x - x0) / (x1 - x0) * plot_w

    def py(y):
        return TOP + plot_h - (fy(y) - fy(y0)) / (fy(y1) - fy(y0)) * plot_h

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'width="{WIDTH}" height="{HEIGHT}" font-family="sans-serif" font-size="13">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="white"/>',
        f'<text x="{LEFT}" y="28" font-size="16" font-weight="bold">{escape(title)}</text>',
    ]
    for x in ticks(x0, x1):
        out.append(f'<line x1="{px(x):.1f}" y1="{TOP}" x2="{px(x):.1f}" y2="{TOP + plot_h}" stroke="#e5e7eb"/>')
        out.append(f'<text x="{px(x):.1f}" y="{TOP + plot_h + 20}" text-anchor="middle">{x:g}</text>')
    for y in (log_ticks(y0, y1) if log_y else ticks(y0, y1)):
        out.append(f'<line x1="{LEFT}" y1="{py(y):.1f}" x2="{LEFT + plot_w}" y2="{py(y):.1f}" stroke="#e5e7eb"/>')
        out.append(f'<text x="{LEFT - 8}" y="{py(y) + 4:.1f}" text-anchor="end">{y:g}</text>')
    out.append(f'<rect x="{LEFT}" y="{TOP}" width="{plot_w}" height="{plot_h}" fill="none" stroke="#111827"/>')
    out.append(f'<text x="{LEFT + plot_w / 2}" y="{HEIGHT - 15}" text-anchor="middle">{escape(x_label)}</text>')
    out.append(f'<text transform="translate(18 {TOP + plot_h / 2}) rotate(-90)" text-anchor="middle">{escape(y_label)}</text>')

    legend_x, legend_y = LEFT + plot_w + 20, TOP + 10
    for name, color, kind, points in series:
        shown = [(x, y) for x, y in points if x0 <= x <= x1 and y0 <= y <= y1]
        if kind in ("line", "dash"):
            dash = ' stroke-dasharray="7 5"' if kind == "dash" else ""
            coords = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in shown)
            out.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2"{dash}/>')
            out.append(f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x + 30}" y2="{legend_y}" '
                       f'stroke="{color}" stroke-width="2"{dash}/>')
        else:
            fill = color if kind == "dot" else "white"
            for x, y in shown:
                out.append(f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="4" fill="{fill}" stroke="{color}" stroke-width="1.5"/>')
            out.append(f'<circle cx="{legend_x + 15}" cy="{legend_y}" r="4" fill="{fill}" stroke="{color}" stroke-width="1.5"/>')
        out.append(f'<text x="{legend_x + 38}" y="{legend_y + 4}">{escape(name)}</text>')
        legend_y += 22
    if note:
        for i, line in enumerate(note.split("\n")):
            out.append(f'<text x="{legend_x}" y="{legend_y + 14 + i * 16}" font-size="11" fill="#4b5563">{escape(line)}</text>')
    out.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
