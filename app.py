import json
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Читалища в България (1980-2000)", layout="wide")


@st.cache_data
def load_data():
    df = pd.read_csv("data_by_year.csv")

    # Robust year parsing
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)

    for c in [
        "chitalishta_total",
        "chitalishta_cities",
        "chitalishta_villages",
        "members_total",
        "members_cities",
        "members_villages",
    ]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


@st.cache_data
def load_geojson_28():
    with open("provinces.geojson", "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_geojson_9():
    with open("provinces_9.geojson", "r", encoding="utf-8") as f:
        return json.load(f)


df_all = load_data()  # includes BG rows if present
bg_geo_28 = load_geojson_28()
bg_geo_9 = load_geojson_9()

# ---- PATCH HISTORICAL NAMES/CODES HERE ----
name_fix = {
    "Толбухин": "Добрич",   # label unification
}
code_fix = {
    "TLB": "DOB",           # if old code exists
}

df_all["okrug"] = df_all["okrug"].replace(name_fix)
df_all["region_code"] = df_all["region_code"].replace(code_fix)

# ---------- ДАННИ ЗА ОСНОВНАТА КАРТА (оригинална логика) ----------
df = df_all[df_all["region_code"] != "BG"].copy()

# ако admin_type липсва – 28-окръжен режим по подразбиране
if "admin_type" not in df.columns:
    df["admin_type"] = "okrug28"

# ---------- ДАННИ ЗА HEATMAP (агрегирани 28→8) ----------
region_to_macro = {
    "BGS": "BGS",  # Бургас
    "SLV": "BGS",  # Сливен
    "JAM": "BGS",  # Ямбол
    "MON": "MON",  # Монтана
    "VID": "MON",  # Видин
    "VRC": "MON",  # Враца
    "VTR": "LOV",  # Велико Търново
    "PVN": "LOV",  # Плевен
    "LOV": "LOV",  # Ловеч
    "GAB": "LOV",  # Габрово
    "RSE": "RSE",  # Русе
    "SLS": "RSE",  # Силистра
    "RAZ": "RSE",  # Разград
    "TGV": "RSE",  # Търговище
    "VAR": "VAR",  # Варна
    "DOB": "VAR",  # Добрич
    "SHU": "VAR",  # Шумен
    "HKV": "HKV",  # Хасково
    "KRZ": "HKV",  # Кърджали
    "SZR": "HKV",  # Стара Загора
    "PDV": "PDV",  # Пловдив
    "PAZ": "PDV",  # Пазарджик
    "SML": "PDV",  # Смолян
    "BLG": "SFO",  # Благоевград
    "PER": "SFO",  # Перник
    "KNL": "SFO",  # Кюстендил
    "SFO": "SFO",  # София-област
    "SOF": "SOF",  # София-град
}

df_heat = df_all[df_all["region_code"] != "BG"].copy()
df_heat["macro_region_code"] = df_heat["region_code"].map(region_to_macro)
df_heat = df_heat.dropna(subset=["macro_region_code"])

st.title("Читалища - градове/села")

# ---- common controls ----
col1, col2 = st.columns(2)
years = sorted(df["year"].unique())

with col1:
    year_sel = st.slider(
        "Year",
        min_value=int(years[0]),
        max_value=int(years[-1]),
        value=int(years[0]),
        step=1,
    )

with col2:
    metric_sel = st.selectbox(
        "Metric (map)",
        ["общо", "градове", "села"],
    )

metric_col_map = {
    "общо": "chitalishta_total",
    "градове": "chitalishta_cities",
    "села": "chitalishta_villages",
}
metric_col = metric_col_map[metric_sel]

df_y = df[df["year"] == year_sel].copy()
df_y["value"] = df_y[metric_col]

# choose geometry and key per year/admin_type
if (df_y["admin_type"] == "oblast9").all():
    geo = bg_geo_9
    loc_col = "macro_region_code"  # при 9-областния shapefile колоната трябва да идва от CSV
else:
    geo = bg_geo_28
    loc_col = "region_code"

# global min/max for fixed color scale across all years
global_min = float(df[metric_col].min())
global_max = float(df[metric_col].max())

# ---- tabs ----
tab_map, tab_visitors, tab_side, tab_peaks = st.tabs(
    ["Карта", "Читатели(град/село)", "Сравнение/дисбаланс", "Пикове във времето"]
)

# ---------- TAB 1: SIMPLE MAP ----------
with tab_map:
    if metric_sel == "общо":
        metric_label = "общ брой читалища по области"
    elif metric_sel == "градове":
        metric_label = "брой читалища в градовете по области"
    else:
        metric_label = "брой читалища в селата по области"

    st.markdown(f"**Показател:** {metric_label.capitalize()} за избраната година.\n")

    st.markdown(
        """
**Важно за разделението на картата**

Визуализацията на картата за периода 1980–1986 г. представя страната, разделена на 28 области, а за периода 1987–1997 г. – на 8 области. Статистически данните са представени така в годишниците на НСИ, а тези визуализации следват това административно-териториално деление с цел кохерентност на данните.

**Допълнителна информация**

През 1978 г. с изменението и допълнението на Закона за народните съвети (1951 г.) територията на Народна република България е разделена на 28 окръга (включително София-град и София-окръг). Окръзите са управлявани от окръжни народни съвети. С административно-териториалната реформа от 1987 г. окръзите са ликвидирани и са създадени 8 области и Столична голяма община със статут на област.[web:373]
        """
    )

    fig = px.choropleth_mapbox(
        df_y,
        geojson=geo,          # 28 or 9
        locations=loc_col,    # region_code or macro_region_code
        featureidkey="properties.nuts3",  # adjust to your GeoJSON property
        color="value",
        hover_name="okrug",
        hover_data={"region_code": True, "value": True},
        color_continuous_scale="YlOrRd",
        range_color=(global_min, global_max),  # fixed scale over time
        mapbox_style="carto-positron",
        zoom=5.7,
        center={"lat": 42.7, "lon": 25.3},
        opacity=0.75,
        title=f"{metric_sel.capitalize()} chitalishta – {year_sel}",
    )
    fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})
    st.plotly_chart(fig, use_container_width=True)

