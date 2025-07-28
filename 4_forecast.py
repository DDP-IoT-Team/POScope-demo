import streamlit as st
from PIL import Image
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.model_selection import train_test_split
from sklearn.metrics import root_mean_squared_error, mean_absolute_percentage_error
from sklearn.linear_model import LinearRegression


#-----------------------------------------Settings-----------------------------------------

# Load images
favicon = Image.open("static/favicon.ico")
sleeping = Image.open("static/sleeping_hamburger.png")
sleeping_no_training_data = Image.open("static/sleeping_hamburger_no_training_data.png")

# Page configuration
st.set_page_config(
    page_title="予測", 
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

#------------------Check files------------------

def check_uploaded_files() -> list[str]:
    """
    Check if the required files are uploaded.\\
    Return a list of not uploaded files.
    """
    not_uploaded = []
    if "df_customers" not in st.session_state:
        not_uploaded.append("POSデータ")
    if "df_syllabus_west" not in st.session_state or "df_syllabus_east" not in st.session_state:
        not_uploaded.append("履修者数データ")
    if "df_calendar" not in st.session_state:
        not_uploaded.append("カレンダー形式データ")
    return not_uploaded


def check_options(store: str):
    """
    Check if the data is available for the selected options.\\
    Return True if the data is available, otherwise False.
    """
    if store == "西食堂":
        if "df_syllabus_west" not in st.session_state:
            return False
    elif store == "東カフェテリア":
        if "df_syllabus_east" not in st.session_state:
            return False
    return True


#----------------Process POS data----------------

def process_pos(df_cus: pd.DataFrame):
    """
    Filter the DataFrame based on the selected options.\\
    Return an empty DataFrame if no valid data is found.
    """
    # Load option from session state
    store = st.session_state["forecast_store"]
    # Filter by store
    df_cus = df_cus[df_cus["アカウント名"] == store]
    # Filter by business hours
    df_cus = df_cus.set_index("開始日時")
    df_cus = df_cus.between_time("11:00", "14:00")
    df_cus = df_cus.reset_index(drop=False)
    if df_cus.empty:
        return pd.DataFrame()
    # Resample the DataFrame by day
    df_cus = df_cus.resample("1D", on="開始日時")["客数"].sum()
    return df_cus


#-------------Process calendar data-------------

def get_nweek(df_cal: pd.DataFrame) -> list:
    """
    Calculate the number of weeks since the first Monday of the term and return it as a list.
    """
    r, _ = df_cal.shape
    current_term = ""
    first_mon_date = None
    nweeks = []
    daynames = ["MON", "TUE", "WED", "THU", "FRI"]
    for i in range(r):
        term = df_cal.loc[i, "term"]
        class_info = df_cal.loc[i, "class"]
        _date = df_cal.loc[i, "date"]
        dayname = _date.day_name()[:3].upper()
        if term in ["SPR", "SMR", "AUT", "WTR", "SMRINT", "WTRINT1to3", "WTRINT4"] and class_info != "NoClass":
            if current_term != term:
                # not change first_mon_date when SPR->SMR or AUT->WTR
                if term == "SMR" or term == "WTR":
                    current_term = term
                else:
                    current_term = term
                    first_mon_date = _date - pd.Timedelta(days=daynames.index(dayname))
            nweeks.append((_date - first_mon_date).days // 7 + 1)
        else:
            nweeks.append(float("nan"))
    return nweeks


def get_holiday_dummy(df_cal: pd.DataFrame) -> list:
    """
    Get holiday dummy variable and return it as a list.
    """
    r, _ = df_cal.shape
    holidays = []
    for i in range(r):
        info = df_cal.loc[i, "info"]
        if pd.notna(info) and "Holiday" in info:
            holidays.append(1)
        else:
            holidays.append(0)
    return holidays


def get_replaced_dummy(df_cal: pd.DataFrame) -> list:
    """
    Get replaced dummy variable and return it as a list.
    """
    r, _ = df_cal.shape
    replaced = []
    for i in range(r):
        info = df_cal.loc[i, "info"]
        if pd.notna(info) and "Replaced" in info:
            replaced.append(1)
        else:
            replaced.append(0)
    return replaced


def get_first_week_dummy(df_cal: pd.DataFrame) -> list:
    """
    Get first week dummy variable and return it as a list.
    """
    r, _ = df_cal.shape
    first_week = []
    for i in range(r):
        nweek = df_cal.loc[i, "nweek"]
        if nweek == 1:
            first_week.append(1)
        else:
            first_week.append(0)
    return first_week


def get_last_week_dummy(df_cal: pd.DataFrame) -> list:
    """
    Get last week dummy variable and return it as a list.\\
    Note that this function only works when the maximum number of week is 15.\\
    To cope with exceptions, more complicated logic is needed (future implementation).
    """
    r, _ = df_cal.shape
    last_week = []
    for i in range(r):
        nweek = df_cal.loc[i, "nweek"]
        if nweek == 15:
            last_week.append(1)
        else:
            last_week.append(0)
    return last_week


def process_calendar(df_cal: pd.DataFrame):
    """
    Process calendar data.
    """
    df_cal["nweek"] = get_nweek(df_cal)
    df_cal["holiday"] = get_holiday_dummy(df_cal)
    df_cal["replaced"] = get_replaced_dummy(df_cal)
    df_cal["first_week"] = get_first_week_dummy(df_cal)
    df_cal["last_week"] = get_last_week_dummy(df_cal)
    return df_cal


#-------------gather all dataframes-------------

def concatenate_data(df_cus: pd.DataFrame, df_cal: pd.DataFrame, df_syl: pd.DataFrame) -> pd.DataFrame:
    """
    Concatenate customer data, calendar data, and syllabus data into a single DataFrame.\\
    If the customer data is empty, return an empty DataFrame.
    """
    if df_cus.empty:
        return pd.DataFrame()
    # Assign syllabus data to the calendar data
    r, _ = df_cal.shape
    jp_daynames = ["月", "火", "水", "木", "金"]
    en_daynames = ["MON", "TUE", "WED", "THU", "FRI"]
    main_terms = ["SPR", "SMR", "AUT", "WTR"]
    syllabus = []
    for i in range(r):
        academic_year = df_cal.loc[i, "academic_year"]
        term = df_cal.loc[i, "term"]
        class_dayname = df_cal.loc[i, "class"]
        if term in main_terms and class_dayname in en_daynames:
            jp_dayname = jp_daynames[en_daynames.index(class_dayname)]
            try:
                syl = df_syl.loc[(jp_dayname, [1, 2, 3]), str(academic_year)+term].sum()
            except KeyError:
                syl = float("nan")
        else:
            syl = float("nan")
        syllabus.append(syl)
    df_cal["syllabus"] = syllabus
    # Gather all DataFrames
    df_main = pd.merge(
        df_cus, df_cal, how="outer", 
        left_index=True, right_on="date"
    ).set_index("date")
    return df_main


def split_data(df_main: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split the DataFrame into training and prediction sets.
    """
    yX_tr = df_main[
        (df_main["客数"].notna()) & 
        (df_main["客数"] > 0) & 
        (df_main["class"].isin(["MON", "TUE", "WED", "THU", "FRI"])) & 
        (df_main["syllabus"].notna())
    ]
    X_pred = df_main[
        (df_main.index > yX_tr.index.max()) & 
        (df_main["class"].isin(["MON", "TUE", "WED", "THU", "FRI"])) & 
        (df_main["syllabus"].notna())
    ][["syllabus", "nweek", "holiday", "replaced", "first_week", "last_week"]]
    return yX_tr, X_pred


def get_train_data(yX: pd.DataFrame) -> tuple:
    """
    Split the training data into training and validation sets.
    """
    y = yX["客数"]
    X = yX[["syllabus", "nweek", "holiday", "replaced", "first_week", "last_week"]]
    X_tr, X_va, y_tr, y_va = train_test_split(X, y, test_size=0.2, shuffle=False)
    return X_tr, X_va, y_tr, y_va


def train_model(y, X):
    """
    Train a linear regression model using the training data.
    """
    model = LinearRegression()
    model.fit(X, y)
    return model


def callback_on_change():
    """
    Callback function.
    """
    st.session_state["model_trained"] = False


def convert_for_download(df: pd.DataFrame, index_flag: bool) -> bytes:
    """
    Convert the DataFrame to a CSV format encoded in Shift-JIS for download.\\
    The `index` parameter determines whether to include the index in the CSV.\\
    The option of `encoding` in `pd.DataFrame.to_csv()` is not supported when `path_or_buf` is `None`.
    """
    return df.to_csv(index=index_flag).encode("shift-jis")


#-----------------------------------------Contents-----------------------------------------

# logo in the sidebar
st.logo(favicon, size="large")

st.header("1日当たりの客数予測")

# Check if the required files are uploaded
not_uploaded_files = check_uploaded_files()
if not_uploaded_files:
    st.error(
        f"""
        :material/error: 以下のファイルがアップロードされていません。
        {" - POSデータ" if "POSデータ" in not_uploaded_files else ""}
        {" - 履修者数データ" if "履修者数データ" in not_uploaded_files else ""}
        {" - カレンダー形式データ" if "カレンダー形式データ" in not_uploaded_files else ""}
        """
    )
    st.stop() # Stop execution

# Initialize session state
st.session_state["model_trained"] = False

with st.container(border=True):
    st.write("##### :material/model_training: モデル構築・予測")
    # Options and a button
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.selectbox(
                label=":material/storefront: 店舗", 
                options=["西食堂", "東カフェテリア"], 
                index=0, 
                key="forecast_store", 
                on_change=callback_on_change
            )
        with col2:
            st.selectbox(
                label=":material/schedule: 営業時間", 
                options=["昼（11:00～14:00）"], 
                index=0, 
                key="forecast_bsh", 
                help="夜営業については、一部の会計データがPOSデータに記録されていないため予測できません。"
            )
        with col1:
            st.button(
                label="学習・予測する", 
                key="train_predict_button", 
                help="予測可能な範囲がない場合、学習のみ実行されます。"
            )
    # Data preparation
    with st.container(border=True):
        # Check if the data is available for the selected options
        if not check_options(st.session_state["forecast_store"]):
            st.image(sleeping)
            st.stop()
        # When all data is ready, load them from session state
        df_cus: pd.DataFrame = st.session_state["df_customers"].copy()
        df_cal: pd.DataFrame = st.session_state["df_calendar"].copy()
        if st.session_state["forecast_store"] == "西食堂":
            df_syl: pd.DataFrame = st.session_state["df_syllabus_west"].copy()
        else:
            df_syl: pd.DataFrame = st.session_state["df_syllabus_east"].copy()     
        # Process POS data
        df_cus = process_pos(df_cus)
        # Process calendar data
        df_cal = process_calendar(df_cal)
        # Gather all DataFrames
        df_main = concatenate_data(df_cus, df_cal, df_syl)
        if not df_main.empty:
            # Split data into training and prediction sets
            yX_tr, X_for_pred = split_data(df_main)
            if yX_tr.empty:
                st.image(sleeping_no_training_data)
                st.stop() # Stop execution 
        else:
            st.image(sleeping)
    # Train model
    if st.session_state.get("train_predict_button", False):
        with st.spinner("モデルを学習中...", show_time=True):
            # Split data into training and validation sets
            x_tr, x_va, y_tr, y_va = get_train_data(yX_tr)
            # Train the model
            model = train_model(np.log(y_tr), x_tr)
            # Predict
            y_tr_pred = np.exp(model.predict(x_tr))
            y_va_pred = np.exp(model.predict(x_va))
            y_pred = y_tr_pred.tolist() + y_va_pred.tolist()
            if not X_for_pred.empty:
                y_pred_future = np.exp(model.predict(X_for_pred)).tolist()
            else:
                y_pred_future = []
            # Calculate evaluation metrics
            tr_rmse = root_mean_squared_error(y_tr, y_tr_pred)
            va_rmse = root_mean_squared_error(y_va, y_va_pred)
            tr_mape = mean_absolute_percentage_error(y_tr, y_tr_pred)
            va_mape = mean_absolute_percentage_error(y_va, y_va_pred)
            # Set session state variable
            st.session_state["model_trained"] = True
    # Plot graph
    with st.container(border=True):
        colors = {"西食堂": "rgba(255, 127, 14, 0.7)", "東カフェテリア": "rgba(0, 104, 201, 0.7)"}
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=yX_tr.index, 
            y=yX_tr["客数"], 
            name="実際の客数", 
            mode="lines+markers", 
            hovertemplate="日付: %{x|%Y-%m-%d (%a)}<br>客数: %{y:,}人<br>学期: %{meta[0]}年度%{meta[1]}<br>講義情報: %{meta[2]}<br>その他情報: %{meta[3]}<extra></extra>",
            hoverlabel=dict(font=dict(size=15)), 
            meta=yX_tr[["academic_year", "term", "class", "info"]].values.tolist(), 
            marker=dict(size=5), 
            line=dict(color=colors[st.session_state["forecast_store"]])
        ))
        # Add training range rectangle
        fig.add_shape(
            type="rect",
            xref="x", yref="paper",  
            x0=yX_tr.index.min(), x1=yX_tr.index.max(), 
            y0=0, y1=1, 
            fillcolor="rgba(237, 168, 168, 0.2)", 
            line_width=0, 
            label=dict(text="学習範囲", textposition="top center", font=dict(size=15))
        )
        # Add predictable range rectangle
        if not X_for_pred.empty:
            fig.add_shape(
                type="rect",
                xref="x", yref="paper",  
                x0=X_for_pred.index.min(), x1= X_for_pred.index.max(), 
                y0=0, y1=1, 
                fillcolor="LightGreen", 
                opacity=0.2, 
                line_width=0, 
                label=dict(text="予測範囲", textposition="top center", font=dict(size=15))
            )
        # Add predicted values
        if st.session_state.get("model_trained", False):
            fig.add_trace(go.Scatter(
                x=yX_tr.index, 
                y=y_pred, 
                mode="lines+markers", 
                marker=dict(size=5), 
                line=dict(color="rgba(0, 0, 0, 0.3)"), 
                hovertemplate="日付: %{x|%Y-%m-%d (%a)}<br>予測値: %{y:,.1f}人<extra></extra>", 
                hoverlabel=dict(font=dict(size=15)), 
                name="予測値"
            ))
        # Add future predicted values
        if not X_for_pred.empty and st.session_state.get("model_trained", False):
            fig.add_trace(go.Scatter(
                x=X_for_pred.index, 
                y=y_pred_future, 
                mode="lines+markers", 
                marker=dict(size=5), 
                line=dict(color="rgba(0, 0, 0, 0.3)"), 
                hovertemplate="日付: %{x|%Y-%m-%d (%a)}<br>予測値: %{y:,.1f}人<extra></extra>", 
                hoverlabel=dict(font=dict(size=15)), 
                showlegend=False
            ))
        st.plotly_chart(fig)
    # Metrics
    if st.session_state.get("model_trained", False):
        st.info(
            f"""
            :material/check_circle: 学習済みモデルの評価指標
             - 学習データにおける平均的な予測誤差：{tr_mape:.1%}（{tr_rmse:.1f}人）
             - 検証データにおける平均的な予測誤差：{va_mape:.1%}（{va_rmse:.1f}人）
            """
        )
    else:
        st.info(
            """
            :material/check_circle: 学習済みモデルの評価指標
             - まだモデルが学習されていません。
            """
        )
    # Data
    with st.expander("データを見る", expanded=False):
        if st.session_state.get("model_trained", False):
            if st.session_state["forecast_store"] == "西食堂":
                store_name = "west"
            else:
                store_name = "east"
            if not X_for_pred.empty:
                df_pred = pd.DataFrame(
                    index=yX_tr.index.tolist() + X_for_pred.index.tolist(), 
                    data={
                        "実際の客数": yX_tr["客数"].tolist() + [float("nan")] * len(X_for_pred),
                        "予測値": y_pred + y_pred_future
                    }
                ).rename_axis(index="日付")
                st.dataframe(df_pred)
                st.download_button(
                        label=":material/download: `.csv`でダウンロード", 
                        data=convert_for_download(df_pred, index_flag=True), 
                        file_name=f"pred_{store_name}_{yX_tr.index.min().strftime("%Y-%m-%d")}-{X_for_pred.index.max().strftime("%Y-%m-%d")}.csv", 
                        mime="text/csv"
                    )
            else:
                df_pred = pd.DataFrame(
                    index=yX_tr.index, 
                    data={
                        "実際の客数": yX_tr["客数"], 
                        "予測値": y_pred
                    }
                ).rename_axis(index="日付")
                st.dataframe(df_pred)
                st.download_button(
                        label=":material/download: `.csv`でダウンロード", 
                        data=convert_for_download(df_pred, index_flag=True), 
                        file_name=f"pred_{store_name}_{yX_tr.index.min().strftime("%Y-%m-%d")}-{yX_tr.index.max().strftime("%Y-%m-%d")}.csv", 
                        mime="text/csv"
                    )

