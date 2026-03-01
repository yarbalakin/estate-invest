"""Блок 2: ANALYTICS ENGINE — расчёт метрик из сырых данных."""

import pandas as pd

from data_loader import parse_number, parse_date


# ---------------------------------------------------------------------------
# Подготовка данных: конвертация строк в числа и даты
# ---------------------------------------------------------------------------

def prepare_data(raw_data):
    """Добавить числовые и датовые колонки к сырым DataFrame.

    Вызывается один раз после load_all_data().
    Оригинальные строковые колонки сохраняются для отображения.
    """
    data = dict(raw_data)

    # --- Транзакции ---
    tr = data["transactions"].copy()

    for src, dst in {
        "Сумма взноса руб": "взнос_руб",
        "Сумма инвестирования": "инвестиция",
        "Сумма инвестирования руб": "инвестиция_руб",
        "Сумма выплаты": "выплата",
        "Сумма выплаты руб": "выплата_руб",
        "Итого в объектах руб": "в_объектах_руб",
        "Итого остаток руб": "свободные_руб",
    }.items():
        tr[dst] = tr[src].apply(parse_number).fillna(0)

    for src, dst in {
        "Дата взноса": "дата_взноса",
        "Дата инвестирования": "дата_инвестирования",
        "Дата выплаты": "дата_выплаты",
    }.items():
        tr[dst] = tr[src].apply(parse_date)

    data["transactions"] = tr

    # --- Объекты ---
    obj = data["objects"].copy()

    for src, dst in {
        "col_5": "площадь",
        "col_7": "мин_срок_мес",
        "col_8": "макс_срок_мес",
        "col_10": "доп_расходы",
        "col_11": "цена_покупки",
        "col_13": "цена_покупки_руб",
        "col_14": "цена_продажи",
        "col_16": "цена_продажи_руб",
        "col_18": "roi",
        "col_21": "мин_сумма",
        "col_22": "макс_сумма",
    }.items():
        if src in obj.columns:
            obj[dst] = obj[src].apply(parse_number).fillna(0)

    for src, dst in {
        "col_6": "дата_старта",
        "col_19": "дата_окончания_сбора",
        "col_20": "дата_завершения",
    }.items():
        if src in obj.columns:
            obj[dst] = obj[src].apply(parse_date)

    data["objects"] = obj

    return data


# ===================================================================
# АНАЛИТИКА ПО ИНВЕСТОРАМ
# ===================================================================

def get_investor_list(data):
    """Отсортированный список уникальных инвесторов."""
    names = data["transactions"]["Инвестор"].unique()
    return sorted(n for n in names if n.strip())


def get_investor_summary(data, name):
    """Сводка по инвестору: вложил, в объектах, свободные, получил, баланс."""
    tr = data["transactions"]
    inv = tr[tr["Инвестор"] == name]

    # Вложения
    deposits = inv[inv["Вид взноса"] == "вложение"]
    total_deposited = deposits["взнос_руб"].sum()

    # Выплаты по типам
    payouts = inv[inv["Вид выплаты"].str.strip() != ""]
    body_returned = payouts.loc[
        payouts["Вид выплаты"] == "выплата тела", "выплата_руб"
    ].sum()
    interest_paid = payouts.loc[
        payouts["Вид выплаты"] == "выплата %", "выплата_руб"
    ].sum()
    referral_paid = payouts.loc[
        payouts["Вид выплаты"] == "реферальный бонус", "выплата_руб"
    ].sum()
    team_paid = payouts.loc[
        payouts["Вид выплаты"] == "командные", "выплата_руб"
    ].sum()

    total_received = body_returned + interest_paid + referral_paid + team_paid

    # Баланс из последней строки инвестора (рассчитан формулами таблицы)
    last_row = inv.iloc[-1]
    in_objects = last_row["в_объектах_руб"]
    free_funds = last_row["свободные_руб"]

    # Объекты
    objects = inv.loc[inv["Объект"].str.strip() != "", "Объект"].unique()

    return {
        "name": name,
        "total_deposited": total_deposited,
        "in_objects": in_objects,
        "free_funds": free_funds,
        "body_returned": body_returned,
        "interest_paid": interest_paid,
        "referral_paid": referral_paid,
        "team_paid": team_paid,
        "total_received": total_received,
        "profit": interest_paid + referral_paid + team_paid,
        "balance": total_deposited - body_returned,
        "objects_count": len(objects),
    }