# ---------- TAB 2: VISITORS BAR CHART ----------
with tab_visitors:
    df_bar = df_y.copy()
    df_bar["visitors_cities"] = df_bar["members_cities"]
    df_bar["visitors_villages"] = df_bar["members_villages"]

    df_long = df_bar.melt(
        id_vars=["okrug"],
        value_vars=["visitors_cities", "visitors_villages"],
        var_name="settlement",
        value_name="visitors",
    )
    df_long["settlement"] = df_long["settlement"].map(
        {"visitors_cities": "Градове", "visitors_villages": "Села"}
    )

    fig_bar = px.bar(
        df_long,
        x="okrug",
        y="visitors",
        color="settlement",
        barmode="group",
        labels={"okrug": "Област", "visitors": "Читатели"},
        title=f"Visitors by oblast – {year_sel}",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ---------- TAB 3: SIDE-BY-SIDE / SKEW MAPS ----------
with tab_side:
    view_mode = st.radio(
        "View",
        ["Сравнение – паралелен изглед", "Дисбаланс – абсолютна разлика", "Дисбаланс – относително съотношение"],
        horizontal=True,
    )

    def make_choropleth(
        data,
        value_col,
        title,
        color_scale,
        vmin=None,
        vmax=None,
        midpoint=None,
        hover_cols=None,
    ):
        if hover_cols is None:
            hover_cols = [
                "chitalishta_total",
                "chitalishta_cities",
                "chitalishta_villages",
            ]

        hover_dict = {"region_code": True}
        for c in hover_cols:
            hover_dict[c] = True

        fig_local = px.choropleth_mapbox(
            data,
            geojson=geo,       # same geometry choice
            locations=loc_col,  # same key as main map
            featureidkey="properties.nuts3",
            color=value_col,
            hover_name="okrug",
            hover_data=hover_dict,
            color_continuous_scale=color_scale,
            mapbox_style="carto-positron",
            zoom=5.7,
            center={"lat": 42.7, "lon": 25.3},
            opacity=0.78,
            title=title,
            range_color=(vmin, vmax) if (vmin is not None and vmax is not None) else None,
        )
        if midpoint is not None:
            fig_local.update_layout(coloraxis=dict(cmid=midpoint))
        fig_local.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})
        return fig_local

    df_side = df_y.copy()

    if view_mode == "Сравнение – паралелен изглед":
        shared_min = float(
            min(
                df_side["chitalishta_cities"].min(),
                df_side["chitalishta_villages"].min(),
            )
        )
        shared_max = float(
            max(
                df_side["chitalishta_cities"].max(),
                df_side["chitalishta_villages"].max(),
            )
        )

        col_left, col_right = st.columns(2)

        with col_left:
            fig_c = make_choropleth(
                df_side,
                value_col="chitalishta_cities",
                title=f"Cities – {year_sel}",
                color_scale="YlOrRd",
                vmin=shared_min,
                vmax=shared_max,
                hover_cols=["chitalishta_total", "chitalishta_cities"],
            )
            st.plotly_chart(fig_c, use_container_width=True)

        with col_right:
            fig_v = make_choropleth(
                df_side,
                value_col="chitalishta_villages",
                title=f"Villages – {year_sel}",
                color_scale="YlOrRd",
                vmin=shared_min,
                vmax=shared_max,
                hover_cols=["chitalishta_total", "chitalishta_villages"],
            )
            st.plotly_chart(fig_v, use_container_width=True)

    elif view_mode == "Дисбаланс – абсолютна разлика":
        df_side["villages_minus_cities"] = (
            df_side["chitalishta_villages"] - df_side["chitalishta_cities"]
        )
        diff_min = float(df_side["villages_minus_cities"].min())
        diff_max = float(df_side["villages_minus_cities"].max())
        bound = max(abs(diff_min), abs(diff_max))

        fig_diff = make_choropleth(
            df_side,
            value_col="villages_minus_cities",
            title=f"Villages minus cities – {year_sel}",
            color_scale="RdBu",
            vmin=-bound,
            vmax=bound,
            midpoint=0,
            hover_cols=[
                "chitalishta_total",
                "chitalishta_cities",
                "chitalishta_villages",
                "villages_minus_cities",
            ],
        )
        st.plotly_chart(fig_diff, use_container_width=True)

    else:  # Дисбаланс – относително съотношение
        df_side["villages_over_cities"] = (
            (df_side["chitalishta_villages"] + 1)
            / (df_side["chitalishta_cities"] + 1)
        )
        fig_ratio = make_choropleth(
            df_side,
            value_col="villages_over_cities",
            title=f"Villages over cities ratio – {year_sel}",
            color_scale="Viridis",
            hover_cols=[
                "chitalishta_total",
                "chitalishta_cities",
                "chitalishta_villages",
                "villages_over_cities",
            ],
        )
        st.plotly_chart(fig_ratio, use_container_width=True)

    with st.expander("See the table for this year"):
        st.dataframe(
            df_side[
                [
                    "okrug",
                    "region_code",
                    "chitalishta_total",
                    "chitalishta_cities",
                    "chitalishta_villages",
                ]
            ].sort_values("okrug"),
            use_container_width=True,
        )

