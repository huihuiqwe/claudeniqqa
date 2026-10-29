"""Графическая часть: календарный план, график движения рабочих, схема
стройгенплана, схема к подбору крана, транспортная схема."""
from __future__ import annotations

import datetime as dt
import math
import os
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Polygon, Rectangle  # noqa: E402

from . import calc  # noqa: E402

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8,
    "axes.linewidth": 0.6,
    "savefig.dpi": 220,
})

GROUP_COLORS = {
    "prep": "#8c8c8c",
    "under": "#8c564b",
    "above": "#1f77b4",
    "spec": "#2ca02c",
    "finish": "#ff7f0e",
    "ext": "#9467bd",
}
MONTHS_RU = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]


def ru(x: float, nd: int = 0) -> str:
    """Число в русской записи: пробел между разрядами, десятичная запятая."""
    s = f"{x:,.{nd}f}"
    return s.replace(",", " ").replace(".", ",")


def _month_starts(a: dt.date, b: dt.date) -> list[dt.date]:
    out = []
    d = dt.date(a.year, a.month, 1)
    while d <= b:
        out.append(d)
        d = dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return out


def _forward_fill_workdays(dates, daily):
    """Для наглядности графика значения выходных дней берутся по предыдущему рабочему дню."""
    out = np.array(daily, dtype=float)
    last = 0.0
    for i, d in enumerate(dates):
        if np.is_busday(np.datetime64(d), holidays=calc._HOL):
            last = out[i]
        else:
            out[i] = last
    return out