def get_investor_objects(data, name):
    """Объекты, в которых участвует инвестор, с суммами."""
    tr = data["transactions"]
    inv = tr[(tr["Инвестор"] == name) & (tr["Объект"].str.strip() != "")]

    if inv.empty:
        return pd.DataFrame()

    rows = []
    for obj_name in inv["Объект"].unique():
        obj_rows = inv[inv["Объект"] == obj_name]

        invested = obj_rows["инвестиция_руб"].max()  # обычно одна сумма
        pct = obj_rows["% участия"].iloc[0]
        stage = obj_rows["Стадия объекта"].iloc[0]

        body = obj_rows.loc[
            obj_rows["Вид выплаты"] == "выплата тела", "выплата_руб"
        ].sum()
        interest = obj_rows.loc[
            obj_rows["Вид выплаты"] == "выплата %", "выплата_руб"
        ].sum()

        rows.append(
            {
                "Объект": obj_name,
                "Инвестировано": invested,
                "% участия": pct,
                "Стадия": stage,
                "Возврат тела": body,
                "Выплата %": interest,
                "Остаток": invested - body,
            }
        )

    return pd.DataFrame(rows)


def get_investor_transactions(data, name):
    """История транзакций инвестора (хронологически)."""
    tr = data["transactions"]
    inv = tr[tr["Инвестор"] == name].copy()

    # Определяем дату для сортировки
    inv["_дата"] = inv["дата_выплаты"].fillna(inv["дата_взноса"]).fillna(
        inv["дата_инвестирования"]
    )
    inv = inv.sort_values("_дата")

    # Определяем тип операции
    def row_type(r):
        if r["Вид взноса"].strip():
            return r["Вид взноса"]
        if r["Вид выплаты"].strip():
            return r["Вид выплаты"]
        if r["Объект"].strip():
            return "инвестирование"
        return "—"

    inv["Тип"] = inv.apply(row_type, axis=1)

    # Определяем сумму для отображения
    def row_amount(r):
        if r["Вид взноса"].strip():
            return r["взнос_руб"]
        if r["Вид выплаты"].strip():
            return r["выплата_руб"]
        if r["инвестиция_руб"] > 0:
            return r["инвестиция_руб"]
        return 0

    inv["Сумма"] = inv.apply(row_amount, axis=1)

    cols = ["_дата", "Тип", "Объект", "Сумма", "Валюта взноса"]
    result = inv[cols].rename(columns={"_дата": "Дата", "Валюта взноса": "Валюта"})

    return result.reset_index(drop=True)


def get_investor_payouts(data, name):
    """История выплат инвестору (только выплаты, хронологически)."""
    tr = data["transactions"]
    inv = tr[
        (tr["Инвестор"] == name) & (tr["Вид выплаты"].str.strip() != "")
    ].copy()

    inv = inv.sort_values("дата_выплаты")

    result = inv[["дата_выплаты", "Вид выплаты", "Объект", "выплата_руб", "Сумма выплаты", "Валюта выплаты"]].rename(
        columns={
            "дата_выплаты": "Дата",
            "Вид выплаты": "Тип",
            "выплата_руб": "Сумма руб",
            "Сумма выплаты": "Сумма ориг",
            "Валюта выплаты": "Валюта",
        }
    )
    return result.reset_index(drop=True)