# ---------- TAB 4: PEAKS OVER TIME ----------
with tab_peaks:
    # ---------- 4.1 National chitalishta over time ----------
    st.subheader("Брой читалища през времето")

    # use BG rows if present; otherwise sum all regions per year
    if (df_all["region_code"] == "BG").any():
        df_nat = (
            df_all[df_all["region_code"] == "BG"]
            .groupby("year", as_index=False)[["chitalishta_total"]]
            .sum()
        )
    else:
        df_nat = (
            df_all.groupby("year", as_index=False)[["chitalishta_total"]]
            .sum()
        )

    min_year = int(df_nat["year"].min())
    max_year = int(df_nat["year"].max())
    existing_years = set(df_nat["year"].unique())

    gap_years = [
        y for y in range(min_year, max_year + 1)
        if y not in existing_years
    ]

    df_nat["series"] = "chitalishta_total"
    df_nat_long = df_nat.rename(columns={"chitalishta_total": "value"})

    gap_rows = [
        {"year": y, "series": "chitalishta_total", "value": float("nan")}
        for y in gap_years
    ]

    df_nat_long_gap = (
        pd.concat([df_nat_long, pd.DataFrame(gap_rows)], ignore_index=True)
        .sort_values("year")
    )

    fig_nat = px.line(
        df_nat_long_gap,
        x="year",
        y="value",
        labels={
            "year": "Година",
            "value": "Читалища (общо)",
        },
        title="Читалища (общо) – национално ниво",
        markers=True,
    )
    st.plotly_chart(fig_nat, use_container_width=True)

    # пояснение за агрегирането към 8 области
    st.markdown(
        """
Данните за периода 1980–2000 г. са агрегирани до 8 административни области,
за да бъдат сравними във времето независимо от промяната от 28 към 8 окръга.
"""
    )

    # ---------- 4.2 Heatmap: 8 области, 1980–2000 ----------
    st.subheader("Топлинна карта: общ брой читалища по области (агрегирани до 8), 1980–2000")

    # агрегиране на всички години до 8 области
    df_macro = (
        df_heat
        .groupby(["macro_region_code", "year"], as_index=False)["chitalishta_total"]
        .sum()
    )

    if not df_macro.empty:
        heat_macro = df_macro.pivot_table(
            index="macro_region_code",
            columns="year",
            values="chitalishta_total",
            aggfunc="sum",
        )

        # гарантираме, че имаме всички години в диапазона
        y_min = int(df_macro["year"].min())
        y_max = int(df_macro["year"].max())
        full_years = list(range(y_min, y_max + 1))
        heat_macro = heat_macro.reindex(columns=full_years)

        fig_heat_macro = px.imshow(
            heat_macro,
            aspect="auto",
            color_continuous_scale="YlOrRd",
            labels={"color": "Читалища (общо)"},
        )
        st.plotly_chart(fig_heat_macro, use_container_width=True)

        with st.expander("Виж таблицата по области (8) и години"):
            st.dataframe(
                heat_macro,
                use_container_width=True,
            )
    else:
        st.info("Няма данни за периода 1980–2000.")

    # ---------- 4.3 Peak info ----------
    st.subheader("Peak years")

    col_a, col_b = st.columns(2)

    # 4.3.1 National peak year
    with col_a:
        st.markdown("**National peak (all years)**")
        peak_idx_nat = df_nat["chitalishta_total"].idxmax()
        peak_row_nat = df_nat.loc[[peak_idx_nat]].rename(columns={
            "year": "Година пик",
            "chitalishta_total": "Читалища (общо, национално)",
        })
        st.dataframe(peak_row_nat, use_container_width=True)

    # 4.3.2 Peak by macro-region (using aggregated 8-oblast series)
    with col_b:
        st.markdown("**Peak by macro-region (1980–2000, aggregated 28→8)**")
        if not df_macro.empty:
            idx_macro = df_macro.groupby("macro_region_code")["chitalishta_total"].idxmax()
            peak_macro = (
                df_macro.loc[idx_macro, ["macro_region_code", "year", "chitalishta_total"]]
                .rename(columns={
                    "macro_region_code": "Макрорегион",
                    "year": "Година пик",
                    "chitalishta_total": "Читалища (общо)",
                })
                .sort_values("Макрорегион")
            )
            st.dataframe(peak_macro, use_container_width=True)
        else:
            st.write("—")