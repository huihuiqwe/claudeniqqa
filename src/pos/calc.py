"""Расчётная часть ПОС.

Объект: 9-этажный 4-секционный крупнопанельный жилой дом из блок-секций
типового проекта 148-037сп/1.2, г. Норильск, начало строительства 01.12.2027,
фундаменты свайные.

Все числа, которые попадают в пояснительную записку, таблицы и графики,
вычисляются здесь, чтобы текст и иллюстрации не расходились между собой.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, field

import numpy as np

D = dt.date

# ---------------------------------------------------------------------------
# 1. Исходные данные
# ---------------------------------------------------------------------------
VARIANT = {
    "project": "148-037сп/1.2",
    "sections": 4,
    "region": "г. Норильск",
    "start": D(2027, 12, 1),
    "extra": "свайный фундамент",
}
N_SEC = VARIANT["sections"]
START = VARIANT["start"]

# ТЭП блок-секции по листу типового проекта (Строительный каталог, ч. 2, ЦИТП, 1983)
TP = {
    "name": "Блок-секция 9-этажная 18-квартирная с двойным поворотом прямая 4Б–4Б",
    "author": "ТашЗНИИЭП (г. Ташкент)",
    "floors": 9,
    "flats": 18,
    "floor_h": 3.0,
    "len_axes": 27.6,       # м, оси 1с–9с
    "body_len": 19.8,       # м, основной объём в осях 2с–8с
    "width_axes": 10.8,     # м, оси Ас–Вс
    "mark_roof": 26.750,    # верх основного объёма
    "mark_mr": 31.530,      # верх машинного помещения лифта
    "mark_ground": -1.100,  # планировочная отметка земли
    "S_built": 289, "S_reduced": 1553, "S_total": 1406, "S_living": 949,
    "S_summer": 402, "S_nonflat": 246,
    "V_build": 6448, "V_under": 107,
    "cost_total": 230, "cost_cmr": 224, "cost_eq": 6,   # тыс. руб., цены 1984 г., район IА
    "labor": 3536,                                     # чел.-дн., построечные трудозатраты
    "cement": 543, "steel": 101, "steel_red": 123,
    "concrete": 1911, "mono_heavy": 411, "mono_light": 12,
    "precast_heavy": 1237, "precast_light": 251,
    "timber": 121, "timber_round": 227, "brick": 1.3,
    "mass_total": 4640, "mass_above": 3780,
    "max_element": 7.76,                               # т, панель перекрытия
    "water_cold": 0.8, "water_hot": 1.1, "sewage": 3.5,
    "heat_total": 291.51, "heat_heating": 124.12, "heat_hw": 167.39,
    "gas": 5.1, "el_power": 36, "lift_q": 320,
}


def per_building(key: str) -> float:
    return TP[key] * N_SEC


BLD = {k: per_building(k) for k in (
    "S_built", "S_reduced", "S_total", "S_living", "S_summer", "S_nonflat",
    "V_build", "V_under", "cost_total", "cost_cmr", "cost_eq", "labor",
    "cement", "steel", "concrete", "mono_heavy", "mono_light",
    "precast_heavy", "precast_light", "timber", "brick", "mass_total", "mass_above")}
BLD["flats"] = TP["flats"] * N_SEC
BLD["length"] = TP["len_axes"] * N_SEC                     # 110,4 м по осям
BLD["height_roof"] = TP["mark_roof"] - TP["mark_ground"]   # 27,85 м от земли
BLD["height_mr"] = TP["mark_mr"] - TP["mark_ground"]       # 32,63 м от земли

# Климат и нагрузки (Норильск)
CLIMATE = {
    "t5_092": -46,       # °С, наиболее холодная пятидневка 0,92
    "t5_098": -47,
    "t_abs_min": -53.1,
    "t_jan": -27.6, "t_jul": 13.8, "t_year": -9.8,
    "frost_days": 280,   # период устойчивых морозов, сут
    "snow_months": "7,5–9",
    "blizzard_days": 130,
    "snow_kpa": 2.41, "snow_region": "V",
    "wind_kpa": 0.48, "wind_region": "IV",
}

# ---------------------------------------------------------------------------
# 2. Свайный фундамент (ориентировочно, до проекта привязки)
# ---------------------------------------------------------------------------
PILE = {
    "b": 0.35, "L": 12.0,          # сечение и длина буроопускной сваи, м
    "drill_d": 0.55,               # диаметр скважины, м
    "drill_depth": 10.8,           # глубина скважины, м (оголовок выступает на 1,2 м)
    "N_allow": 600.0,              # кН, допускаемая расчётная нагрузка на сваю (принята)
    "k_place": 1.08,               # учёт неравномерной передачи нагрузки и расстановки в узлах
    "walls_len": 159.0,            # м, длина несущих стен секции (по ростверку)
    "grill_b": 0.6, "grill_h": 0.8,
    "live_kpa": 1.5, "live_psi": 0.6, "gamma_f": 1.15,
    "G_under_t": 300.0,            # т, ростверк и цокольные конструкции секции
}


def pile_calc() -> dict:
    g = 9.81
    G_above = TP["mass_above"] * g
    G_under = PILE["G_under_t"] * g
    P_live = PILE["live_kpa"] * (TP["S_total"] + TP["S_nonflat"]) * PILE["live_psi"]
    P_snow = CLIMATE["snow_kpa"] * TP["S_built"]
    N_norm = G_above + G_under + P_live + P_snow
    N_des = N_norm * PILE["gamma_f"]
    n_raw = N_des / PILE["N_allow"] * PILE["k_place"]
    n_sec = int(math.ceil(n_raw / 4.0) * 4)          # кратно 4 (симметричная расстановка)
    n_total = n_sec * N_SEC
    v_pile = PILE["b"] ** 2 * PILE["L"]
    v_hole = math.pi * PILE["drill_d"] ** 2 / 4 * PILE["drill_depth"]
    v_mortar = v_hole - PILE["b"] ** 2 * PILE["drill_depth"]
    v_grill_sec = PILE["walls_len"] * PILE["grill_b"] * PILE["grill_h"]
    return {
        "G_above": G_above, "G_under": G_under, "P_live": P_live, "P_snow": P_snow,
        "N_norm": N_norm, "N_des": N_des, "n_raw": n_raw, "n_sec": n_sec,
        "n_total": n_total, "step": PILE["walls_len"] / n_sec,
        "v_pile": v_pile, "m_pile": v_pile * 2.5, "V_piles": v_pile * n_total,
        "v_hole": v_hole, "V_drill": v_hole * n_total,
        "drill_m": PILE["drill_depth"] * n_total,
        "v_mortar": v_mortar, "V_mortar": v_mortar * n_total,
        "V_grill_sec": v_grill_sec, "V_grill": v_grill_sec * N_SEC,
        "grill_steel_t": v_grill_sec * N_SEC * 0.10,
        "grill_form_m2": (2 * PILE["grill_h"] + PILE["grill_b"]) * PILE["walls_len"] * N_SEC,
    }


# ---------------------------------------------------------------------------
# 3. Продолжительность строительства (МДС 12-43.2008)
# ---------------------------------------------------------------------------
# Таблица 1 МДС 12-43.2008, 9 этажей, крупнопанельное:
#   общая площадь -> (общая, подготовительный, подземная, надземная, отделка), мес
MDS_9_PANEL = {3000: (5.0, 1.0, 1.0, 2.0, 1.0), 8000: (6.5, 1.0, 1.0, 3.5, 1.0)}
K_NORTH = 1.2              # п. 1 МДС 12-43.2008: для северного региона — до 1,2
PILE_DAYS_PER_100 = 10     # раб. дней на каждые 100 свай (Пособие к СНиП 1.04.03-85*)
WORKDAYS_PER_MONTH = 22


def duration_calc(n_piles: int) -> dict:
    F = BLD["S_total"]
    (f1, r1), (f2, r2) = sorted(MDS_9_PANEL.items())
    k = (F - f1) / (f2 - f1)
    stages = [a + k * (b - a) for a, b in zip(r1, r2)]
    T_tab = stages[0]
    dT_days = n_piles / 100 * PILE_DAYS_PER_100
    dT = dT_days / WORKDAYS_PER_MONTH
    T_raw = (T_tab + dT) * K_NORTH
    T = math.ceil(T_raw * 2 - 1e-9) / 2          # округление до 0,5 мес в большую сторону
    st = {
        "prep": stages[1] * K_NORTH,
        "under": (stages[2] + dT) * K_NORTH,
        "above": stages[3] * K_NORTH,
        "finish": stages[4] * K_NORTH,
    }
    return {"F": F, "f1": f1, "f2": f2, "r1": r1, "r2": r2, "k": k,
            "stages_tab": stages, "T_tab": T_tab, "dT_days": dT_days, "dT": dT,
            "T_raw": T_raw, "T": T, "stages": st}


# ---------------------------------------------------------------------------
# 4. Календарный план
# ---------------------------------------------------------------------------
K_LABOR = 1.2   # пересчёт трудоёмкости ТП на зимние условия Крайнего Севера

HOLIDAYS = [D(2027, 12, 31)] + [D(2028, 1, d) for d in range(1, 9)] + [
    D(2028, 2, 23), D(2028, 3, 8), D(2028, 5, 1), D(2028, 5, 9), D(2028, 6, 12)]
_HOL = np.array(HOLIDAYS, dtype="datetime64[D]")


def busdays(a: dt.date, b: dt.date) -> int:
    """Рабочие дни (пятидневка) с a по b включительно."""
    return int(np.busday_count(np.datetime64(a), np.datetime64(b + dt.timedelta(days=1)),
                               holidays=_HOL))


@dataclass
class Work:
    code: str
    name: str
    start: dt.date
    end: dt.date
    labor: float                 # чел.-дн.
    group: str
    trades: dict                 # профессия -> доля трудоёмкости
    shifts: float = 1.0
    unit: str = ""
    volume: float = 0.0
    days: int = 0
    workers: float = 0.0


GROUPS = {
    "prep": "Подготовительный период",
    "under": "Подземная часть",
    "above": "Надземная часть",
    "spec": "Специальные работы",
    "finish": "Отделочные работы",
    "ext": "Наружные сети и благоустройство",
}

# Распределение трудоёмкости здания по видам работ (доли от трудоёмкости ТП,
# пересчитанной на условия Норильска) — по аналогам для крупнопанельных домов
BUILDING_SHARES = {
    "B1": 0.0377, "B2": 0.0648, "B3": 0.0375,     # подземная часть — 14 %
    "C1": 0.23, "C2": 0.03, "C3": 0.03, "C4": 0.03,
    "D1": 0.11, "D2": 0.06, "D3": 0.02, "D4": 0.02,
    "E1": 0.20, "E2": 0.08, "F": 0.05,
}


def make_schedule(piles: dict) -> list[Work]:
    q_bld = BLD["labor"] * K_LABOR
    s = BUILDING_SHARES
    W = Work
    n = piles["n_total"]
    works = [
        W("1", "Геодезическая разбивочная основа, очистка территории от снега, планировка",
          D(2027, 12, 1), D(2027, 12, 10), 120, "prep", {"Дорожные рабочие, машинисты": 0.6, "Геодезисты": 0.4}),
        W("2", "Временное ограждение, КПП, пункт очистки колёс, информационный щит",
          D(2027, 12, 1), D(2027, 12, 15), 140, "prep", {"Монтажники": 0.6, "Плотники": 0.4}),
        W("3", "Временные дороги и площадки складирования (ж/б плиты по щебню)",
          D(2027, 12, 6), D(2027, 12, 28), 260, "prep", {"Дорожные рабочие, машинисты": 1.0}),
        W("4", "Установка инвентарных зданий (блок-контейнеров), тёплые переходы",
          D(2027, 12, 1), D(2027, 12, 20), 160, "prep", {"Монтажники": 0.6, "Электромонтажники": 0.4}),
        W("5", "Временные сети: электроснабжение (КТП), освещение, водопровод, канализация, связь",
          D(2027, 12, 6), D(2027, 12, 30), 220, "prep", {"Электромонтажники": 0.6, "Сантехники": 0.4}),
        W("6", f"Бурение скважин и погружение буроопускных свай ({n} шт.)",
          D(2027, 12, 13), D(2028, 2, 4), q_bld * s["B1"], "under",
          {"Бурильщики, машинисты": 0.5, "Монтажники": 0.3, "Бетонщики": 0.2}, 2.0, "шт.", n),
        W("7", "Подкрановый путь, монтаж и опробование башенного крана",
          D(2028, 1, 10), D(2028, 2, 18), 200, "prep", {"Монтажники": 0.7, "Электромонтажники": 0.3}),
        W("8", "Срубка голов свай, монолитный ж/б ростверк с электропрогревом в тепляках",
          D(2028, 1, 10), D(2028, 2, 29), q_bld * s["B2"], "under",
          {"Бетонщики": 0.45, "Арматурщики": 0.3, "Плотники": 0.25}, 2.0, "м³", piles["V_grill"]),
        W("9", "Цокольные конструкции, перекрытие над подпольем, утепление, вводы сетей",
          D(2028, 1, 31), D(2028, 3, 15), q_bld * s["B3"], "under",
          {"Монтажники": 0.6, "Изолировщики": 0.4}),
        W("10", "Монтаж сборных конструкций 1–9 этажей, чердака и покрытия, замоноличивание узлов",
          D(2028, 2, 21), D(2028, 5, 31), q_bld * s["C1"], "above",
          {"Монтажники": 0.65, "Электросварщики": 0.2, "Бетонщики": 0.15}, 2.0),
        W("11", "Герметизация и утепление стыков наружных стеновых панелей",
          D(2028, 3, 15), D(2028, 6, 9), q_bld * s["C2"], "above", {"Изолировщики": 1.0}),
        W("12", "Тепловой ввод, подключение системы отопления по временной схеме",
          D(2028, 3, 1), D(2028, 3, 31), 220, "ext", {"Сантехники": 0.7, "Электросварщики": 0.3}),
        W("13", "Кровля: утепление, кровельные панели, примыкания, внутренний водосток",
          D(2028, 4, 6), D(2028, 6, 20), q_bld * s["C3"], "above", {"Кровельщики": 1.0}),
        W("14", "Заполнение проёмов, двери, остекление лоджий, ограждения",
          D(2028, 4, 1), D(2028, 6, 30), q_bld * s["C4"], "above", {"Плотники": 0.7, "Монтажники": 0.3}),
        W("15", "Внутренние санитарно-технические системы (I и II стадии)",
          D(2028, 3, 1), D(2028, 7, 31), q_bld * s["D1"], "spec", {"Сантехники": 1.0}),
        W("16", "Электромонтажные работы (I и II стадии), электроплиты",
          D(2028, 3, 1), D(2028, 7, 31), q_bld * s["D2"], "spec", {"Электромонтажники": 1.0}),
        W("17", "Отделочные работы (шпаклёвка, окраска, обои, облицовка)",
          D(2028, 4, 3), D(2028, 8, 15), q_bld * s["E1"], "finish", {"Маляры, штукатуры": 0.8, "Облицовщики": 0.2}),
        W("18", "Монтаж лифтов и мусоропроводов, пусконаладка лифтов",
          D(2028, 5, 15), D(2028, 7, 31), q_bld * s["D4"], "spec", {"Монтажники лифтов": 1.0}),
        W("19", "Устройство полов (стяжки, линолеум, ламинат, плитка)",
          D(2028, 6, 1), D(2028, 8, 25), q_bld * s["E2"], "finish", {"Плиточники, паркетчики": 1.0}),
        W("20", "Слаботочные системы (связь, ТВ, домофон, АПС, диспетчеризация)",
          D(2028, 6, 1), D(2028, 8, 10), q_bld * s["D3"], "spec", {"Электромонтажники": 1.0}),
        W("21", "Прочие работы (входы, крыльца, отмостка, лоджии, встроенное оборудование)",
          D(2028, 6, 13), D(2028, 8, 25), q_bld * s["F"], "finish", {"Бетонщики": 0.4, "Плотники": 0.3, "Подсобные рабочие": 0.3}),
        W("22", "Демонтаж башенного крана и подкранового пути",
          D(2028, 6, 5), D(2028, 6, 30), 80, "prep", {"Монтажники": 0.7, "Электромонтажники": 0.3}),
        W("23", "Наружные сети водопровода, канализации, электроснабжения, связи (утилидоры)",
          D(2028, 6, 13), D(2028, 8, 10), 800, "ext", {"Сантехники": 0.5, "Электросварщики": 0.2, "Монтажники": 0.3}),
        W("24", "Благоустройство и озеленение территории",
          D(2028, 7, 10), D(2028, 8, 25), 680, "ext", {"Дорожные рабочие, машинисты": 0.6, "Подсобные рабочие": 0.4}),
        W("25", "Пусконаладочные работы, уборка, сдача объекта",
          D(2028, 8, 1), D(2028, 8, 31), 170, "ext", {"Наладчики": 0.6, "Подсобные рабочие": 0.4}),
    ]
    for w in works:
        w.labor = round(w.labor)
        w.days = busdays(w.start, w.end)
        w.workers = w.labor / w.days
    return works


@dataclass
class LaborGraph:
    dates: list
    daily: np.ndarray
    n_max: float
    n_avg: float
    alpha: float
    total: float
    workdays: int
    by_month: dict = field(default_factory=dict)
    trades_max: dict = field(default_factory=dict)


def labor_graph(works: list[Work], end: dt.date) -> LaborGraph:
    n_days = (end - START).days + 1
    dates = [START + dt.timedelta(days=i) for i in range(n_days)]
    is_bd = np.array([bool(np.is_busday(np.datetime64(d), holidays=_HOL)) for d in dates])
    daily = np.zeros(n_days)
    trades: dict[str, np.ndarray] = {}
    for w in works:
        i0, i1 = (w.start - START).days, (w.end - START).days
        mask = np.zeros(n_days, bool)
        mask[i0:i1 + 1] = True
        mask &= is_bd
        daily[mask] += w.workers
        for t, share in w.trades.items():
            trades.setdefault(t, np.zeros(n_days))[mask] += w.workers * share
    total = sum(w.labor for w in works)
    wd = int(is_bd.sum())
    n_max = float(daily.max())
    n_avg = total / wd
    by_month: dict = {}
    for d, v in zip(dates, daily):
        key = (d.year, d.month)
        by_month[key] = by_month.get(key, 0.0) + v
    trades_max = {t: float(a.max()) for t, a in trades.items()}
    return LaborGraph(dates, daily, n_max, n_avg, n_max / n_avg, total, wd, by_month, trades_max)


# ---------------------------------------------------------------------------
# 5. Кадры
# ---------------------------------------------------------------------------
CATEGORY_SHARES = {"Рабочие": 0.845, "ИТР": 0.11, "Служащие": 0.032, "МОП и охрана": 0.013}
DAYS_PER_YEAR = 230


def staff_calc(lg: LaborGraph, T_months: float) -> dict:
    # Выработка на 1 работающего в год по показателям ТП (базисные цены 1984 г.)
    B = TP["cost_cmr"] * 1000 / TP["labor"] * DAYS_PER_YEAR * CATEGORY_SHARES["Рабочие"]
    k_scope = lg.total / BLD["labor"]
    C = BLD["cost_cmr"] * k_scope                     # тыс. руб.
    T_years = T_months / 12
    N_out = C * 1000 / (B * T_years)
    cat_out = {k: N_out * v for k, v in CATEGORY_SHARES.items()}
    N_work_max = math.ceil(lg.n_max)
    N_all_max = N_work_max / CATEGORY_SHARES["Рабочие"]
    cat_max = {"Рабочие": N_work_max}
    for k in ("ИТР", "Служащие", "МОП и охрана"):
        cat_max[k] = math.ceil(N_all_max * CATEGORY_SHARES[k])
    shift = {"Рабочие": math.ceil(0.7 * cat_max["Рабочие"])}
    for k in ("ИТР", "Служащие", "МОП и охрана"):
        shift[k] = math.ceil(0.8 * cat_max[k])
    return {"B": B, "k_scope": k_scope, "C": C, "T_years": T_years, "N_out": N_out,
            "cat_out": cat_out, "cat_max": cat_max, "N_all_max": sum(cat_max.values()),
            "shift": shift, "N_shift": sum(shift.values())}


# ---------------------------------------------------------------------------
# 6. Монтажный кран
# ---------------------------------------------------------------------------
CRANE = {
    "model": "КБ-405.1А",
    "Q_max": 10.0, "R_Qmax": 18.0, "Q_Rmax": 7.5, "R_max": 25.0,
    "H_Rmax": 46.0, "H_max": 57.8, "M": 187.5, "gauge": 6.0, "base": 6.0,
    "P_kw": 101.7, "mass": 113.1, "r_tail": 4.0,
}


def crane_calc() -> dict:
    m_sling = 0.24                                       # 4СК-10 с траверсой
    Q = TP["max_element"] + m_sling
    h0 = (TP["mark_mr"] - 0.20) - TP["mark_ground"]      # опора плиты покрытия машинного помещения
    h_gap, h_el, h_sl = 0.5, 0.2, 4.0
    H = h0 + h_gap + h_el + h_sl
    b_clear = CRANE["r_tail"] + 0.7                      # поворотная часть + 0,7 м (ФНП ПС)
    b_proj = 1.2                                         # вынос лоджий/ограждений
    to_facade = b_clear + b_proj
    c_far = TP["width_axes"] + 0.4
    L = to_facade + c_far
    R_slab = to_facade + 5.4 + 2.7                       # центр дальней плиты перекрытия
    R_work = CRANE["R_Qmax"]
    delta = math.sqrt(R_work ** 2 - L ** 2)
    l_bld = BLD["length"] + 0.4
    l_cr = l_bld - 2 * delta
    l_track_raw = l_cr + CRANE["base"] + 2 * 1.5 + 2 * 0.5
    links = math.ceil(l_track_raw / 12.5)
    # опасная зона (РД-11-06-2007): R_max + 0,5·Bmin + Lmax + X
    B_min, L_max, X = 0.30, 6.0, 10.0
    R_danger = R_work + 0.5 * B_min + L_max + X
    return {"m_sling": m_sling, "Q": Q, "h0": h0, "h_gap": h_gap, "h_el": h_el, "h_sl": h_sl,
            "H": H, "b_clear": b_clear, "b_proj": b_proj, "to_facade": to_facade,
            "c_far": c_far, "L": L, "R_slab": R_slab, "R_work": R_work, "delta": delta,
            "l_bld": l_bld, "l_cr": l_cr, "l_track_raw": l_track_raw, "links": links,
            "l_track": links * 12.5, "M_req": Q * R_slab,
            "B_min": B_min, "L_max": L_max, "X": X, "R_danger": R_danger,
            "X_bld": 7.0}


# ---------------------------------------------------------------------------
# 7. Сборные конструкции и транспорт
# ---------------------------------------------------------------------------
def precast_calc() -> dict:
    ext = TP["precast_light"] * (1 + 16 / 19)                # двухслойные наружные панели
    rest = TP["precast_heavy"] - TP["precast_light"] * 16 / 19
    sec = {
        "Наружные стеновые панели": ext,
        "Внутренние стеновые панели": rest * 0.38,
        "Плиты перекрытий и покрытия": rest * 0.43,
        "Перегородки": rest * 0.07,
        "Санкабины, лестницы, лифтовые и вентблоки, лоджии": rest * 0.12,
    }
    per_floor = {"Наружные стеновые панели": 22, "Внутренние стеновые панели": 18,
                 "Плиты перекрытий и покрытия": 14, "Перегородки": 10,
                 "Санкабины, лестницы, лифтовые и вентблоки, лоджии": 15}
    extra_per_sec = 80                                       # цоколь, чердак, покрытие, машинное
    n_sec = sum(per_floor.values()) * TP["floors"] + extra_per_sec
    mass_sec = TP["precast_heavy"] * 2.5 + TP["precast_light"] * 1.6
    return {"vol_sec": sec, "vol": {k: v * N_SEC for k, v in sec.items()},
            "V_total": (TP["precast_heavy"] + TP["precast_light"]) * N_SEC,
            "n_elements": n_sec * N_SEC, "mass": mass_sec * N_SEC,
            "m_avg": mass_sec / n_sec, "per_floor": per_floor}


def transport_calc(pc: dict, works: list[Work], piles: dict) -> dict:
    erect = next(w for w in works if w.code == "10")
    Q_day = pc["mass"] / erect.days
    # панелевоз: полуприцеп г/п 16 т, коэффициент использования 0,8
    q_trip = 16 * 0.8
    L, v = 12.0, 20.0
    t_load, t_unload, t_man = 0.4, 1.0, 0.2
    t_cycle = t_load + 2 * L / v + t_unload + t_man
    trips_shift = math.floor(8 * 0.85 / t_cycle)
    per_day = trips_shift * 2 * q_trip
    n_panel = math.ceil(Q_day / per_day)
    # автобетоносмесители (ростверк): 7 м³, выдача 38 м³/смену
    v_mix = 7 * 0.85
    t_mix = 0.25 + 2 * 8.0 / 20.0 + 0.4 + 0.15
    trips_mix = math.floor(8 * 0.85 / t_mix)
    n_mix = math.ceil(38 / (trips_mix * v_mix))
    return {"Q_day": Q_day, "q_trip": q_trip, "L": L, "v": v, "t_cycle": t_cycle,
            "t_load": t_load, "t_unload": t_unload, "t_man": t_man,
            "trips_shift": trips_shift, "per_day": per_day, "n_panel": n_panel,
            "v_mix": v_mix, "t_mix": t_mix, "trips_mix": trips_mix, "n_mix": n_mix,
            "erect_days": erect.days}


# ---------------------------------------------------------------------------
# 8. Машины, механизмы, топливо
# ---------------------------------------------------------------------------
@dataclass
class Machine:
    name: str
    model: str
    purpose: str
    qty: int
    start: dt.date
    end: dt.date
    fuel_lph: float = 0.0        # л/ч дизельного топлива
    hours_day: float = 0.0       # маш.-ч в рабочий день на 1 машину
    power_kw: float = 0.0


def machines(tr: dict) -> list[Machine]:
    M = Machine
    return [
        M("Кран башенный", "КБ-405.1А (исп. ХЛ)", "монтаж надземной части", 1,
          D(2028, 2, 21), D(2028, 6, 4), 0, 0, CRANE["P_kw"]),
        M("Кран автомобильный 25 т", "КС-55713 «Галичанин» (ХЛ)",
          "установка свай, ростверк, монтаж крана, разгрузка", 2,
          D(2027, 12, 13), D(2028, 3, 15), 12, 14),
        M("Кран автомобильный 25 т", "КС-55713 «Галичанин» (ХЛ)",
          "кровля, демонтаж крана, сети, благоустройство", 1,
          D(2028, 3, 16), D(2028, 8, 25), 12, 6),
        M("Буровая установка для мёрзлых грунтов", "шнековая, D до 600 мм, глубина до 15 м",
          "бурение скважин под сваи", 2, D(2027, 12, 13), D(2028, 2, 4), 28, 14),
        M("Бульдозер", "Б10М (ХЛ)", "планировка, уборка снега", 1,
          D(2027, 12, 1), D(2028, 8, 25), 18, 2.5),
        M("Погрузчик фронтальный", "Амкодор 342В", "уборка и вывоз снега, ПРР", 1,
          D(2027, 12, 1), D(2028, 6, 15), 12, 5),
        M("Экскаватор-погрузчик", "JCB 3CX", "траншеи, заземление, благоустройство", 1,
          D(2027, 12, 1), D(2028, 8, 25), 8, 2),
        M("Автобетоносмеситель 7 м³", "на шасси КамАЗ (утеплённый барабан)",
          "доставка бетона и раствора", tr["n_mix"], D(2027, 12, 13), D(2028, 2, 29), 14, 7),
        M("Автобетононасос", "стрела 24 м", "бетонирование ростверка", 1,
          D(2028, 1, 10), D(2028, 2, 29), 15, 3),
        M("Панелевоз", "полуприцеп-панелевоз 16 т + тягач КамАЗ-65116",
          "доставка сборных конструкций", tr["n_panel"], D(2028, 2, 21), D(2028, 5, 31), 14, 15),
        M("Автосамосвал 15 т", "КамАЗ-65115 (ХЛ)", "щебень, вывоз грунта и снега", 2,
          D(2027, 12, 1), D(2028, 8, 25), 15, 3),
        M("Бортовой автомобиль", "КамАЗ-43118 (ХЛ)", "доставка материалов", 2,
          D(2027, 12, 1), D(2028, 8, 31), 10, 4),
        M("Автобус вахтовый", "НефАЗ-4208 на шасси КамАЗ", "перевозка работающих", 2,
          D(2027, 12, 1), D(2028, 8, 31), 12, 4),
        M("Топливозаправщик", "АТЗ-10", "заправка машин на площадке", 1,
          D(2027, 12, 1), D(2028, 8, 31), 10, 1),
        M("Теплогенератор дизельный 50 кВт", "непрямого нагрева", "тепляки ростверка и стыков", 4,
          D(2028, 1, 10), D(2028, 4, 15), 5.5, 16),
        M("Компрессорная станция", "ПКСД-5,25", "пневмоинструмент, продувка скважин", 1,
          D(2027, 12, 13), D(2028, 6, 30), 10, 4),
        M("Подъёмник мачтовый грузопассажирский", "г/п 1,0 т", "подача материалов на этажи", 2,
          D(2028, 5, 1), D(2028, 8, 20), 0, 0, 7.5),
        M("Сварочный аппарат", "инверторный 315 А", "сварка закладных и арматуры", 4,
          D(2028, 1, 10), D(2028, 7, 31), 0, 0, 0),
        M("Трансформатор для прогрева бетона", "КТПТО-80", "электропрогрев ростверка и стыков", 2,
          D(2028, 1, 10), D(2028, 4, 15), 0, 0, 0),
        M("Штукатурная (растворная) станция", "производительность 2–3 м³/ч", "стяжки, штукатурка", 2,
          D(2028, 5, 1), D(2028, 8, 20), 0, 0, 5.5),
        M("Люлька фасадная", "ЛЭ-100-300", "герметизация стыков", 2,
          D(2028, 5, 1), D(2028, 6, 10), 0, 0, 1.5),
    ]


def fuel_calc(mach: list[Machine]) -> dict:
    rows = []
    total = 0.0
    for m in mach:
        if not m.fuel_lph:
            continue
        hours = busdays(m.start, m.end) * m.hours_day * m.qty
        # для автотранспорта — зимняя надбавка до 20 % (АМ-23-р), принята усреднённо 10 %
        k_winter = 1.10
        litres = hours * m.fuel_lph * k_winter
        rows.append((m, hours, litres))
        total += litres
    lubric = total * 0.84 / 1000 * 0.05                     # т, 5 % от массы топлива
    return {"rows": rows, "diesel_l": total, "diesel_t": total * 0.84 / 1000,
            "lubric_t": lubric, "petrol_l": 2500}


# ---------------------------------------------------------------------------
# 9. Электроснабжение (период максимального потребления — март 2028 г.)
# ---------------------------------------------------------------------------
def power_calc(temp_area: float, site_area: float) -> dict:
    motors = [  # наименование, кол-во, P ед., Kс, cosφ
        ("Кран башенный КБ-405.1А", 1, CRANE["P_kw"], 0.3, 0.5),
        ("Электроинструмент, вибраторы", 1, 15.0, 0.15, 0.6),
        ("Насосы (водоснабжение, растворы)", 2, 2.0, 0.7, 0.8),
    ]
    weld = ("Сварочные аппараты (кВ·А)", 4, 20.0, 0.35, None)
    tech = [
        ("Электропрогрев бетона ростверка (КТПТО-80, кВ·А)", 1, 80.0, 0.8, None),
        ("Электропрогрев стыков (греющий провод)", 1, 20.0, 0.6, 0.9),
        ("Электроотопление инвентарных зданий", 1, round(temp_area * 0.12, 1), 0.8, 1.0),
        ("Электроводонагреватели душевых", 2, 9.0, 0.8, 1.0),
        ("Сушильные шкафы для спецодежды", 2, 3.0, 0.8, 1.0),
    ]
    rows = []
    s_motor = 0.0
    for nm, q, p, k, c in motors:
        val = k * q * p / c
        rows.append((nm, q, p, k, c, val))
        s_motor += val
    nm, q, p, k, _ = weld
    val = k * q * p
    rows.append((nm, q, p, k, "—", val))
    s_motor += val
    s_tech = 0.0
    for nm, q, p, k, c in tech:
        val = k * q * p / c if c else k * q * p
        rows.append((nm, q, p, k, c if c else "—", val))
        s_tech += val
    # освещение
    p_in = temp_area * 0.015 + 10.0                       # кВт: бытовки 15 Вт/м² + здание 10 кВт
    lighting = lighting_calc(site_area)
    p_out = lighting["P_total"]
    k_in = 0.8
    rows.append(("Внутреннее освещение (бытовки, строящееся здание)", 1, round(p_in, 1), k_in, 1.0, k_in * p_in))
    rows.append(("Наружное освещение (прожекторы)", 1, round(p_out, 1), 1.0, 1.0, p_out))
    s_light = k_in * p_in + p_out
    alpha = 1.1
    S = alpha * (s_motor + s_tech + s_light)
    tp = 400 if S <= 400 * 0.95 else 630
    return {"rows": rows, "s_motor": s_motor, "s_tech": s_tech, "s_light": s_light,
            "alpha": alpha, "S": S, "TP": tp, "lighting": lighting}


ILLUM = [  # участок, E (лк), площадь (м²) задаётся в lighting_calc
    ("Территория строительства (общее равномерное)", 2),
    ("Зона монтажа (рабочий горизонт и захватка)", 30),
    ("Склады и места разгрузки", 10),
    ("Проезды и проходы", 5),
    ("Охранное освещение по периметру", 0.5),
]
P_SPEC = 0.05       # Вт/(м²·лк) — светодиодные прожекторы
K_RESERVE = 1.5


def lighting_calc(site_area: float) -> dict:
    areas = [site_area, (BLD["length"] + 20) * (TP["width_axes"] + 20), 1200.0, 1000.0, 570 * 5.0]
    lamp = [150, 300, 150, 100, 50]
    rows = []
    total = 0.0
    for (nm, E), S, pl in zip(ILLUM, areas, lamp):
        P = P_SPEC * E * S * K_RESERVE / 1000
        n = max(1, math.ceil(P * 1000 / pl))
        rows.append((nm, E, S, P, pl, n))
        total += P
    return {"rows": rows, "P_total": total}


# ---------------------------------------------------------------------------
# 10. Водоснабжение, тепло, сжатый воздух
# ---------------------------------------------------------------------------
def water_calc(shift: dict) -> dict:
    prod = [  # потребитель, объём в смену, ед., норма л/ед.
        ("Приготовление и затворение растворов, стяжки", 20.0, "м³", 300.0),
        ("Малярные работы", 500.0, "м²", 1.0),
        ("Уход за бетоном (летний период)", 10.0, "м³", 200.0),
        ("Подпитка пункта мойки колёс (оборотная система)", 40.0, "маш.", 30.0),
        ("Заправка и охлаждение двигателей", 10.0, "маш.", 40.0),
        ("Полив зелёных насаждений", 500.0, "м²", 10.0),
    ]
    sum_prod = sum(v * q for _, v, _, q in prod)
    Kn, Kh, t = 1.2, 1.5, 8
    Q_prod = Kn * sum_prod * Kh / (t * 3600)
    N = shift["Рабочие"] + shift["ИТР"] + shift["Служащие"] + shift["МОП и охрана"]
    qx, Kx = 25.0, 2.0
    Q_hoz1 = qx * N * Kx / (t * 3600)
    qd, share_d, t1 = 30.0, 0.4, 45
    N_d = math.ceil(N * share_d)
    Q_shower = qd * N_d / (t1 * 60)
    Q_hoz = Q_hoz1 + Q_shower
    Q_fire = 10.0
    Q_total = Q_fire + 0.5 * (Q_prod + Q_hoz)
    v_fire, v_tmp = 1.5, 1.0
    D_fire = 2 * math.sqrt(Q_total / 1000 / (math.pi * v_fire)) * 1000
    D_tmp = 2 * math.sqrt((Q_prod + Q_hoz) / 1000 / (math.pi * v_tmp)) * 1000
    return {"prod": prod, "sum_prod": sum_prod, "Kn": Kn, "Kh": Kh, "t": t, "Q_prod": Q_prod,
            "N": N, "qx": qx, "Kx": Kx, "Q_hoz1": Q_hoz1, "qd": qd, "N_d": N_d, "t1": t1,
            "Q_shower": Q_shower, "Q_hoz": Q_hoz, "Q_fire": Q_fire, "Q_total": Q_total,
            "D_fire": D_fire, "D_tmp": D_tmp}


def heat_calc() -> dict:
    q0, tin, tout = 0.35, 18.0, -25.0           # Вт/(м³·°С), °С
    V = BLD["V_build"]
    Q1 = q0 * V * (tin - tout) / 1000            # кВт
    k_dry, k_loss = 1.15, 1.15
    Q = Q1 * k_dry * k_loss
    return {"q0": q0, "tin": tin, "tout": tout, "V": V, "Q1": Q1, "k_dry": k_dry,
            "k_loss": k_loss, "Q": Q, "Gcal": Q * 0.00086}


def air_calc() -> dict:
    tools = [("Отбойные молотки (срубка голов свай)", 3, 1.0),
             ("Продувка скважин и стыков", 2, 0.5),
             ("Краскораспылители", 2, 0.3)]
    k = 0.8
    Q = sum(n * q for _, n, q in tools) * k
    return {"tools": tools, "k": k, "Q": Q, "compressor": "ПКСД-5,25 (5,25 м³/мин)"}


# ---------------------------------------------------------------------------
# 11. Временные здания
# ---------------------------------------------------------------------------
CONTAINER = 14.4      # м², блок-контейнер 6,0×2,4 м в северном исполнении


def temp_buildings(staff: dict) -> dict:
    W_list = staff["cat_max"]["Рабочие"]
    W_shift = staff["shift"]["Рабочие"]
    itr_shift = staff["shift"]["ИТР"] + staff["shift"]["Служащие"]
    all_shift = staff["N_shift"]
    rows = [  # помещение, норма м²/чел, расчётная численность, пояснение
        ("Гардеробная (с отдельным хранением уличной и рабочей одежды)", 0.9, W_list, "все рабочие"),
        ("Помещение для обогрева рабочих", 0.2, W_shift, "рабочие max смены"),
        ("Сушильная для одежды и обуви", 0.2, W_shift, "рабочие max смены"),
        ("Душевая", 0.54, math.ceil(0.8 * W_shift), "80 % рабочих max смены"),
        ("Умывальная", 0.2, W_shift, "рабочие max смены"),
        ("Помещение для приёма пищи", 0.8, all_shift, "все работающие max смены"),
        ("Туалет", 0.1, all_shift, "все работающие max смены"),
        ("Прорабская (контора)", 4.0, itr_shift, "ИТР и служащие max смены"),
        ("Помещение для инструктажа и собраний", 0.75, math.ceil(0.5 * W_shift), "50 % рабочих max смены"),
        ("Медицинский пункт", None, None, "1 пункт"),
        ("КПП (проходная)", None, None, "1 пост"),
    ]
    out = []
    total = 0.0
    total_fact = 0.0
    for nm, norm, n, note in rows:
        if norm is None:
            area = 14.4 if "Мед" in nm else 7.2
            k = 1
        else:
            area = norm * n
            k = max(1, math.ceil(area / CONTAINER - 0.05))
        fact = k * CONTAINER if area > 7.2 else 7.2
        if "КПП" in nm:
            fact = 7.2
        out.append((nm, norm, n, note, area, k, fact))
        total += area
        total_fact += fact
    n_cont = sum(r[5] for r in out if "КПП" not in r[0])
    return {"rows": out, "area": total, "area_fact": total_fact, "n_cont": n_cont}


# ---------------------------------------------------------------------------
# 12. Склады
# ---------------------------------------------------------------------------
K1, K2 = 1.1, 1.3


def storage_calc(pc: dict, piles: dict, works: list[Work]) -> dict:
    erect_days = next(w for w in works if w.code == "10").days
    pile_days = next(w for w in works if w.code == "6").days
    v = pc["vol"]
    items = [  # материал, ед., Q, T, n, q (на 1 м²), β, тип
        ("Наружные стеновые панели", "м³", v["Наружные стеновые панели"], erect_days, 3, 0.5, 0.6,
         "открытый, в кассетах"),
        ("Внутренние стеновые панели и перегородки", "м³",
         v["Внутренние стеновые панели"] + v["Перегородки"], erect_days, 3, 0.6, 0.6, "открытый, в кассетах"),
        ("Плиты перекрытий и покрытия", "м³", v["Плиты перекрытий и покрытия"], erect_days, 3, 1.0, 0.6,
         "открытый, штабель до 2,5 м"),
        ("Санкабины, лестницы, лифтовые и вентблоки, лоджии", "м³",
         v["Санкабины, лестницы, лифтовые и вентблоки, лоджии"], erect_days, 3, 0.4, 0.6, "открытый"),
        ("Сваи 35×35, L = 12 м (в период свайных работ)", "м³", piles["V_piles"], pile_days, 5, 1.2, 0.6,
         "открытый, штабель до 2 м"),
        ("Арматура, закладные детали", "т", piles["grill_steel_t"] + 40, 100, 10, 1.2, 0.5, "навес"),
        ("Утеплитель, кровельные и изоляционные материалы", "м³", BLD["S_built"] * 0.25 + 120, 60, 10,
         2.0, 0.6, "навес / закрытый"),
        ("Отделочные материалы (смеси, краски, плитка, обои)", "т", 100.0, 75, 10, 1.0, 0.6, "закрытый"),
        ("Линолеум, ламинат", "м²", 5000.0, 60, 10, 150.0, 0.6, "закрытый"),
        ("Двери и столярные изделия", "м²", 940.0, 60, 10, 44.0, 0.6, "закрытый"),
        ("Инженерное оборудование, кабели, приборы", "т", 40.0, 100, 10, 0.5, 0.6, "закрытый"),
    ]
    rows = []
    sums = {"открытый": 0.0, "навес": 0.0, "закрытый": 0.0, "сваи": 0.0}
    for nm, u, Q, T, n, q, beta, kind in items:
        P = Q / T * n * K1 * K2
        F = P / q
        S = F / beta
        rows.append((nm, u, Q, T, Q / T, n, P, q, F, beta, S, kind))
        if nm.startswith("Сваи"):
            # склад свай нужен только в период свайных работ и размещается на месте склада панелей
            key = "сваи"
        else:
            key = "открытый" if kind.startswith("открытый") else ("навес" if kind.startswith("навес") else "закрытый")
        sums[key] += S
    return {"rows": rows, "sums": sums}


# ---------------------------------------------------------------------------
# 13. Стройгенплан (схема) — геометрия
# ---------------------------------------------------------------------------
def site_layout(cr: dict) -> dict:
    site_w, site_h = 200.0, 85.0
    x0 = 55.0
    y_south = 45.0
    sec_len, width = TP["len_axes"], TP["width_axes"]
    sections = [(x0 + i * sec_len, y_south, sec_len, width) for i in range(N_SEC)]
    x_mid = x0 + BLD["length"] / 2
    y_crane = y_south - cr["to_facade"]
    track = (x_mid - cr["l_track"] / 2, x_mid + cr["l_track"] / 2)
    cr_x = (track[0] + 0.5 + 1.5 + CRANE["base"] / 2, track[1] - 0.5 - 1.5 - CRANE["base"] / 2)
    road_y = y_crane - cr["R_work"] + 0.0       # ось дороги на рабочем вылете
    store = (y_crane - CRANE["r_tail"] - 0.7 - 10.0, y_crane - CRANE["r_tail"] - 0.7)
    return {"W": site_w, "H": site_h, "sections": sections, "x_mid": x_mid,
            "y_south": y_south, "y_crane": y_crane, "track": track, "cr_x": cr_x,
            "road_y": road_y, "store": store, "area": site_w * site_h,
            "fence": 2 * (site_w + site_h)}


# ---------------------------------------------------------------------------
# 14. Сводка
# ---------------------------------------------------------------------------
@dataclass
class Results:
    piles: dict
    dur: dict
    works: list
    lg: LaborGraph
    staff: dict
    crane: dict
    pc: dict
    tr: dict
    mach: list
    fuel: dict
    tb: dict
    power: dict
    water: dict
    heat: dict
    air: dict
    store: dict
    site: dict
    end: dt.date


def compute() -> Results:
    piles = pile_calc()
    dur = duration_calc(piles["n_total"])
    works = make_schedule(piles)
    end = max(w.end for w in works)
    lg = labor_graph(works, end)
    staff = staff_calc(lg, dur["T"])
    cr = crane_calc()
    pc = precast_calc()
    tr = transport_calc(pc, works, piles)
    mach = machines(tr)
    fuel = fuel_calc(mach)
    tb = temp_buildings(staff)
    site = site_layout(cr)
    power = power_calc(tb["area_fact"], site["area"])
    water = water_calc(staff["shift"])
    heat = heat_calc()
    air = air_calc()
    store = storage_calc(pc, piles, works)
    return Results(piles, dur, works, lg, staff, cr, pc, tr, mach, fuel, tb, power, water,
                   heat, air, store, site, end)


if __name__ == "__main__":
    r = compute()
    p, d = r.piles, r.dur
    print(f"Сваи: N_des={p['N_des']:.0f} кН/секц, n_raw={p['n_raw']:.1f}, n_sec={p['n_sec']}, "
          f"всего {p['n_total']}, шаг {p['step']:.2f} м, V_grill={p['V_grill']:.0f} м³")
    print(f"Продолжительность: k={d['k']:.4f} T_tab={d['T_tab']:.2f} dT={d['dT']:.2f} "
          f"T_raw={d['T_raw']:.2f} T={d['T']} этапы={ {k: round(v, 2) for k, v in d['stages'].items()} }")
    print(f"Окончание по календарному плану: {r.end}")
    for w in r.works:
        print(f"  {w.code:>3} {w.start}–{w.end} {w.days:>3} дн {w.labor:>6} чел.-дн {w.workers:6.1f} чел/дн  {w.name[:60]}")
    lg = r.lg
    print(f"Трудоёмкость {lg.total:.0f}, раб.дней {lg.workdays}, Nmax {lg.n_max:.1f}, "
          f"Nср {lg.n_avg:.1f}, α={lg.alpha:.2f}")
    print("По месяцам (чел.-дн):", {f'{k[1]:02d}.{k[0]}': round(v) for k, v in lg.by_month.items()})
    print("Профессии max:", {k: round(v, 1) for k, v in lg.trades_max.items()})
    s = r.staff
    print(f"Кадры: B={s['B']:.0f} руб/чел-год, C={s['C']:.0f} тыс.руб, N_out={s['N_out']:.1f}, "
          f"max={s['cat_max']}, смена={s['shift']} ({s['N_shift']})")
    c = r.crane
    print(f"Кран: Q={c['Q']:.2f} т, H={c['H']:.2f} м, L={c['L']:.2f} м, R_slab={c['R_slab']:.2f}, "
          f"M={c['M_req']:.1f} т·м, l_cr={c['l_cr']:.1f}, путь {c['l_track_raw']:.1f}->{c['l_track']} м, "
          f"R_оп={c['R_danger']:.2f}")
    print(f"Сборные: V={r.pc['V_total']:.0f} м³, n={r.pc['n_elements']}, m={r.pc['mass']:.0f} т, "
          f"m_ср={r.pc['m_avg']:.2f}")
    t = r.tr
    print(f"Транспорт: Q_day={t['Q_day']:.0f} т, t_ц={t['t_cycle']:.2f} ч, рейсов/смену {t['trips_shift']}, "
          f"панелевозов {t['n_panel']}, миксеров {t['n_mix']}")
    print(f"Топливо: {r.fuel['diesel_l']:.0f} л = {r.fuel['diesel_t']:.1f} т; масла {r.fuel['lubric_t']:.1f} т")
    print(f"Врем. здания: {r.tb['area']:.1f} м² треб., {r.tb['area_fact']:.1f} м² факт, {r.tb['n_cont']} конт.")
    for row in r.tb["rows"]:
        print("   ", row)
    pw = r.power
    print(f"Электро: S={pw['S']:.1f} кВ·А -> КТП {pw['TP']} (двиг {pw['s_motor']:.1f}, техн {pw['s_tech']:.1f}, "
          f"осв {pw['s_light']:.1f})")
    for row in pw["lighting"]["rows"]:
        print("   ", row)
    wt = r.water
    print(f"Вода: Qпр={wt['Q_prod']:.2f} Qхоз={wt['Q_hoz']:.2f} Qпож={wt['Q_fire']} Qобщ={wt['Q_total']:.2f} "
          f"D={wt['D_fire']:.1f} мм, Dврем={wt['D_tmp']:.1f} мм")
    print(f"Тепло: {r.heat['Q']:.0f} кВт = {r.heat['Gcal']:.3f} Гкал/ч; воздух {r.air['Q']:.2f} м³/мин")
    for row in r.store["rows"]:
        print("   ", row[0][:40], f"P={row[6]:.1f} F={row[8]:.1f} S={row[10]:.1f}", row[11])
    print("Склады:", {k: round(v) for k, v in r.store["sums"].items()})
    print("Площадка:", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.site.items() if k != 'sections'})