def get_investor_roi_by_completed(data, name):
    """ROI инвестора по каждому завершённому объекту."""
    tr = data["transactions"]
    inv = tr[(tr["Инвестор"] == name) & (tr["Объект"].str.strip() != "")]

    rows = []
    for obj_name in inv["Объект"].unique():
        obj_rows = inv[inv["Объект"] == obj_name]
        stage = obj_rows["Стадия объекта"].iloc[0]

        if stage != "завершен":
            continue

        invested = obj_rows["инвестиция_руб"].max()
        if invested <= 0:
            continue

        interest = obj_rows.loc[
            obj_rows["Вид выплаты"] == "выплата %", "выплата_руб"
        ].sum()
        body = obj_rows.loc[
            obj_rows["Вид выплаты"] == "выплата тела", "выплата_руб"
        ].sum()

        roi = (interest / invested * 100) if invested > 0 else 0

        rows.append({
            "Объект": obj_name,
            "Инвестировано": invested,
            "Возврат тела": body,
            "Выплата %": interest,
            "ROI %": round(roi, 2),
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("ROI %", ascending=False)
    return df.reset_index(drop=True)


# ===================================================================
# АНАЛИТИКА ПО ОБЪЕКТАМ
# ===================================================================

def get_object_list(data):
    """Список объектов с основными полями."""
    obj = data["objects"]
    valid = obj[obj["Название объекта"].str.strip() != ""]
    return valid[
        ["Название объекта", "Тип", "Стадия объекта", "roi", "цена_покупки_руб",
         "цена_продажи_руб", "площадь"]
    ].reset_index(drop=True)


def get_object_summary(data, name):
    """P&L и детали объекта."""
    obj = data["objects"]
    match = obj[obj["Название объекта"] == name]

    if match.empty:
        return None

    row = match.iloc[0]

    purchase = row.get("цена_покупки_руб", 0) or 0
    sale = row.get("цена_продажи_руб", 0) or 0
    extra = row.get("доп_расходы", 0) or 0
    profit = sale - purchase - extra

    # Из транзакций
    tr = data["transactions"]
    obj_tr = tr[tr["Объект"] == name]

    total_invested = obj_tr["инвестиция_руб"].sum()
    investors_count = obj_tr["Инвестор"].nunique()
    body_returned = obj_tr.loc[
        obj_tr["Вид выплаты"] == "выплата тела", "выплата_руб"
    ].sum()
    interest_paid = obj_tr.loc[
        obj_tr["Вид выплаты"] == "выплата %", "выплата_руб"
    ].sum()

    return {
        "name": name,
        "type": row.get("Тип", ""),
        "area": row.get("площадь", 0),
        "stage": row.get("Стадия объекта", ""),
        "currency_buy": row.get("Валюта покупки", ""),
        "currency_sell": row.get("Валюта продажи", ""),
        "purchase_price": purchase,
        "sale_price": sale,
        "additional_costs": extra,
        "profit": profit,
        "roi": row.get("roi", 0),
        "start_date": row.get("дата_старта"),
        "end_date": row.get("дата_завершения"),
        "total_invested": total_invested,
        "investors_count": investors_count,
        "body_returned": body_returned,
        "interest_paid": interest_paid,
        "remaining_debt": total_invested - body_returned,
    }


def get_object_investors(data, name):
    """Инвесторы объекта с суммами."""
    tr = data["transactions"]
    obj_tr = tr[tr["Объект"] == name]

    if obj_tr.empty:
        return pd.DataFrame()

    rows = []
    for inv_name in obj_tr["Инвестор"].unique():
        inv_rows = obj_tr[obj_tr["Инвестор"] == inv_name]

        invested = inv_rows["инвестиция_руб"].max()
        pct = inv_rows["% участия"].iloc[0]
        body = inv_rows.loc[
            inv_rows["Вид выплаты"] == "выплата тела", "выплата_руб"
        ].sum()
        interest = inv_rows.loc[
            inv_rows["Вид выплаты"] == "выплата %", "выплата_руб"
        ].sum()

        rows.append(
            {
                "Инвестор": inv_name,
                "Инвестировано": invested,
                "% участия": pct,
                "Возврат тела": body,
                "Выплата %": interest,
                "Остаток": invested - body,
            }
        )

    return pd.DataFrame(rows)


def get_objects_comparison(data):
    """Таблица сравнения объектов для рейтинга."""
    obj = data["objects"]
    tr = data["transactions"]
    valid = obj[obj["Название объекта"].str.strip() != ""]

    rows = []
    for _, row in valid.iterrows():
        name = row["Название объекта"]
        obj_tr = tr[tr["Объект"] == name]

        invested = obj_tr["инвестиция_руб"].sum()
        investors = obj_tr["Инвестор"].nunique()
        body = obj_tr.loc[
            obj_tr["Вид выплаты"] == "выплата тела", "выплата_руб"
        ].sum()
        interest = obj_tr.loc[
            obj_tr["Вид выплаты"] == "выплата %", "выплата_руб"
        ].sum()

        rows.append(
            {
                "Объект": name,
                "Тип": row.get("Тип", ""),
                "Стадия": row.get("Стадия объекта", ""),
                "Площадь": row.get("площадь", 0),
                "Цена покупки": row.get("цена_покупки_руб", 0),
                "Цена продажи": row.get("цена_продажи_руб", 0),
                "ROI": row.get("roi", 0),
                "Инвесторов": investors,
                "Собрано руб": invested,
                "Возвращено тела": body,
                "Выплачено %": interest,
                "Остаток долга": invested - body,
            }
        )

    return pd.DataFrame(rows)


# ===================================================================
# ОБЩАЯ СВОДКА ПОРТФЕЛЯ
# ===================================================================

def get_portfolio_summary(data):
    """Общие метрики по всему портфелю."""
    tr = data["transactions"]
    obj = data["objects"]

    # Вложения
    deposits = tr[tr["Вид взноса"] == "вложение"]
    total_deposited = deposits["взнос_руб"].sum()

    # Выплаты
    payouts = tr[tr["Вид выплаты"].str.strip() != ""]
    total_body = payouts.loc[
        payouts["Вид выплаты"] == "выплата тела", "выплата_руб"
    ].sum()
    total_interest = payouts.loc[
        payouts["Вид выплаты"] == "выплата %", "выплата_руб"
    ].sum()
    total_referral = payouts.loc[
        payouts["Вид выплаты"] == "реферальный бонус", "выплата_руб"
    ].sum()
    total_team = payouts.loc[
        payouts["Вид выплаты"] == "командные", "выплата_руб"
    ].sum()

    # Баланс: в объектах и свободные (из последней строки каждого инвестора)
    last_rows = tr.groupby("Инвестор").last()
    total_in_objects = last_rows["в_объектах_руб"].sum()
    total_free_funds = last_rows["свободные_руб"].sum()

    # Объекты
    valid_obj = obj[obj["Название объекта"].str.strip() != ""]
    stages = valid_obj["Стадия объекта"].value_counts().to_dict()

    return {
        "investors_count": tr["Инвестор"].nunique(),
        "objects_total": len(valid_obj),
        "objects_active": stages.get("реализация", 0),
        "objects_completed": stages.get("завершен", 0),
        "objects_collecting": stages.get("сбор средств", 0),
        "objects_cancelled": stages.get("отменен", 0),
        "total_deposited": total_deposited,
        "total_in_objects": total_in_objects,
        "total_free_funds": total_free_funds,
        "total_body_returned": total_body,
        "total_interest_paid": total_interest,
        "total_referral_paid": total_referral,
        "total_team_paid": total_team,
        "total_paid_out": total_body + total_interest + total_referral + total_team,
        "remaining_debt": total_deposited - total_body,
    }
