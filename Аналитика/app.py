"""Estate Invest Analytics — Блок 1 + 2: Data Loader + Analytics Engine."""

import streamlit as st

from config import SHEETS, CACHE_TTL
from data_loader import load_all_data
from analytics import (
    prepare_data,
    get_portfolio_summary,
    get_investor_list,
    get_investor_summary,
    get_investor_objects,
    get_investor_transactions,
    get_investor_payouts,
    get_investor_roi_by_completed,
    get_object_list,
    get_object_summary,
    get_object_investors,
    get_objects_comparison,
)

# ---------------------------------------------------------------------------
# Настройки страницы
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Estate Invest Analytics",
    page_icon="🏢",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Кэшированная загрузка и подготовка данных
# ---------------------------------------------------------------------------


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_data():
    raw = load_all_data()
    return prepare_data(raw)


# ---------------------------------------------------------------------------
# Заголовок + навигация
# ---------------------------------------------------------------------------

st.title("Estate Invest Analytics")

if st.button("Обновить данные"):
    st.cache_data.clear()
    st.rerun()

with st.spinner(
    "Загрузка данных из Google Sheets... Первый запуск может занять до 30 сек."
):
    try:
        data = get_data()
    except Exception as e:
        st.error(f"Ошибка загрузки: {e}")
        st.stop()

tab_main, tab_cabinet, tab_investors, tab_objects, tab_compare, tab_raw = st.tabs(
    ["Сводка", "Кабинет инвестора", "Инвесторы (admin)", "Объекты", "Сравнение объектов", "Сырые данные"]
)


# ---------------------------------------------------------------------------
# Вспомогательная функция форматирования
# ---------------------------------------------------------------------------


def fmt(value, suffix="руб"):
    """Форматировать число: 1234567.89 → '1 234 568 руб'."""
    if value is None or value == 0:
        return "0"
    return f"{value:,.0f} {suffix}".replace(",", " ")


# ===================================================================
# Вкладка: СВОДКА
# ===================================================================

with tab_main:
    st.markdown("## Общая сводка портфеля")

    ps = get_portfolio_summary(data)

    # Ключевые цифры
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Инвесторов", f'{ps["investors_count"]:,}'.replace(",", " "))
    c2.metric("Объектов всего", ps["objects_total"])
    c3.metric("Активных", ps["objects_active"])
    c4.metric("Завершённых", ps["objects_completed"])
    c5.metric("Сбор средств", ps["objects_collecting"])
    c6.metric("Отменённых", ps["objects_cancelled"])

    st.divider()

    # Финансы
    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown("#### Привлечение")
        st.metric("Всего привлечено", fmt(ps["total_deposited"]))
        st.metric("В объектах", fmt(ps["total_in_objects"]))
        st.metric("Свободные средства", fmt(ps["total_free_funds"]))
    with f2:
        st.markdown("#### Выплаты")
        st.metric("Возврат тела", fmt(ps["total_body_returned"]))
        st.metric("Выплата процентов", fmt(ps["total_interest_paid"]))
        st.metric("Реферальные", fmt(ps["total_referral_paid"]))
        st.metric("Командные", fmt(ps["total_team_paid"]))
    with f3:
        st.markdown("#### Итого")
        st.metric("Итого выплачено", fmt(ps["total_paid_out"]))
        st.metric(
            "Остаток к возврату (тело)",
            fmt(ps["remaining_debt"]),
            help="Сколько ещё нужно вернуть инвесторам тела вложений",
        )


# ===================================================================
# Вкладка: КАБИНЕТ ИНВЕСТОРА
# ===================================================================

