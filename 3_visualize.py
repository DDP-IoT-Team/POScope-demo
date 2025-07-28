import streamlit as st
import pandas as pd
import datetime
from PIL import Image
import plotly.graph_objects as go
from plotly.subplots import make_subplots


#-----------------------------------------Settings-----------------------------------------

# Load images
favicon = Image.open("static/favicon.ico")
sleeping = Image.open("static/sleeping_hamburger.png")
sleeping_no_syllabus = Image.open("static/sleeping_hamburger_no_syllabus_data.png")

# Page configuration
st.set_page_config(
    page_title="データ可視化", 
    layout="wide",
    initial_sidebar_state="expanded", 
    page_icon=favicon, 
    menu_items={
        'Get help': st.secrets["documentation"]["notion_site"], # Documentation
        'Report a bug': st.secrets["google_forms"]["report_a_bug"], # Google Forms
        'About': "#### POScope \nv1.0.0"
    }
)


#-----------------------------------------Functions-----------------------------------------

# Future implementation
# When `@st.cache_data` is attached to a function, it caches the return in the memory
# and reuses it until any argument of the function changes.
# Therefore, `@st.cache_data` is useful for expensive computations.
# However, as stated above, the function is not executed when the arguments do not change, 
# so the options in the session state need to be included in the arguments.
# Otherwise, the function will not be executed when the options are changed.


#------------Universal------------

def convert_for_download(df: pd.DataFrame, index_flag: bool) -> bytes:
    """
    Convert the DataFrame to a CSV format encoded in Shift-JIS for download.\\
    The `index` parameter determines whether to include the index in the CSV.\\
    The option of `encoding` in `pd.DataFrame.to_csv()` is not supported when `path_or_buf` is `None`.
    """
    return df.to_csv(index=index_flag).encode("shift-jis")


#---Number of customers by time of day---

def process_cus1(df_cus: pd.DataFrame):
    """
    Filter the DataFrame based on the selected options and return a DataFrame for visualization of number of customers by time of day.\\
    Return an empty DataFrame if no valid data is found.
    """
    # Load options from session state
    date = st.session_state["date1"]
    span = st.session_state["span1"]
    business_hours = st.session_state["bsh1"]
    store = st.session_state["store1"]
    # Date inputs
    left_date = pd.Timestamp(date[0])
    right_date = pd.Timestamp(date[1]) + pd.Timedelta("1D")
    # Filter the DataFrame by date and store
    df_cus = df_cus[(left_date <= df_cus["開始日時"]) & (df_cus["開始日時"] < right_date)]
    df_cus = df_cus.query(f'アカウント名 == "{store}"')
    # Resample the number of customers by span
    df_cus = df_cus.resample(span, on="開始日時")["客数"].sum()
    if business_hours == "昼（11:00～14:00）":
        df_cus = df_cus.between_time("11:00", "14:00")
    elif business_hours == "夜（17:30～19:30）":
        df_cus = df_cus.between_time("17:30", "19:30")
    else:
        df_cus = df_cus.between_time("11:00", "19:30")
    # If the sum of customers is zero, there is nothing to visualize, so return an empty DataFrame
    if df_cus.sum() == 0:
        return pd.DataFrame()
    df_cus = df_cus.to_frame()
    df_cus["日付"] = df_cus.index.date
    df_cus["時間"] = df_cus.index.time
    df_cus = df_cus.set_index(["日付", "時間"])
    df_cus = df_cus.unstack(level=0)
    df_cus.index = list(map(lambda x: x.strftime("%H:%M"), df_cus.index))
    df_cus.columns = df_cus.columns.droplevel(0)
    return df_cus


#----Total number of customers per day----

def process_cus2(df_cus: pd.DataFrame):
    """
    Filter the DataFrame based on the selected options and return a DataFrame for visualization of total number of customers per day.\\
    Return an empty DataFrame if no valid data is found.
    """
    # Load options from session state
    date: tuple[datetime.date] = st.session_state["date2"]
    business_hours = st.session_state["bsh2"]
    store = st.session_state["store2"]
    # Date inputs
    left_date = pd.Timestamp(date[0])
    right_date = pd.Timestamp(date[1]) + pd.Timedelta("1D")
    # Filter the DataFrame by date and store
    df_cus = df_cus[(left_date <= df_cus["開始日時"]) & (df_cus["開始日時"] < right_date)]
    if store == "西食堂" or store == "東カフェテリア":
        df_cus = df_cus.query(f'アカウント名 == "{store}"')
    df_cus = df_cus.set_index("開始日時")
    if business_hours == "昼（11:00～14:00）":
        df_cus = df_cus.between_time("11:00", "14:00")
    elif business_hours == "夜（17:30～19:30）":
        df_cus = df_cus.between_time("17:30", "19:30")
    else:
        df_cus = df_cus.between_time("11:00", "19:30")
    df_cus = df_cus.reset_index(drop=False)
    if df_cus.empty:
        return pd.DataFrame()
    df_cus = df_cus.groupby("アカウント名").resample("1D", on="開始日時")["客数"].sum()
    df_cus = df_cus.to_frame().unstack(level=0)
    df_cus.columns = df_cus.columns.droplevel(0)
    return df_cus