def calendar_plan(r: calc.Results, path: str) -> None:
    works = r.works
    start, end = calc.START, r.end
    n = len(works)
    fig = plt.figure(figsize=(11.0, 7.8))
    top, bottom_gantt = 0.96, 0.36
    ax_t = fig.add_axes([0.01, bottom_gantt, 0.42, top - bottom_gantt])
    ax_g = fig.add_axes([0.43, bottom_gantt, 0.56, top - bottom_gantt])
    ax_l = fig.add_axes([0.43, 0.06, 0.56, 0.24], sharex=ax_g)
    ax_lt = fig.add_axes([0.01, 0.06, 0.40, 0.24])
    y_head = -0.9

    # --- таблица слева
    ax_t.set_xlim(0, 1)
    ax_t.set_ylim(n + 0.2, -1.8)
    ax_t.axis("off")
    cols = [(0.0, "№"), (0.05, "Наименование работ"), (0.765, "Трудо-\nёмкость,\nчел.-дн."),
            (0.865, "Рабочих\nв день,\nчел."), (0.94, "Раб.\nдн.")]
    for x, h in cols:
        ax_t.text(x + 0.004, y_head, h, va="center", ha="left", fontsize=5.8, weight="bold")
    ax_t.axhline(0.0, color="k", lw=0.6)
    for i, w in enumerate(works):
        y = i + 0.5
        ax_t.text(0.005, y, w.code, va="center", fontsize=6.0)
        ax_t.text(0.05, y, textwrap.fill(w.name, 70), va="center", fontsize=5.0, linespacing=1.0)
        ax_t.text(0.765, y, ru(w.labor), va="center", fontsize=6.0)
        ax_t.text(0.865, y, ru(w.workers), va="center", fontsize=6.0)
        ax_t.text(0.945, y, f"{w.days}", va="center", fontsize=6.0)
        ax_t.axhline(i + 1, color="#cccccc", lw=0.3)

    # --- линейный график
    ax_g.set_ylim(n + 0.2, -1.8)
    ax_g.set_xlim(mdates.date2num(start), mdates.date2num(end + dt.timedelta(days=1)))
    ax_g.set_yticks([])
    ms = _month_starts(start, end)
    for m in ms:
        ax_g.axvline(mdates.date2num(m), color="#999999", lw=0.5)
    for m in ms:
        nxt = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
        mid = mdates.date2num(m) + (mdates.date2num(min(nxt, end + dt.timedelta(days=1))) - mdates.date2num(m)) / 2
        ax_g.text(mid, y_head, f"{MONTHS_RU[m.month - 1]}\n{m.year}", ha="center", va="center",
                  fontsize=6.5, weight="bold")
    ax_g.axhline(0.0, color="k", lw=0.6)
    for i, w in enumerate(works):
        x0 = mdates.date2num(w.start)
        x1 = mdates.date2num(w.end + dt.timedelta(days=1))
        ax_g.add_patch(Rectangle((x0, i + 0.22), x1 - x0, 0.56, color=GROUP_COLORS[w.group], lw=0))
        ax_g.text(x1 + 1.5, i + 0.5, ru(w.workers), va="center", fontsize=5.6, color="#333333")
        ax_g.axhline(i + 1, color="#eeeeee", lw=0.3)
    ax_g.tick_params(axis="x", labelbottom=False, length=0)
    handles = [Rectangle((0, 0), 1, 1, color=c) for c in GROUP_COLORS.values()]
    ax_g.legend(handles, list(calc.GROUPS.values()), loc="lower left", fontsize=5.8, ncol=3,
                frameon=True, framealpha=0.95, bbox_to_anchor=(0.0, 0.0))

    # --- график движения рабочих
    lg = r.lg
    xs = [mdates.date2num(d) for d in lg.dates] + [mdates.date2num(end + dt.timedelta(days=1))]
    ys = list(_forward_fill_workdays(lg.dates, lg.daily))
    ys = ys + [ys[-1]]
    ax_l.fill_between(xs, ys, step="post", color="#4c72b0", alpha=0.35, lw=0)
    ax_l.step(xs, ys, where="post", color="#4c72b0", lw=0.8)
    ax_l.axhline(lg.n_max, color="#c44e52", lw=0.7, ls="--")
    ax_l.axhline(lg.n_avg, color="#55a868", lw=0.7, ls="--")
    ax_l.text(xs[2], lg.n_max + 3, f"Nmax = {ru(lg.n_max)} чел.", color="#c44e52", fontsize=6.5)
    ax_l.text(xs[2], lg.n_avg + 3, f"Nср = {ru(lg.n_avg)} чел.", color="#55a868", fontsize=6.5)
    for m in ms:
        ax_l.axvline(mdates.date2num(m), color="#999999", lw=0.5)
    ax_l.set_ylim(0, lg.n_max * 1.2)
    ax_l.set_ylabel("Рабочих в день, чел.", fontsize=7)
    ax_l.xaxis.set_major_locator(mdates.MonthLocator(bymonthday=15))
    ax_l.xaxis.set_major_formatter(plt.FuncFormatter(
        lambda v, _: f"{MONTHS_RU[mdates.num2date(v).month - 1]}"))
    ax_l.tick_params(labelsize=6.5, length=0)
    ax_l.grid(axis="y", lw=0.3, color="#dddddd")

    ax_lt.axis("off")
    lines = [
        "График движения рабочих кадров",
        "",
        f"Общая трудоёмкость: {ru(lg.total)} чел.-дн.",
        f"Рабочих дней (пятидневная неделя): {lg.workdays}",
        f"Максимальное число рабочих Nmax = {ru(lg.n_max)} чел.",
        f"Среднее число рабочих Nср = {ru(lg.total)} / {lg.workdays} = {ru(lg.n_avg)} чел.",
        f"Коэффициент неравномерности α = Nmax / Nср = {ru(lg.alpha, 2)} ≤ 1,5",
        "",
        f"Начало строительства — {calc.START:%d.%m.%Y}, окончание — {r.end:%d.%m.%Y}",
        "Цифры справа от полос — число рабочих в день",
    ]
    ax_lt.text(0.0, 0.98, "\n".join(lines), va="top", fontsize=7, linespacing=1.35)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def _stadium(ax, x0, x1, y, R, **kw):
    t1 = np.linspace(math.pi / 2, 3 * math.pi / 2, 60)
    t2 = np.linspace(-math.pi / 2, math.pi / 2, 60)
    xs = list(x0 + R * np.cos(t1)) + list(x1 + R * np.cos(t2))
    ys = list(y + R * np.sin(t1)) + list(y + R * np.sin(t2))
    ax.plot(xs + xs[:1], ys + ys[:1], **kw)