with tab_cabinet:
    st.markdown("## Кабинет инвестора")

    investors_all = get_investor_list(data)

    # Поиск по имени
    search = st.text_input(
        "Введите имя или фамилию",
        placeholder="Например: Иванов",
    )

    if search.strip():
        matches = [n for n in investors_all if search.strip().lower() in n.lower()]
    else:
        matches = []

    if not search.strip():
        st.info("Введите имя инвестора для поиска")
    elif not matches:
        st.warning(f"Инвестор «{search}» не найден")
    else:
        if len(matches) > 1:
            selected_cab = st.selectbox("Уточните инвестора", matches)
        else:
            selected_cab = matches[0]

        summary = get_investor_summary(data, selected_cab)

        # --- Заголовок ---
        st.markdown(f"### {selected_cab}")
        st.caption(f"Участвует в {summary['objects_count']} объектах")

        st.divider()

        # --- Раздел 1: Ключевые метрики ---
        st.markdown("#### Состояние средств")
        m1, m2, m3 = st.columns(3)
        m1.metric("Вложено всего", fmt(summary["total_deposited"]))
        m2.metric("В объектах (работает)", fmt(summary["in_objects"]))
        m3.metric("Свободные средства", fmt(summary["free_funds"]))

        r1, r2, r3 = st.columns(3)
        r1.metric("Возврат тела", fmt(summary["body_returned"]))
        r2.metric("Выплачено %", fmt(summary["interest_paid"]))
        r3.metric(
            "Итого получено",
            fmt(summary["total_received"]),
        )

        # --- Раздел 2: Объекты ---
        st.divider()
        st.markdown("#### Объекты")
        obj_df = get_investor_objects(data, selected_cab)
        if not obj_df.empty:
            st.dataframe(
                obj_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Инвестировано": st.column_config.NumberColumn(format="%.0f руб"),
                    "Возврат тела": st.column_config.NumberColumn(format="%.0f руб"),
                    "Выплата %": st.column_config.NumberColumn(format="%.0f руб"),
                    "Остаток": st.column_config.NumberColumn(format="%.0f руб"),
                },
            )
        else:
            st.info("Нет активных объектов")

        # --- Раздел 3: Доходность по завершённым ---
        roi_df = get_investor_roi_by_completed(data, selected_cab)
        if not roi_df.empty:
            st.divider()
            st.markdown("#### Доходность по завершённым объектам")

            # Итоговая строка
            total_inv = roi_df["Инвестировано"].sum()
            total_int = roi_df["Выплата %"].sum()
            avg_roi = (total_int / total_inv * 100) if total_inv > 0 else 0

            ri1, ri2, ri3 = st.columns(3)
            ri1.metric("Завершённых объектов", len(roi_df))
            ri2.metric("Суммарно инвестировано", fmt(total_inv))
            ri3.metric("Средний ROI", f"{avg_roi:.1f}%")

            st.dataframe(
                roi_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Инвестировано": st.column_config.NumberColumn(format="%.0f руб"),
                    "Возврат тела": st.column_config.NumberColumn(format="%.0f руб"),
                    "Выплата %": st.column_config.NumberColumn(format="%.0f руб"),
                    "ROI %": st.column_config.NumberColumn(format="%.2f %%"),
                },
            )

        # --- Раздел 4: История выплат ---
        st.divider()
        st.markdown("#### История выплат")
        payouts_df = get_investor_payouts(data, selected_cab)
        if not payouts_df.empty:
            st.dataframe(
                payouts_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Дата": st.column_config.DateColumn(format="DD.MM.YYYY"),
                    "Сумма руб": st.column_config.NumberColumn(format="%.0f руб"),
                },
            )
            st.caption(f"Всего выплат: {len(payouts_df)}")
        else:
            st.info("Выплат пока не было")


# ===================================================================
# Вкладка: ИНВЕСТОРЫ
# ===================================================================

with tab_investors:
    st.markdown("## Инвесторы")

    investors = get_investor_list(data)

    selected = st.selectbox(
        "Выберите инвестора",
        investors,
        index=None,
        placeholder="Начните вводить имя...",
    )

    if selected:
        summary = get_investor_summary(data, selected)

        st.markdown(f"### {selected}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Вложил", fmt(summary["total_deposited"]))
        c2.metric("В объектах", fmt(summary["in_objects"]))
        c3.metric("Свободные средства", fmt(summary["free_funds"]))
        c4.metric("Объектов", summary["objects_count"])

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Возврат тела", fmt(summary["body_returned"]))
        c6.metric("Выплата %", fmt(summary["interest_paid"]))
        c7.metric("Реферальные", fmt(summary["referral_paid"]))
        c8.metric("Получил всего", fmt(summary["total_received"]))

        # Объекты инвестора
        st.markdown("#### Объекты")
        obj_df = get_investor_objects(data, selected)
        if not obj_df.empty:
            st.dataframe(
                obj_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Инвестировано": st.column_config.NumberColumn(format="%.0f руб"),
                    "Возврат тела": st.column_config.NumberColumn(format="%.0f руб"),
                    "Выплата %": st.column_config.NumberColumn(format="%.0f руб"),
                    "Остаток": st.column_config.NumberColumn(format="%.0f руб"),
                },
            )
        else:
            st.info("Нет инвестиций в объекты")

        # История транзакций
        with st.expander("История транзакций"):
            hist = get_investor_transactions(data, selected)
            st.dataframe(hist, use_container_width=True, hide_index=True)