#---------Ratio of payment methods---------

def filter_pm(df_cus: pd.DataFrame) -> pd.DataFrame:
    """
    Filter the DataFrame and return a DataFrame for visualization of the ratio of payment methods.
    It does not exclude records with multiple payment methods, 
    so the sum of the total counts is not necessarily equal to the total number of customers.
    """
    # Load options from session state
    date = st.session_state["date3"]
    business_hours = st.session_state["bsh3"]
    store = st.session_state["store3"]
    left_date = pd.Timestamp(date[0])
    right_date = pd.Timestamp(date[1]) + pd.Timedelta("1D")
    df_cus = df_cus[(left_date <= df_cus["開始日時"]) & (df_cus["開始日時"] < right_date)]
    if store == "西食堂" or store == "東カフェテリア":
        df_cus = df_cus.query(f'アカウント名 == "{store}"')
    df_cus = df_cus.set_index("開始日時")
    if business_hours == "昼（11:00～14:00）":
        df_cus = df_cus.between_time("11:00", "14:00")
    elif business_hours == "夜（17:30～19:30）":
        df_cus = df_cus.between_time("17:30", "19:30")
    else:
        df_cus = df_cus.between_time("11:00", "19:30")
    df_cus = df_cus.reset_index(drop=False)
    pms = list(set(df_cus.columns) - set(["アカウント名", "会計ID", "開始日時", "会計日時", "金額", "客数"]))
    df_pm = df_cus[pms] * df_cus["客数"].values.reshape(-1, 1)
    df_pm = df_pm.sum(axis="index").to_frame(name="合計利用者数").reset_index(names=["支払い方法"])
    return df_pm

#--------------Sales by item---------------

def process_itm1(df_itm: pd.DataFrame):
    """
    Filter the DataFrame based on the selected options and return a DataFrame for visualization of sales by item.\\
    If no valid data is found, return an empty DataFrame.
    """
    # Load options from session state
    date: tuple[datetime.date] = st.session_state["date4"]
    business_hours = st.session_state["bsh4"]
    store = st.session_state["store4"]
    aggregation = st.session_state["aggr4"]
    method = st.session_state["mthd4"]
    item = st.session_state["item4"]
    left_date = pd.Timestamp(date[0])
    right_date = pd.Timestamp(date[1]) + pd.Timedelta("1D")
    df_itm = df_itm[(left_date <= df_itm["開始日時"]) & (df_itm["開始日時"] < right_date)]
    if store == "西食堂" or store == "東カフェテリア":
        df_itm = df_itm.query(f'アカウント名 == "{store}"')
    if method == "名前":
        df_itm = df_itm[df_itm["名前"] == item]
    elif method == "バーコード":
        df_itm = df_itm[df_itm["バーコード"] == item]
    elif method == "SKU":
        df_itm = df_itm[df_itm["SKU"] == item]
    df_itm = df_itm.set_index("開始日時")
    if business_hours == "昼（11:00～14:00）":
        df_itm = df_itm.between_time("11:00", "14:00")
    elif business_hours == "夜（17:30～19:30）":
        df_itm = df_itm.between_time("17:30", "19:30")
    else:
        df_itm = df_itm.between_time("11:00", "19:30")
    df_itm = df_itm.reset_index(drop=False)
    if df_itm.empty:
        return pd.DataFrame()
    df_itm = df_itm.groupby("アカウント名").resample("1D", on="開始日時")[aggregation].sum()
    df_itm = df_itm.to_frame().unstack(level=0)
    df_itm.columns = df_itm.columns.droplevel(0)
    return df_itm


def candidates_itm1(df_itm: pd.DataFrame):
    """
    Return a list of possible candidates of items based on the selected options.
    """
    # Load options from session state
    date: tuple[datetime.date] = st.session_state["date4"]
    business_hours = st.session_state["bsh4"]
    store = st.session_state["store4"]
    method = st.session_state["mthd4"]
    if len(date) != 2:
        return []
    left_date = pd.Timestamp(date[0])
    right_date = pd.Timestamp(date[1]) + pd.Timedelta("1D")
    df_itm = df_itm[(left_date <= df_itm["開始日時"]) & (df_itm["開始日時"] < right_date)]
    if store == "西食堂" or store == "東カフェテリア":
        df_itm = df_itm.query(f'アカウント名 == "{store}"')
    df_itm = df_itm.set_index("開始日時")
    if business_hours == "昼（11:00～14:00）":
        df_itm = df_itm.between_time("11:00", "14:00")
    elif business_hours == "夜（17:30～19:30）":
        df_itm = df_itm.between_time("17:30", "19:30")
    else:
        df_itm = df_itm.between_time("11:00", "19:30")
    df_itm = df_itm.reset_index(drop=False)
    if method == "名前":
        candidates = df_itm["名前"].unique().tolist()
    elif method == "バーコード":
        candidates = df_itm["バーコード"].unique().tolist()
    elif method == "SKU":
        candidates = df_itm["SKU"].unique().tolist()
    return candidates