def site_plan(r: calc.Results, path: str) -> None:
    s, cr = r.site, r.crane
    fig, ax = plt.subplots(figsize=(11.0, 7.4))
    W, H = s["W"], s["H"]
    y_c = s["y_crane"]
    g = calc.CRANE["gauge"] / 2

    # улица, тротуар, существующая застройка и утилидор
    ax.add_patch(Rectangle((-15, -16), W + 32, 10, color="#e8e8e8", lw=0))
    ax.text(W / 2, -11, "Городская улица (существующая)", ha="center", va="center", fontsize=8)
    ax.add_patch(Rectangle((-15, -6), W + 32, 3.5, color="#f4f4f4", lw=0))
    ax.text(110, -4.3, "тротуар; над пешеходной зоной у ворот — защитный козырёк", ha="center",
            va="center", fontsize=6)
    ax.add_patch(Rectangle((60, 92), 100, 12, fc="#d9d9d9", ec="k", lw=0.6))
    ax.text(110, 98, "Существующий 5-этажный жилой дом", ha="center", va="center", fontsize=7.5)
    ax.add_patch(Rectangle((-11, -6), 4, 112, fc="#fde0dd", ec="#c51b8a", lw=0.6))
    ax.text(-13.0, 30, "Существующий утилидор (теплосеть, водопровод, канализация)", rotation=90,
            ha="center", va="center", fontsize=6.3, color="#7a0177")

    # ограждение
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, ec="k", lw=1.4, ls=(0, (6, 2))))
    ax.text(W / 2, H + 1.8, f"Временное ограждение площадки h = 2,0 м, L = {ru(s['fence'])} м; "
            f"площадь площадки {ru(s['area'] / 10000, 2)} га", ha="center", fontsize=7)

    # здание и захватки
    for i, (x, y, L, B) in enumerate(s["sections"]):
        ax.add_patch(Rectangle((x, y), L, B, fc="#f6d8ae", ec="k", lw=1.0))
        ax.text(x + L / 2, y + B / 2, f"Секция {i + 1}", ha="center", va="center", fontsize=7.5, weight="bold")
    xs0 = s["sections"][0][0]
    xs2 = s["sections"][2][0]
    xe = xs0 + calc.BLD["length"]
    yb = s["y_south"] + calc.TP["width_axes"]
    for a, b, t in ((xs0, xs2, "Захватка I (секции 1–2)"), (xs2, xe, "Захватка II (секции 3–4)")):
        ax.annotate("", (a, yb + 3.0), (b, yb + 3.0), arrowprops=dict(arrowstyle="<->", lw=0.6))
        ax.text((a + b) / 2, yb + 4.0, t, ha="center", fontsize=6.5)
    ax.add_patch(Rectangle((xs0 - cr["X_bld"], s["y_south"] - cr["X_bld"]),
                           calc.BLD["length"] + 2 * cr["X_bld"], calc.TP["width_axes"] + 2 * cr["X_bld"],
                           fill=False, ec="#d62728", lw=0.8, ls=":"))

    # подкрановый путь и кран
    for yy in (y_c - g, y_c + g):
        ax.plot(s["track"], [yy, yy], color="k", lw=1.6)
    for xt in s["track"]:
        ax.plot([xt, xt], [y_c - g - 0.8, y_c + g + 0.8], color="k", lw=2.2)
    ax.text(s["track"][1] + 1.0, y_c, f"Подкрановый\nпуть {ru(cr['l_track'], 1)} м\n({cr['links']} звеньев)",
            fontsize=5.8, ha="left", va="center")
    x_work = s["x_mid"] - 20
    for xc, ls in ((s["cr_x"][0], ":"), (x_work, "-"), (s["cr_x"][1], ":")):
        ax.add_patch(Rectangle((xc - 3, y_c - 3), 6, 6, fill=ls == "-", fc="#ffd92f", ec="k", lw=0.8, ls=ls))
    ax.text(x_work + 3.8, y_c, calc.CRANE["model"], ha="left", va="center", fontsize=6.5, weight="bold")
    ax.text(s["track"][0] - 0.8, y_c + 1.8, "крайние стоянки\nкрана — пунктир", ha="right", va="bottom",
            fontsize=5.0)
    _stadium(ax, s["cr_x"][0], s["cr_x"][1], y_c, cr["R_work"], color="#1f77b4", lw=0.9, ls="--")
    _stadium(ax, s["cr_x"][0], s["cr_x"][1], y_c, cr["R_danger"], color="#d62728", lw=1.0, ls="-.")
    ax.text(s["x_mid"] + 30, y_c + cr["R_danger"] + 0.8,
            f"Граница опасной зоны крана R = {ru(cr['R_danger'], 1)} м", color="#d62728", fontsize=6.8,
            ha="center")
    ax.text(s["cr_x"][1] + cr["R_work"] + 0.8, y_c + 6, f"Рабочая зона крана R = {ru(cr['R_work'])} м",
            color="#1f77b4", fontsize=6.0, ha="left", va="bottom", rotation=90)

    # открытые склады
    st = r.store["rows"]
    y0, y1 = s["store"]
    labels = ["Наружные\nпанели", "Внутренние\nпанели", "Плиты\nперекрытий", "Прочие\nэлементы"]
    x = 58.0
    for lab, srow in zip(labels, st[:4]):
        L = srow[10] / (y1 - y0)
        ax.add_patch(Rectangle((x, y0), L, y1 - y0, fc="#c7e9c0", ec="#238b45", lw=0.7, hatch="////"))
        ax.text(x + L / 2, (y0 + y1) / 2, f"{lab}\n{ru(srow[10])} м²", ha="center", va="center",
                fontsize=6, bbox=dict(boxstyle="square,pad=0.15", fc="white", ec="none", alpha=0.85))
        x += L + 1.0

    # временная дорога (одностороннее кольцо)
    ry = s["road_y"]
    ax.add_patch(Rectangle((30 - 1.75, -2.5), 3.5, ry + 2.5, fc="#bdbdbd", lw=0))
    ax.add_patch(Rectangle((185 - 1.75, -2.5), 3.5, ry + 2.5, fc="#bdbdbd", lw=0))
    ax.add_patch(Rectangle((30 - 1.75, ry - 1.75), 155 + 3.5, 3.5, fc="#bdbdbd", lw=0))
    ax.add_patch(Rectangle((50, ry - 1.75), 120, 6.0, fc="#bdbdbd", lw=0))
    for (xa, ya), (xb, yb2) in (((40, ry), (52, ry)), ((30, 6), (30, 14)), ((185, 14), (185, 6)),
                                ((172, ry), (180, ry))):
        ax.annotate("", (xb, yb2), (xa, ya), arrowprops=dict(arrowstyle="->", lw=0.9))
    ax.text(110, ry - 3.6, "Временная дорога из ж/б плит, одностороннее движение, b = 3,5 м "
            "(в зоне разгрузки — 6,0 м)", ha="center", fontsize=6.2)
    ax.text(30, -1.2, "Въезд", ha="center", fontsize=6.5, weight="bold",
            bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none"))
    ax.text(185, -1.2, "Выезд", ha="center", fontsize=6.5, weight="bold",
            bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none"))
    ax.add_patch(Rectangle((33, 1.0), 3.0, 2.4, fc="#ffffff", ec="k", lw=0.7))
    ax.text(36.8, 2.2, "КПП", fontsize=6, va="center")
    ax.add_patch(Rectangle((185 - 1.75, 3.0), 3.5, 6.0, fc="#d0e1f9", ec="k", lw=0.6, hatch="xx"))
    ax.text(188.5, 6.0, "Пункт\nочистки\nколёс", fontsize=5.5, va="center")

    # зона вне опасной зоны: бытовой городок, склады, КТП
    n_fp = math.ceil(r.tb["n_cont"] / 2)
    per_col = math.ceil(n_fp / 2)
    for col, x0 in enumerate((3.0, 12.0)):
        for k in range(per_col):
            if col * per_col + k >= n_fp:
                break
            ax.add_patch(Rectangle((x0, 26 + k * 2.4), 6.0, 2.4, fc="#fff2cc", ec="#7f6000", lw=0.5))
    ax.plot([9.0, 12.0], [26 + per_col * 1.2] * 2, color="#7f6000", lw=2.0)
    ax.text(10.5, 22.6, f"Бытовой городок: {r.tb['n_cont']} блок-\nконтейнеров в 2 яруса",
            ha="center", va="center", fontsize=5.4)
    ax.add_patch(Rectangle((3, 3), 10, 7, fc="#e5f5e0", ec="k", lw=0.6))
    ax.text(8, 6.5, f"Закрытый\nсклад\n{ru(r.store['sums']['закрытый'])} м²", ha="center", va="center", fontsize=5.4)
    ax.add_patch(Rectangle((14, 3), 9, 7, fc="#f0f0f0", ec="k", lw=0.6, hatch=".."))
    ax.text(18.5, 6.5, f"Навес\n{ru(r.store['sums']['навес'])} м²", ha="center", va="center", fontsize=5.4,
            bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none", alpha=0.8))
    ax.add_patch(Rectangle((3, 14), 4, 4, fc="#fdae6b", ec="k", lw=0.7))
    ax.text(7.6, 16, "КТПН-400", fontsize=5.8, va="center")
    ax.add_patch(Rectangle((4, 76), 9, 4, fc="#ffffff", ec="k", lw=0.6))
    ax.text(8.5, 78, "отходы", fontsize=5.4, va="center", ha="center")

    # временные сети
    ax.plot([-7, 10.5, 10.5], [70, 70, 26 + per_col * 2.4], color="#2171b5", lw=1.0, ls="--")
    ax.plot([10.5, 50, 55], [70, 70, 54], color="#2171b5", lw=1.0, ls="--")
    ax.text(-6.5, 71.0, "В1 — врем. водопровод DN50 (теплоизоляция, греющий кабель)", fontsize=5.5, color="#2171b5")
    ax.plot([-7, 52, 52, 55], [64, 64, 50, 50], color="#e31a1c", lw=1.0, ls="--")
    ax.text(-6.5, 65.0, "Т — врем. теплоснабжение здания от утилидора", fontsize=5.5, color="#e31a1c")
    ax.plot([7, 22.5, 22.5, s["track"][0]], [18, 18, y_c - g, y_c - g], color="#ff7f00", lw=1.0, ls="-.")
    ax.text(24.4, 27.0, "W — кабель 0,4 кВ к крану", fontsize=5.5, color="#ff7f00", rotation=90,
            va="center", ha="center")

    # освещение, гидранты, пожарные щиты
    for px, py in ((1.5, 1.5), (100, 1.5), (198.5, 1.5), (1.5, 83.5), (100, 83.5), (198.5, 83.5),
                   (198.5, 42), (1.5, 56)):
        ax.plot(px, py, marker="*", color="#e6550d", ms=7)
    for hx in (40, 160):
        ax.plot(hx, -8.5, marker="o", color="#3182bd", ms=6)
        ax.text(hx + 2, -8.8, "ПГ (сущ.)", fontsize=5.8, va="center")
    for fx, fy in ((25, 44), (172, 30), (25, 76)):
        ax.add_patch(Rectangle((fx, fy), 2.0, 2.0, fc="#de2d26", ec="k", lw=0.5))

    # север и роза ветров (схематично)
    ax.annotate("С", xy=(W + 17, H + 8), xytext=(W + 17, H - 6), ha="center",
                arrowprops=dict(arrowstyle="-|>", lw=1.0), fontsize=9, weight="bold")
    rose = [(0, 0.45), (45, 0.4), (90, 0.75), (135, 1.0), (180, 0.9), (225, 0.45), (270, 0.5), (315, 0.4)]
    cx, cy, sc = W + 17, 34, 9
    pts = []
    for a, v in rose:
        px, py = cx + sc * v * math.sin(math.radians(a)), cy + sc * v * math.cos(math.radians(a))
        ax.plot([cx, cx + sc * math.sin(math.radians(a))], [cy, cy + sc * math.cos(math.radians(a))],
                color="#bbbbbb", lw=0.5)
        pts.append((px, py))
    ax.add_patch(Polygon(pts, closed=True, fc="#c6dbef", ec="#08519c", lw=0.9))
    for t, a in (("С", 0), ("В", 90), ("Ю", 180), ("З", 270)):
        ax.text(cx + (sc + 2.2) * math.sin(math.radians(a)), cy + (sc + 2.2) * math.cos(math.radians(a)), t,
                ha="center", va="center", fontsize=6)
    ax.text(cx, cy - sc - 4.0, "Роза ветров\n(дек.–фев.,\nсхематично)", ha="center", va="top", fontsize=5.6)

    leg = [
        (Rectangle((0, 0), 1, 1, fc="#f6d8ae", ec="k"), "Строящийся жилой дом"),
        (Rectangle((0, 0), 1, 1, fc="#c7e9c0", ec="#238b45", hatch="////"), "Открытые склады"),
        (Rectangle((0, 0), 1, 1, fc="#bdbdbd"), "Временная дорога"),
        (Rectangle((0, 0), 1, 1, fc="#fff2cc", ec="#7f6000"), "Инвентарные здания"),
        (Line2D([], [], color="#d62728", ls="-.", lw=1.0), "Опасная зона крана"),
        (Line2D([], [], color="#1f77b4", ls="--", lw=0.9), "Рабочая зона крана"),
        (Line2D([], [], color="#d62728", ls=":", lw=0.8), f"Опасная зона у здания ({ru(cr['X_bld'])} м)"),
        (Line2D([], [], color="k", ls=(0, (6, 2)), lw=1.2), "Временное ограждение"),
        (Line2D([], [], marker="*", color="#e6550d", ls="", ms=7), "Прожекторная мачта"),
        (Line2D([], [], marker="o", color="#3182bd", ls="", ms=6), "Пожарный гидрант"),
        (Rectangle((0, 0), 1, 1, fc="#de2d26", ec="k"), "Пожарный щит"),
        (Line2D([], [], color="#2171b5", ls="--", lw=1.0), "Временный водопровод"),
    ]
    ax.legend([h for h, _ in leg], [t for _, t in leg], loc="upper center", bbox_to_anchor=(0.5, -0.0),
              ncol=4, fontsize=6.5, frameon=False)
    ax.set_xlim(-16, W + 30)
    ax.set_ylim(-17, 106)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.text(W + 29, -16.5, "Размеры — в метрах; схема", ha="right", fontsize=6)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def crane_scheme(r: calc.Results, path: str) -> None:
    cr = r.crane
    fig, ax = plt.subplots(figsize=(7.2, 5.8))
    g = calc.CRANE["gauge"] / 2
    ax.plot([-12, 26], [0, 0], color="k", lw=1.0)
    xf = cr["to_facade"]
    B = cr["c_far"]
    h_roof = calc.BLD["height_roof"]
    h_mr = calc.BLD["height_mr"]
    ax.add_patch(Rectangle((xf, 0), B, h_roof, fc="#f6d8ae", ec="k", lw=0.8))
    ax.add_patch(Rectangle((xf + 3.0, h_roof), 4.0, h_mr - h_roof, fc="#f6d8ae", ec="k", lw=0.8))
    ax.add_patch(Rectangle((xf - cr["b_proj"], 1.1), cr["b_proj"], h_roof - 2.0, fc="#fbe7c6", ec="k", lw=0.5))
    for k in range(1, 10):
        ax.plot([xf, xf + B], [1.1 + 3 * k, 1.1 + 3 * k], color="#a0a0a0", lw=0.4)
    H_tower = cr["H"] + 3.5
    ax.add_patch(Rectangle((-g, 0), 2 * g, 1.2, fc="#ffd92f", ec="k", lw=0.8))
    ax.add_patch(Rectangle((-0.8, 1.2), 1.6, H_tower - 1.2, fc="#ffe680", ec="k", lw=0.8))
    ax.plot([-6, calc.CRANE["R_max"]], [H_tower, H_tower], color="k", lw=1.4)
    ax.add_patch(Rectangle((-calc.CRANE["r_tail"], 1.2), calc.CRANE["r_tail"] - 0.8, 2.0, fc="#bdbdbd",
                           ec="k", lw=0.6))
    x_hook, y_hook = cr["L"], cr["H"]
    ax.plot([x_hook, x_hook], [H_tower, y_hook], color="k", lw=0.6)
    ax.plot(x_hook, y_hook, marker="v", color="k", ms=5)
    el_top = y_hook - cr["h_sl"]
    ax.plot([x_hook, x_hook - 1.4], [y_hook, el_top], color="#555555", lw=0.5)
    ax.plot([x_hook, x_hook + 1.4], [y_hook, el_top], color="#555555", lw=0.5)
    ax.add_patch(Rectangle((x_hook - 1.6, el_top - cr["h_el"]), 3.2, cr["h_el"], fc="#4c72b0"))

    def dim_v(x, y0, y1, text):
        ax.annotate("", (x, y0), (x, y1), arrowprops=dict(arrowstyle="<->", lw=0.6))
        ax.text(x + 0.4, (y0 + y1) / 2, text, fontsize=6.8, va="center", ha="left", rotation=90)

    def dim_h(y, x0, x1, text):
        ax.annotate("", (x0, y), (x1, y), arrowprops=dict(arrowstyle="<->", lw=0.6))
        ax.text((x0 + x1) / 2, y + 0.5, text, fontsize=6.6, ha="center")

    dim_v(24.2, 0, cr["H"], f"Hтр = {ru(cr['H'], 2)} м")
    dim_v(20.8, 0, cr["h0"], f"h0 = {ru(cr['h0'], 2)} м")
    dim_h(-2.6, 0, cr["L"], f"Lтр = {ru(cr['L'], 1)} м")
    dim_h(-5.4, 0, xf, f"{ru(cr['b_clear'], 1)} + {ru(cr['b_proj'], 1)}")
    dim_h(-5.4, xf, xf + B, f"{ru(B, 1)}")
    dim_h(H_tower + 1.6, 0, calc.CRANE["R_max"],
          f"Rmax = {ru(calc.CRANE['R_max'])} м (рабочий вылет ограничен {ru(cr['R_work'])} м)")
    ax.text(0, -1.3, "колея 6,0 м", fontsize=6.0, ha="center", va="top")
    ax.text(xf + B / 2, h_roof / 2, "Жилой дом\n9 этажей", ha="center", va="center", fontsize=7.5)
    ax.text(6.3, H_tower - 1.6, f"{calc.CRANE['model']}\nQ = {ru(calc.CRANE['Q_max'])} т при R ≤ {ru(calc.CRANE['R_Qmax'])} м\n"
            f"Q = {ru(calc.CRANE['Q_Rmax'], 1)} т при R = {ru(calc.CRANE['R_max'])} м\n"
            f"Hmax = {ru(calc.CRANE['H_Rmax'])} м на Rmax",
            fontsize=6.0, va="top", bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#999999", lw=0.5))
    ax.text(x_hook + 1.9, el_top - 0.6, f"элемент\n{ru(calc.TP['max_element'], 2)} т", fontsize=5.6, va="center")
    ax.set_xlim(-12, 27.5)
    ax.set_ylim(-7.5, H_tower + 4.5)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def transport_scheme(path: str) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    nodes = {
        "msk": (1.2, 4.0, "Мурманск / Архангельск\n(морские порты)"),
        "kras": (5.2, 0.5, "Красноярск\n(речной порт)"),
        "dud": (5.2, 4.0, "Порт Дудинка\n(р. Енисей)"),
        "air": (7.6, 5.6, "Аэропорт Алыкель"),
        "nor": (9.2, 4.0, "Норильск:\nбазы генподрядчика"),
        "site": (12.6, 2.4, "СТРОЙПЛОЩАДКА"),
        "zhbi": (12.6, 5.2, "Предприятие\nЖБИ / ДСК"),
        "bet": (9.2, 1.0, "Бетонный завод"),
        "kar": (12.6, 0.0, "Карьер щебня\nи песка"),
    }
    t = {}
    for k, (x, y, txt) in nodes.items():
        fc = "#fdd0a2" if k == "site" else "#ffffff"
        t[k] = ax.text(x, y, txt, ha="center", va="center", fontsize=7.0, weight="bold" if k == "site" else None,
                       bbox=dict(boxstyle="round,pad=0.4", fc=fc, ec="k", lw=0.7))
    fig.canvas.draw()

    def arrow(a, b, label, color="k", ls="-", rad=0.0, off=(0.0, 0.25)):
        ax.annotate("", xy=(0.5, 0.5), xycoords=t[b], xytext=(0.5, 0.5), textcoords=t[a],
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=1.1, ls=ls,
                                    patchA=t[a].get_bbox_patch(), patchB=t[b].get_bbox_patch(),
                                    shrinkA=2, shrinkB=2, connectionstyle=f"arc3,rad={rad}"))
        (x0, y0, _), (x1, y1, _) = nodes[a], nodes[b]
        ax.text((x0 + x1) / 2 + off[0], (y0 + y1) / 2 + off[1], label, ha="center", va="center",
                fontsize=6.2, color=color)

    arrow("msk", "dud", "Северный морской путь\n(круглогодично,\nс ледокольной проводкой)", "#08519c", off=(0, 0.55))
    arrow("kras", "dud", "р. Енисей —\nв навигацию\n(июнь–октябрь)", "#2171b5", rad=0.3, off=(-1.1, 0))
    arrow("dud", "nor", "ж/д и автодорога\nДудинка–Норильск ≈ 90 км", "#636363", off=(0, 0.62))
    arrow("air", "nor", "персонал\n(≈ 35 км)", "#54278f", ls="--", off=(0.75, 0.25))
    arrow("nor", "site", "≈ 10 км", "#636363", off=(0.15, 0.35))
    arrow("zhbi", "site", "≈ 12 км", "#d94801", off=(0.45, 0))
    arrow("bet", "site", "≈ 8 км", "#d94801", off=(0, 0.3))
    arrow("kar", "site", "≈ 15 км", "#d94801", off=(0.45, 0))
    ax.text(-0.6, -0.55, "Расстояния от местных предприятий приняты условно\n(уточняются по договорам поставки)",
            fontsize=6.2, color="#444444", va="bottom")
    ax.set_xlim(-0.8, 14.4)
    ax.set_ylim(-0.6, 6.2)
    ax.axis("off")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def make_all(r: calc.Results, outdir: str) -> dict:
    os.makedirs(outdir, exist_ok=True)
    paths = {
        "calendar": os.path.join(outdir, "calendar_plan.png"),
        "site": os.path.join(outdir, "site_plan.png"),
        "crane": os.path.join(outdir, "crane_scheme.png"),
        "transport": os.path.join(outdir, "transport_scheme.png"),
    }
    calendar_plan(r, paths["calendar"])
    site_plan(r, paths["site"])
    crane_scheme(r, paths["crane"])
    transport_scheme(paths["transport"])
    return paths


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "build/fig"
    print(make_all(calc.compute(), out))