# ===================================================================
# Вкладка: ОБЪЕКТЫ
# ===================================================================

with tab_objects:
    st.markdown("## Объекты")

    obj_list = get_object_list(data)
    obj_names = obj_list["Название объекта"].tolist()

    selected_obj = st.selectbox(
        "Выберите объект",
        obj_names,
        index=None,
        placeholder="Начните вводить название...",
    )

    if selected_obj:
        os = get_object_summary(data, selected_obj)

        if os:
            st.markdown(f"### {selected_obj}")

            c1, c2, c3 = st.columns(3)
            c1.metric("Тип", os["type"] or "—")
            c2.metric("Площадь", f'{os["area"]} кв.м' if os["area"] else "—")
            c3.metric("Стадия", os["stage"])

            st.divider()
            st.markdown("#### P&L")

            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Цена покупки", fmt(os["purchase_price"]))
            p2.metric("Доп. расходы", fmt(os["additional_costs"]))
            p3.metric("Цена продажи", fmt(os["sale_price"]))
            p4.metric(
                "Прибыль",
                fmt(os["profit"]),
                delta=f'{os["roi"]}%' if os["roi"] else None,
            )

            st.divider()
            st.markdown("#### Инвесторы и выплаты")

            i1, i2, i3, i4 = st.columns(4)
            i1.metric("Инвесторов", os["investors_count"])
            i2.metric("Собрано", fmt(os["total_invested"]))
            i3.metric("Возвращено тела", fmt(os["body_returned"]))
            i4.metric("Выплачено %", fmt(os["interest_paid"]))

            st.metric("Остаток к возврату", fmt(os["remaining_debt"]))

            # Список инвесторов
            st.markdown("#### Список инвесторов")
            inv_df = get_object_investors(data, selected_obj)
            if not inv_df.empty:
                st.dataframe(
                    inv_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Инвестировано": st.column_config.NumberColumn(
                            format="%.0f руб"
                        ),
                        "Возврат тела": st.column_config.NumberColumn(
                            format="%.0f руб"
                        ),
                        "Выплата %": st.column_config.NumberColumn(
                            format="%.0f руб"
                        ),
                        "Остаток": st.column_config.NumberColumn(format="%.0f руб"),
                    },
                )


# ===================================================================
# Вкладка: СРАВНЕНИЕ ОБЪЕКТОВ
# ===================================================================

with tab_compare:
    st.markdown("## Сравнение объектов")

    comp = get_objects_comparison(data)

    # Фильтры
    fc1, fc2 = st.columns(2)
    with fc1:
        stage_filter = st.multiselect(
            "Стадия", comp["Стадия"].unique(), default=list(comp["Стадия"].unique())
        )
    with fc2:
        type_filter = st.multiselect(
            "Тип", comp["Тип"].dropna().unique(), default=list(comp["Тип"].dropna().unique())
        )

    filtered = comp[comp["Стадия"].isin(stage_filter) & comp["Тип"].isin(type_filter)]

    # Сортировка
    sort_col = st.selectbox(
        "Сортировать по",
        ["ROI", "Собрано руб", "Инвесторов", "Цена покупки"],
        index=0,
    )
    filtered = filtered.sort_values(sort_col, ascending=False)

    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ROI": st.column_config.NumberColumn(format="%.1f%%"),
            "Площадь": st.column_config.NumberColumn(format="%.0f кв.м"),
            "Цена покупки": st.column_config.NumberColumn(format="%.0f руб"),
            "Цена продажи": st.column_config.NumberColumn(format="%.0f руб"),
            "Собрано руб": st.column_config.NumberColumn(format="%.0f руб"),
            "Возвращено тела": st.column_config.NumberColumn(format="%.0f руб"),
            "Выплачено %": st.column_config.NumberColumn(format="%.0f руб"),
            "Остаток долга": st.column_config.NumberColumn(format="%.0f руб"),
        },
    )

    st.caption(f"Показано {len(filtered)} объектов из {len(comp)}")


# ===================================================================
# Вкладка: СЫРЫЕ ДАННЫЕ
# ===================================================================

with tab_raw:
    st.markdown("## Сырые данные (из Google Sheets)")

    sheet_keys = [
        "transactions", "investors", "objects",
        "summary_investors", "summary_objects", "summary_combined",
    ]

    for key in sheet_keys:
        df = data[key]
        label = SHEETS[key]["label"]
        with st.expander(f"{label} — {len(df):,} строк"):
            st.dataframe(df.head(20), use_container_width=True, height=400)