#------------Sales by department------------

def process_itm2(df_itm: pd.DataFrame):
    """
    Filter the DataFrame based on the selected options and return a DataFrame for visualization of sales by department.\\
    If no valid data is found, return an empty DataFrame.
    """
    # Load options from session state
    date: tuple[datetime.date] = st.session_state["date5"]
    business_hours = st.session_state["bsh5"]
    store = st.session_state["store5"]
    aggregation = st.session_state["aggr5"]
    department = st.session_state["dpmt5"]
    left_date = pd.Timestamp(date[0])
    right_date = pd.Timestamp(date[1]) + pd.Timedelta("1D")
    df_itm = df_itm[(left_date <= df_itm["開始日時"]) & (df_itm["開始日時"] < right_date)]
    if store == "西食堂" or store == "東カフェテリア":
        df_itm = df_itm.query(f'アカウント名 == "{store}"')
    df_itm = df_itm[df_itm["部門"] == department]
    df_itm = df_itm.set_index("開始日時")
    if business_hours == "昼（11:00～14:00）":
        df_itm = df_itm.between_time("11:00", "14:00")
    elif business_hours == "夜（17:30～19:30）":
        df_itm = df_itm.between_time("17:30", "19:30")
    else:
        df_itm = df_itm.between_time("11:00", "19:30")
    df_itm = df_itm.reset_index(drop=False)
    if df_itm.empty:
        return pd.DataFrame()
    df_itm = df_itm.groupby("アカウント名").resample("1D", on="開始日時")[aggregation].sum()
    df_itm = df_itm.to_frame().unstack(level=0)
    df_itm.columns = df_itm.columns.droplevel(0)
    return df_itm


def candidates_itm2(df_itm: pd.DataFrame):
    """
    Return a list of possible candidates of departments based on the selected options.
    """
    # Load options from session state
    date: tuple[datetime.date] = st.session_state["date5"]
    business_hours = st.session_state["bsh5"]
    store = st.session_state["store5"]
    if len(date) != 2:
        return []
    left_date = pd.Timestamp(date[0])
    right_date = pd.Timestamp(date[1]) + pd.Timedelta("1D")
    df_itm = df_itm[(left_date <= df_itm["開始日時"]) & (df_itm["開始日時"] < right_date)]
    if store == "西食堂" or store == "東カフェテリア":
        df_itm = df_itm.query(f'アカウント名 == "{store}"')
    df_itm = df_itm.set_index("開始日時")
    if business_hours == "昼（11:00～14:00）":
        df_itm = df_itm.between_time("11:00", "14:00")
    elif business_hours == "夜（17:30～19:30）":
        df_itm = df_itm.between_time("17:30", "19:30")
    else:
        df_itm = df_itm.between_time("11:00", "19:30")
    df_itm = df_itm.reset_index(drop=False)
    candidates = df_itm["部門"].unique().tolist()
    return candidates

#---------------Syllabus data---------------

def candidates_syl() -> list[str]:
    """
    Get a list of possible candidates of academic years for the syllabus data.
    """
    # Get syllabus data from session state
    df_syl_west: pd.DataFrame = st.session_state["df_syllabus_west"]
    df_syl_east: pd.DataFrame = st.session_state["df_syllabus_east"]
    # Get years from the columns
    west_years = df_syl_west.columns.str[:4].astype(int).tolist()
    east_years = df_syl_east.columns.str[:4].astype(int).tolist()
    years = sorted(set(west_years + east_years))
    return [str(year) + "年度" for year in years]


def sort_term(terms: list[str]) -> list[str]:
    """
    Sort terms in chronological order.
    """
    seasons = ["SPR", "SMR", "AUT", "WTR"]
    sorted_terms = sorted(terms, key=lambda x: (int(x[:4]), seasons.index(x[4:])))
    return sorted_terms


def process_syllabus():
    """
    Filter west and east syllabus DataFrames based on the selected options and return a list of DataFrames for visualization of syllabus data.\\
    If no valid data is found, return a list of empty DataFrames.
    """
    # Get syllabus data from session state
    df_syl_west: pd.DataFrame = st.session_state["df_syllabus_west"].copy()
    df_syl_east: pd.DataFrame = st.session_state["df_syllabus_east"].copy()
    # Get options from session state
    class_period = st.session_state["class_period"]
    year = st.session_state["year"]
    if class_period == [] or year == []:
        return [pd.DataFrame()] * 2
    else:
        class_period_num = [int(cp[0]) for cp in class_period]
        year_num = [y[:4] for y in year]
        # Filter the DataFrame by class period
        df_syl_west_filtered = df_syl_west.loc[(["月", "火", "水", "木", "金"], class_period_num), :]
        df_syl_east_filtered = df_syl_east.loc[(["月", "火", "水", "木", "金"], class_period_num), :]
        # Filter the DataFrame by year
        df_syl_west_filtered = df_syl_west_filtered.loc[:, df_syl_west_filtered.columns.str[:4].isin(year_num)]
        df_syl_east_filtered = df_syl_east_filtered.loc[:, df_syl_east_filtered.columns.str[:4].isin(year_num)]
        # Group by day of the week and sum the values
        df_syl_west_filtered = df_syl_west_filtered.groupby(by="曜日").sum()
        df_syl_east_filtered = df_syl_east_filtered.groupby(by="曜日").sum()
        # Sort indices
        df_syl_west_filtered = df_syl_west_filtered.reindex(index=["月", "火", "水", "木", "金"])
        df_syl_east_filtered = df_syl_east_filtered.reindex(index=["月", "火", "水", "木", "金"])
        # Sort columns
        west_cols = sort_term(df_syl_west_filtered.columns.tolist())
        east_cols = sort_term(df_syl_east_filtered.columns.tolist())
        df_syl_west_filtered = df_syl_west_filtered.reindex(columns=west_cols)
        df_syl_east_filtered = df_syl_east_filtered.reindex(columns=east_cols)
        return [df_syl_west_filtered, df_syl_east_filtered]


#-----------------------------------------Contents-----------------------------------------

# logo in the sidebar
st.logo(favicon, size="large")

st.header("データの可視化")

# Check if the POS data has been uploaded
if "df_customers" not in st.session_state:
    st.error(":material/error: POSデータがアップロードされていません。")
    st.stop() # Stop executing

# Load data from session states
df_cus = st.session_state["df_customers"].copy()
df_itm = st.session_state["df_items"].copy()
# be used to restric the range of date inputs
min_date = st.session_state["min_date"]
max_date = st.session_state["max_date"]

# 1. number of customers by time of day
with st.container(border=True):
    st.write("##### 1日の時間帯ごとの客数の推移")
    # Options
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.date_input(
                label=":material/calendar_month: 日付", 
                value=(min_date, min_date), 
                min_value=min_date, 
                max_value=max_date, 
                key="date1"
            )
        with col2:
            st.selectbox(
                label=":material/timer: 集計スパン", 
                options=["5min", "10min", "30min"], 
                index=0, 
                accept_new_options=False, 
                key="span1"
            )
        with col3:
            st.selectbox(
                label=":material/schedule: 営業時間", 
                options=["昼（11:00～14:00）", "夜（17:30～19:30）", "昼・夜"], 
                index=0, 
                accept_new_options=False, 
                key="bsh1"
            )
        with col4:
            st.selectbox(
                label=":material/storefront: 店舗", 
                options=["西食堂", "東カフェテリア"], 
                accept_new_options=False, 
                index=0, 
                key="store1"
            )
    # Data processing and visualization
    with st.container(border=True):
        if len(st.session_state["date1"]) == 2:
            df_cus_time = process_cus1(df_cus)
            if not df_cus_time.empty:
                # Identify dates with no customers (ex. holidays)
                df_cus_time_sum = df_cus_time.sum(axis="index")
                exclude_dates = df_cus_time_sum[df_cus_time_sum == 0].index.tolist()
                # Plotly
                fig = go.Figure()
                # tab:orange for "西食堂" and tab:blue for "東カフェテリア"
                colors = {"西食堂": "rgba(255, 127, 14, 0.7)", "東カフェテリア": "rgba(0, 104, 201, 0.7)"}
                for date in df_cus_time.columns:
                    if date.weekday() in [5, 6] or date in exclude_dates:  # Saturday and Sunday
                        continue
                    fig.add_trace(go.Scatter(
                        x=df_cus_time.index, 
                        y=df_cus_time[date], 
                        mode="lines+markers", 
                        name=date.strftime("%Y-%m-%d"), 
                        line=dict(color=colors[st.session_state["store1"]]), 
                        marker=dict(size=5), 
                        hovertemplate="日付: %{meta}<br>時刻: %{x}<br>客数: %{y}人<extra></extra>", 
                        meta=date.strftime("%Y-%m-%d (%a)"), 
                        hoverlabel=dict(font=dict(size=15))
                    ))
                # Plot average if there are multiple columns
                if len(df_cus_time.columns) >= 2:
                    # Calculate the average for only weekdays (excluding weekends)
                    ave = df_cus_time[
                        [col for col in df_cus_time.columns if col.weekday() not in [5, 6] and col not in exclude_dates]
                    ].mean(axis="columns")
                    fig.add_trace(go.Scatter(
                        x=df_cus_time.index, 
                        y=ave, 
                        mode="lines+markers", 
                        name="平均", 
                        line=dict(color="rgba(0, 0, 0, 1)", dash="dot"), 
                        marker=dict(size=5), 
                        hovertemplate="平均<br>時刻: %{x}<br>客数: %{y:.1f}人<extra></extra>", 
                        hoverlabel=dict(font=dict(size=15))
                    ))
                st.plotly_chart(fig)
            # When nothing to show, display a sleeping hamburger
            else:
                st.image(sleeping)
    # Data
    with st.expander("データを見る", expanded=False):
        if len(st.session_state["date1"]) == 2:
            st.dataframe(df_cus_time)
            st.download_button(
                label=":material/download: `.csv`でダウンロード", 
                data=convert_for_download(df_cus_time, index_flag=True), 
                file_name=f"customers_by_time_{st.session_state['date1'][0]}-{st.session_state['date1'][1]}.csv", 
                mime="text/csv"
            )

# space
st.write("")

# 2. total number of customers per day
with st.container(border=True):
    st.write("##### 1日の合計客数の推移")
    # Options
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.date_input(
                label=":material/calendar_month: 日付", 
                value=(min_date, max_date), 
                min_value=min_date, 
                max_value=max_date, 
                key="date2"
            )
        with col2:
            st.selectbox(
                label=":material/schedule: 営業時間", 
                options=["昼（11:00～14:00）", "夜（17:30～19:30）", "昼・夜"], 
                index=0, 
                accept_new_options=False, 
                key="bsh2", 
                help="「昼・夜」を選択すると、昼営業と夜営業のデータを合算します。"
            )
        with col3:
            st.selectbox(
                label=":material/storefront: 店舗", 
                options=["西食堂", "東カフェテリア", "両方"], 
                accept_new_options=False, 
                index=0, 
                key="store2", 
                help="「両方」を選択すると、東西店舗の各グラフを重ね合わせて可視化します。"
            )
    # Data processing and visualization
    with st.container(border=True):
        if len(st.session_state["date2"]) == 2:
            df_cus_day = process_cus2(df_cus)
            if not df_cus_day.empty:
                stores = df_cus_day.columns
                # Add more information from the calendar data if available
                if "df_calendar" in st.session_state:
                    df_cus_day = pd.merge(
                        df_cus_day, 
                        st.session_state["df_calendar"], 
                        left_index=True, 
                        right_on="date", 
                        how="left"
                    ).rename(columns={"date": "開始日時"}).set_index("開始日時")
                    # Plotly
                    fig = go.Figure()
                    # tab:orange for "西食堂" and tab:blue for "東カフェテリア"
                    colors = {"西食堂": "rgba(255, 127, 14, 0.7)", "東カフェテリア": "rgba(0, 104, 201, 0.7)"}
                    for store in stores:
                        fig.add_trace(go.Scatter(
                            x=df_cus_day.index, 
                            y=df_cus_day[store], 
                            mode="lines+markers", 
                            marker=dict(size=5), 
                            name=store, 
                            hovertemplate="日付: %{x|%Y-%m-%d (%a)}<br>客数: %{y:,}人<br>学期: %{meta[0]}年度%{meta[1]}<br>講義情報: %{meta[2]}<br>その他情報: %{meta[3]}<extra></extra>", 
                            meta=df_cus_day[["academic_year", "term", "class", "info"]].values.tolist(), 
                            hoverlabel=dict(font=dict(size=15)), 
                            line=dict(color=colors[store])
                        ))
                    st.plotly_chart(fig)
                else:
                    # Plotly
                    fig = go.Figure()
                    # tab:orange for "西食堂" and tab:blue for "東カフェテリア"
                    colors = {"西食堂": "rgba(255, 127, 14, 0.7)", "東カフェテリア": "rgba(0, 104, 201, 0.7)"}
                    for store in stores:
                        fig.add_trace(go.Scatter(
                            x=df_cus_day.index, 
                            y=df_cus_day[store], 
                            mode="lines+markers", 
                            marker=dict(size=5), 
                            name=store, 
                            hovertemplate="日付: %{x|%Y-%m-%d (%a)}<br>客数: %{y:,}人<extra></extra>", 
                            hoverlabel=dict(font=dict(size=15)), 
                            line=dict(color=colors[store])
                        ))
                    st.plotly_chart(fig)
            # When nothing to show, display a sleeping hamburger
            else:
                st.image(sleeping)
    # Data
    with st.expander("データを見る", expanded=False):
        if len(st.session_state["date2"]) == 2:
            st.dataframe(df_cus_day)
            st.download_button(
                label=":material/download: `.csv`でダウンロード", 
                data=convert_for_download(df_cus_day, index_flag=True), 
                file_name=f"customers_per_day_{st.session_state['date2'][0]}-{st.session_state['date2'][1]}.csv", 
                mime="text/csv"
            )
        
# space
st.write("")

# 3. ratio of payment methods
with st.container(border=True):
    st.write("##### 支払い方法の割合")
    # Options
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.date_input(
                label=":material/calendar_month: 日付", 
                value=(min_date, max_date), 
                min_value=min_date, 
                max_value=max_date, 
                key="date3"
            )
        with col2:
            st.selectbox(
                label=":material/schedule: 営業時間", 
                options=["昼（11:00～14:00）", "夜（17:30～19:30）", "昼・夜"], 
                index=0, 
                accept_new_options=False, 
                key="bsh3", 
                help="「昼・夜」を選択すると、昼営業と夜営業のデータを合算して割合を計算します。"
            )
        with col3:
            st.selectbox(
                label=":material/storefront: 店舗", 
                options=["西食堂", "東カフェテリア", "両方"], 
                accept_new_options=False, 
                index=0, 
                key="store3", 
                help="「両方」を選択すると、東西両店舗のデータを合算して割合を計算します。"
            )
    # Data processing and visualization
    with st.container(border=True):
        if len(st.session_state["date3"]) == 2:
            df_pm = filter_pm(df_cus)
            if df_pm["合計利用者数"].sum() != 0:
                fig = go.Figure()
                fig.add_trace(go.Pie(
                    values=df_pm["合計利用者数"], 
                    labels=df_pm["支払い方法"], 
                    hovertemplate="支払い方法: %{label}<br>合計利用者数: %{value:,}人<extra></extra>", 
                    hoverlabel=dict(font=dict(size=15))
                ))
                st.plotly_chart(fig)
            # When nothing to show, display a sleeping hamburger
            else:
                st.image(sleeping)
    # Data
    with st.expander("データを見る", expanded=False):
        if len(st.session_state["date3"]) == 2:
            st.dataframe(df_pm, hide_index=True)
            st.download_button(
                label=":material/download: `.csv`でダウンロード", 
                data=convert_for_download(df_pm, index_flag=False), 
                file_name=f"payments_{st.session_state['date3'][0]}-{st.session_state['date3'][1]}.csv", 
                mime="text/csv"
            )

# space
st.write("")

# 4. sales by item
with st.container(border=True):
    st.write("##### 各商品ごとの売上推移")
    # Options
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.date_input(
                label=":material/calendar_month: 日付", 
                value=(min_date, max_date), 
                min_value=min_date, 
                max_value=max_date, 
                key="date4"
            )
        with col2:
            st.selectbox(
                label=":material/schedule: 営業時間", 
                options=["昼（11:00～14:00）", "夜（17:30～19:30）", "昼・夜"], 
                index=0, 
                accept_new_options=False, 
                key="bsh4", 
                help="「昼・夜」を選択すると、昼営業と夜営業のデータを合算します。"
            )
        with col3:
            st.selectbox(
                label=":material/storefront: 店舗", 
                options=["西食堂", "東カフェテリア", "両方"], 
                accept_new_options=False, 
                index=0, 
                key="store4", 
                help="「両方」を選択すると、東西店舗の各グラフを重ね合わせて可視化します。"
            )
        with col4:
            st.selectbox(
                label=":material/calculate: 集計方法", 
                options=["数量", "金額"], 
                index=0, 
                accept_new_options=False,
                key="aggr4"
            )
        with col1:
            st.selectbox(
                label=":material/filter_alt: 商品の指定方法", 
                options=["名前", "バーコード", "SKU"], 
                index=0, 
                accept_new_options=False,
                key="mthd4"
            )
        with col2:
            candidates = candidates_itm1(df_itm)
            st.selectbox(
                label=f":material/lunch_dining: {st.session_state['mthd4']}", 
                options=candidates, 
                index=0, 
                accept_new_options=False,
                key="item4"
            )
    # Data processing and visualization
    with st.container(border=True):
        if len(st.session_state["date4"]) == 2:
            df_sales_itm = process_itm1(df_itm)
            if not df_sales_itm.empty:
                stores = df_sales_itm.columns
                # Add more information from the calendar data if available
                if "df_calendar" in st.session_state:
                    df_sales_itm = pd.merge(
                        df_sales_itm, 
                        st.session_state["df_calendar"], 
                        left_on = "開始日時", 
                        right_on="date", 
                        how="left"
                    ).rename(columns={"date": "開始日時"}).set_index("開始日時")
                    # Plotly
                    fig = go.Figure()
                    # tab:orange for "西食堂" and tab:blue for "東カフェテリア"
                    colors = {"西食堂": "rgba(255, 127, 14, 0.7)", "東カフェテリア": "rgba(0, 104, 201, 0.7)"}
                    for store in stores:
                        fig.add_trace(go.Scatter(
                            x=df_sales_itm.index, 
                            y=df_sales_itm[store], 
                            mode="lines+markers", 
                            marker=dict(size=5), 
                            name=store, 
                            hovertemplate="日付: %{x|%Y-%m-%d (%a)}<br>売上: "
                                 + ("%{y}個" if st.session_state["aggr4"] == "数量" else "%{y:,}円")
                                 + "<br>学期: %{meta[0]}年度%{meta[1]}<br>講義情報: %{meta[2]}<br>その他情報: %{meta[3]}<extra></extra>", 
                            meta=df_sales_itm[["academic_year", "term", "class", "info"]].values.tolist(), 
                            hoverlabel=dict(font=dict(size=15)), 
                            line=dict(color=colors[store])
                        ))
                    st.plotly_chart(fig)
                else:
                    # Plotly
                    fig = go.Figure()
                    # tab:orange for "西食堂" and tab:blue for "東カフェテリア"
                    colors = {"西食堂": "rgba(255, 127, 14, 0.7)", "東カフェテリア": "rgba(0, 104, 201, 0.7)"}
                    for store in stores:
                        fig.add_trace(go.Scatter(
                            x=df_sales_itm.index, 
                            y=df_sales_itm[store], 
                            mode="lines+markers", 
                            marker=dict(size=5), 
                            name=store, 
                            hovertemplate="日付: %{x|%Y-%m-%d (%a)}<br>売上: "
                                 + ("%{y}個" if st.session_state["aggr4"] == "数量" else "%{y:,}円")
                                 + "<extra></extra>", 
                            hoverlabel=dict(font=dict(size=15)), 
                            line=dict(color=colors[store])
                        ))
                    st.plotly_chart(fig)
            # When nothing to show, display a sleeping hamburger
            else:
                st.image(sleeping)
    # Data
    with st.expander("データを見る", expanded=False):
        if len(st.session_state["date4"]) == 2:
            tmp = df_sales_itm.rename(columns={
                    "西食堂": f"{st.session_state['item4']}_西食堂", 
                    "東カフェテリア": f"{st.session_state['item4']}_東カフェテリア"
            })
            st.dataframe(tmp)
            st.download_button(
                label=":material/download: `.csv`でダウンロード", 
                data=convert_for_download(tmp, index_flag=True), 
                file_name=f"sales_items_{st.session_state['date4'][0]}-{st.session_state['date4'][1]}.csv", 
                mime="text/csv"
            )

# space
st.write("")

# 5. sales by department
with st.container(border=True):
    st.write("##### 各部門ごとの売上推移")
    # Options
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.date_input(
                label=":material/calendar_month: 日付", 
                value=(min_date, max_date), 
                min_value=min_date, 
                max_value=max_date, 
                key="date5"
                )
        with col2:
            st.selectbox(
                label=":material/schedule: 営業時間", 
                options=["昼（11:00～14:00）", "夜（17:30～19:30）", "昼・夜"], 
                index=0, 
                accept_new_options=False, 
                key="bsh5", 
                help="「昼・夜」を選択すると、昼営業と夜営業のデータを合算します。"
                )
        with col3:
            st.selectbox(
                label=":material/storefront: 店舗", 
                options=["西食堂", "東カフェテリア", "両方"], 
                accept_new_options=False, 
                index=0, 
                key="store5", 
                help="「両方」を選択すると、東西店舗の各グラフを重ね合わせて可視化します。"
                )
        with col4:
            st.selectbox(
                label=":material/calculate: 集計方法", 
                options=["数量", "金額"], 
                index=0, 
                accept_new_options=False,
                key="aggr5"
                )
        with col1:
            candidates = candidates_itm2(df_itm)
            st.selectbox(
                label=":material/category: 部門", 
                options=candidates, 
                index=0, 
                accept_new_options=False,
                key="dpmt5"
                )
    # Data processing and visualization
    with st.container(border=True):
        if len(st.session_state["date5"]) == 2:
            df_sales_dep = process_itm2(df_itm)
            if not df_sales_dep.empty:
                stores = df_sales_dep.columns
                # Add more information from the calendar data if available
                if "df_calendar" in st.session_state:
                    df_sales_dep = pd.merge(
                        df_sales_dep, 
                        st.session_state["df_calendar"], 
                        left_on = "開始日時", 
                        right_on="date", 
                        how="left"
                    ).rename(columns={"date": "開始日時"}).set_index("開始日時")
                    # Plotly
                    fig = go.Figure()
                    # tab:orange for "西食堂" and tab:blue for "東カフェテリア"
                    colors = {"西食堂": "rgba(255, 127, 14, 0.7)", "東カフェテリア": "rgba(0, 104, 201, 0.7)"}
                    for store in stores:
                        fig.add_trace(go.Scatter(
                            x=df_sales_dep.index, 
                            y=df_sales_dep[store], 
                            mode="lines+markers", 
                            marker=dict(size=5), 
                            name=store, 
                            hovertemplate="日付: %{x|%Y-%m-%d (%a)}<br>売上: "
                                 + ("%{y}個" if st.session_state["aggr5"] == "数量" else "%{y:,}円")
                                 + "<br>学期: %{meta[0]}年度%{meta[1]}<br>講義情報: %{meta[2]}<br>その他情報: %{meta[3]}<extra></extra>", 
                            meta=df_sales_dep[["academic_year", "term", "class", "info"]].values.tolist(), 
                            hoverlabel=dict(font=dict(size=15)), 
                            line=dict(color=colors[store])
                        ))
                    st.plotly_chart(fig)
                else:
                    # Plotly
                    fig = go.Figure()
                    # tab:orange for "西食堂" and tab:blue for "東カフェテリア"
                    colors = {"西食堂": "rgba(255, 127, 14, 0.7)", "東カフェテリア": "rgba(0, 104, 201, 0.7)"}
                    for store in stores:
                        fig.add_trace(go.Scatter(
                            x=df_sales_dep.index, 
                            y=df_sales_dep[store], 
                            mode="lines+markers", 
                            marker=dict(size=5), 
                            name=store, 
                            hovertemplate="日付: %{x|%Y-%m-%d (%a)}<br>売上: "
                                 + ("%{y}個" if st.session_state["aggr5"] == "数量" else "%{y:,}円")
                                 + "<extra></extra>", 
                            hoverlabel=dict(font=dict(size=15)), 
                            line=dict(color=colors[store])
                        ))
                    st.plotly_chart(fig)
            else:
                st.image(sleeping)
    # Data
    with st.expander("データを見る", expanded=False):
        if len(st.session_state["date5"]) == 2:
            tmp = df_sales_dep.rename(columns={
                    "西食堂": f"{st.session_state['dpmt5']}_西食堂", 
                    "東カフェテリア": f"{st.session_state['dpmt5']}_東カフェテリア"
            })
            st.dataframe(tmp)
            st.download_button(
                label=":material/download: `.csv`でダウンロード", 
                data=convert_for_download(df_sales_dep, index_flag=False), 
                file_name=f"sales_department_{st.session_state['date5'][0]}-{st.session_state['date5'][1]}.csv", 
                mime="text/csv"
            )

# space
st.write("")

# 6. syllabus data
with st.container(border=True):
    st.write("##### 曜日ごとの対面講義履修者数")
    # When syllabus data is not available
    if "df_syllabus_west" not in st.session_state or "df_syllabus_east" not in st.session_state:
        with st.container(border=True):
            st.image(sleeping_no_syllabus)
    # When syllabus data is available
    else:
        # Options
        with st.container(border=True):
            st.multiselect(
                label=":material/school: 時限", 
                options=["1限", "2限", "3限", "4限", "5限"], 
                default=["1限", "2限", "3限", "4限", "5限"], 
                key="class_period"
            )
            year_candidates = candidates_syl()
            st.multiselect(
                label=":material/event: 年度", 
                options=year_candidates, 
                default=year_candidates[0], 
                max_selections=3, 
                key="year", 
                help="最大3つまで選択できます。"
            )
        # Data processing and visualization
        with st.container(border=True):
            df_syl_west, df_syl_east = process_syllabus()
            if not df_syl_west.empty or not df_syl_east.empty:
                years = [y[:4] for y in st.session_state["year"]]
                terms = ["SPR", "SMR", "AUT", "WTR"]
                titles = ["春学期", "夏学期", "秋学期", "冬学期"]
                colors = [
                    [(255, 127, 14), (255, 172, 100), (255, 211, 172)], 
                    [(0, 104, 201), (107, 176, 241), (181, 219, 255)]
                ]
                fig = make_subplots(
                    rows=2, cols=4, 
                    subplot_titles=["春学期", "夏学期", "秋学期", "冬学期", "", "", "", ""], 
                    shared_yaxes=True
                )
                # Plotly
                for n_row, syl in enumerate([df_syl_west, df_syl_east]):
                    for j, year in enumerate(years):
                        for i, term in enumerate(terms):
                            try:
                                week = syl.loc[:, year + term]
                                fig.add_trace(go.Bar(
                                    x=week.index, 
                                    y=week.values, 
                                    marker=dict(color=f"rgba({colors[n_row][j][0]}, {colors[n_row][j][1]}, {colors[n_row][j][2]}, 1)"), 
                                    hovertemplate="対面講義履修者数: %{y:,}人<extra></extra>", 
                                    name=year + "年度", 
                                    showlegend=True if i == 0 else False, 
                                    hoverlabel=dict(font=dict(size=15))
                                ), row=n_row+1, col=i+1)
                            except KeyError:
                                fig.add_trace(go.Bar(
                                    x=["月", "火", "水", "木", "金"], 
                                    y=[0, 0, 0, 0, 0], 
                                    marker=dict(color=f"rgba({colors[n_row][j][0]}, {colors[n_row][j][1]}, {colors[n_row][j][2]}, 1)"), 
                                    hovertemplate="データなし<extra></extra>", 
                                    name=year + "年度", 
                                    showlegend=True if i == 0 else False, 
                                    hoverlabel=dict(font=dict(size=15))
                                ), row=n_row+1, col=i+1)
                fig.update_layout(barmode="group")
                fig.update_yaxes(title_text="西キャンパス", row=1, col=1)
                fig.update_yaxes(title_text="東キャンパス", row=2, col=1)
                st.plotly_chart(fig)
            else:
                st.image(sleeping)
        # Data
        with st.expander("データを見る", expanded=False):
            tab1, tab2 = st.tabs(["西キャンパス", "東キャンパス"])
            with tab1:
                st.dataframe(df_syl_west)
                st.download_button(
                    label=":material/download: `.csv`でダウンロード", 
                    data=convert_for_download(df_syl_west, index_flag=True), 
                    file_name=f"syllabus_west.csv", 
                    mime="text/csv"
                )
            with tab2:
                st.dataframe(df_syl_east)
                st.download_button(
                    label=":material/download: `.csv`でダウンロード", 
                    data=convert_for_download(df_syl_east, index_flag=True), 
                    file_name=f"syllabus_east.csv", 
                    mime="text/csv"
                )

