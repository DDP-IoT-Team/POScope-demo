import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
import pandas as pd
from io import BytesIO
import zipfile
from PIL import Image
import numpy as np


#-----------------------------------------Settings-----------------------------------------

# Load an image
favicon = Image.open("static/favicon.ico")

# Page configuration
st.set_page_config(
    page_title="アップロード", 
    layout="centered",
    initial_sidebar_state="expanded", 
    page_icon=favicon, 
    menu_items={
        'Get help': st.secrets["documentation"]["notion_site"], # Documentation
        'Report a bug': st.secrets["google_forms"]["report_a_bug"], # Google Forms
        'About': "#### POScope \nv1.0.0"
    }
)


#-----------------------------------------Functions-----------------------------------------

# @st.cache_data(show_spinner=False)
# Info bar "Running function()" in the spinner
# https://discuss.streamlit.io/t/info-bar-running-function-appearing-unnecessarily-for-cached-function/6015


#-------------universal-------------

def button_controller(file_uploader_key: str) -> bool:
    """
    Return `True` (disable button: "使用するデータを決定する") if files are not uploaded or empty.\\
    Otherwise, return `False` (enable button).
    """
    # When no files have ever been uploaded
    if file_uploader_key not in st.session_state:
        return True # disable button
    else:
        # When the session state "file_uploader_key" stores something other than empty or empty list
        if st.session_state[file_uploader_key]:
            return False # enable button
        # When the session state "file_uploader_key" exits but is empty or empty list
        else:
            return True # disable button


#----------------POS----------------

def when_zip_pos_changed() -> None:
    """
    Callback function for `st.file_uploader()` for POS data.\\
    When a different set of files is uploaded, set the session state of `zip_pos_changed` to `True`.\\
    This function is used to control the success message.\\
    The message is shown only when the user has not changed the uploaded files since the last successful upload.
    """
    st.session_state["zip_pos_changed"] = True


def load_uploaded_zip_pos() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load the uploaded zip files and return DataFrames of checkouts, items, and payments.\\
    Each file of checktouts,csv, items.csv, and payments.csv is concatenated into a single DataFrame respectively.
    """
    # load zip files from session state
    zip_files: list[UploadedFile] = st.session_state["uploaded_zip_pos"]
    # Initialize empty DataFrames
    df_checkouts = pd.DataFrame()
    df_items = pd.DataFrame()
    df_payments = pd.DataFrame()
    # checkouts.csv, items.csv, payments.csv, and other trivial files in zip_file
    for zip_file in zip_files:
        # Streamlit's UploadedFile is a subclass of BytesIO, so it can be read directly
        with zipfile.ZipFile(zip_file) as zf:
            # Load the necessary files: checkouts.csv, items.csv, and payments.csv
            for file in zf.namelist():
                if file == "checkouts.csv":
                    with zf.open(file) as f:
                        tmp = pd.read_csv(BytesIO(f.read()), encoding="shift-jis")
                        # Concatenate with empty or all-NA DataFrame will be deprecated, 
                        # so if the loaded DataFrame is empty or all-NA, skip it.
                        if tmp.empty or tmp.isna().all().all():
                            continue
                        df_checkouts = pd.concat([df_checkouts, tmp], axis="index")
                elif file == "items.csv":
                    with zf.open(file) as f:
                        tmp = pd.read_csv(BytesIO(f.read()), encoding="shift-jis")
                        # Concatenate with empty or all-NA DataFrame will be deprecated, 
                        # so if the loaded DataFrame is empty or all-NA, skip it.
                        if tmp.empty or tmp.isna().all().all():
                            continue
                        df_items = pd.concat([df_items, tmp], axis="index")
                elif file == "payments.csv":
                    with zf.open(file) as f:
                        tmp = pd.read_csv(BytesIO(f.read()), encoding="shift-jis")
                        # Concatenate with empty or all-NA DataFrame will be deprecated, 
                        # so if the loaded DataFrame is empty or all-NA, skip it.
                        if tmp.empty or tmp.isna().all().all():
                            continue
                        df_payments = pd.concat([df_payments, tmp], axis="index")
    return df_checkouts, df_items, df_payments


def cleanup_pos(df_checkouts: pd.DataFrame, df_items: pd.DataFrame, df_payments: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Return cleanuped POS data.
    """
    # Filter columns
    df_checkouts = df_checkouts[
        ["アカウント名", "会計ID", "開始日時", "会計日時", "削除日時", "金額", "客数"]
    ]
    df_items = df_items[
        ["会計ID", "SKU", "バーコード",  "名前", "数量", "金額", "部門"]
    ]
    df_payments = df_payments[["会計ID", "支払い方法"]]

    # Drop duplicates
    df_checkouts = df_checkouts.drop_duplicates()
    df_items = df_items.drop_duplicates()
    df_payments = df_payments.drop_duplicates()

    # Delete cancelled records
    # Non-NA value in "削除日時" means that the record is cancelled
    cancelled = df_checkouts[["会計ID", "削除日時"]]
    df_checkouts = df_checkouts[df_checkouts["削除日時"].isna()].drop(columns=["削除日時"])
    df_items = pd.merge(df_items, cancelled, on="会計ID", how="left")
    df_items = df_items[df_items["削除日時"].isna()].drop(columns=["削除日時"])
    df_payments = pd.merge(df_payments, cancelled, on="会計ID", how="left")
    df_payments = df_payments[df_payments["削除日時"].isna()].drop(columns=["削除日時"])

    # Empty entries in "支払い方法" are change of payment, so remove them
    df_payments = df_payments[df_payments["支払い方法"].notna()]

    # A negative value in "数量" seems to indicate that the transaction has been cancelled, so remove those records.
    # While there seems no record with zero value in "数量", remove those records as well.
    invalid_cnt = df_items.query('数量 <= 0')["会計ID"].to_list()
    df_checkouts = df_checkouts[~df_checkouts["会計ID"].isin(invalid_cnt)]
    df_items = df_items[~df_items["会計ID"].isin(invalid_cnt)]
    df_payments = df_payments[~df_payments["会計ID"].isin(invalid_cnt)]

    # Change the account names to more straightforward ones
    df_checkouts = df_checkouts.replace({"アカウント名": {"ub396203": "西食堂", "ub396207": "東カフェテリア"}})

    # One-hot encoding on "支払い方法" to cope with multiple payment methods in a single checkout.
    df_payments = pd.get_dummies(df_payments, columns=["支払い方法"], 
                                 prefix="", prefix_sep="", dtype="int")
    df_payments = df_payments.groupby("会計ID").sum().reset_index()

    # Modigy the data types
    df_checkouts["開始日時"] = pd.to_datetime(df_checkouts["開始日時"]).map(lambda x: x.tz_localize(None))
    df_checkouts["会計日時"] = pd.to_datetime(df_checkouts["会計日時"]).map(lambda x: x.tz_localize(None))
    df_checkouts = df_checkouts.astype({"会計ID": "str", "金額": "int", "客数": "int"})
    df_items = df_items.astype({"会計ID": "str", "SKU": "str", "バーコード": "str", 
                                "名前": "str", "数量": "int", "金額": "int", "部門": "str"})
    df_payments = df_payments.astype({"会計ID": "str"})

    # Merge the DataFrames
    df_customers = pd.merge(df_checkouts, df_payments, on="会計ID", how="inner")
    df_items = pd.merge(df_customers[["アカウント名", "会計ID", "開始日時", "会計日時"]], df_items, on="会計ID", how="inner")

    return df_customers, df_items


def set_session_state_pos(df_cus: pd.DataFrame, df_itm: pd.DataFrame) -> None:
    """
    Set the session states related with POS data.
    """
    # main DataFrames
    st.session_state["df_customers"] = df_cus
    st.session_state["df_items"] = df_itm

    # These session states are used to show information about the uploaded POS data
    st.session_state["west_date_min"] = df_cus.query('アカウント名 == "西食堂"')["会計日時"].min()
    st.session_state["east_date_min"] = df_cus.query('アカウント名 == "東カフェテリア"')["会計日時"].min()
    st.session_state["west_date_max"] = df_cus.query('アカウント名 == "西食堂"')["会計日時"].max()
    st.session_state["east_date_max"] = df_cus.query('アカウント名 == "東カフェテリア"')["会計日時"].max()
    
    stores = df_cus["アカウント名"].unique().tolist()
    if "西食堂" in stores:
        if "東カフェテリア" in stores:
            st.session_state["west_pos"] = True
            st.session_state["east_pos"] = True
            st.session_state["min_date"] = min(
                st.session_state["west_date_min"], 
                st.session_state["east_date_min"]
            )
            st.session_state["max_date"] = max(
                st.session_state["west_date_max"], 
                st.session_state["east_date_max"]
            )
        else:
            st.session_state["west_pos"] = True
            st.session_state["east_pos"] = False
            st.session_state["min_date"] = st.session_state["west_date_min"]
            st.session_state["max_date"] = st.session_state["west_date_max"]
    else:
        if "東カフェテリア" in stores:
            st.session_state["west_pos"] = False
            st.session_state["east_pos"] = True
            st.session_state["min_date"] = st.session_state["east_date_min"]
            st.session_state["max_date"] = st.session_state["east_date_max"]


def get_uploaded_pos_info() -> list[str]:
    """
    Return information about the uploaded POS data.
    """
    messages = []
    if "df_customers" in st.session_state and st.session_state["west_pos"]:
        messages.append(
            f"{st.session_state['west_date_min'].strftime('%Y/%m/%d')}～{st.session_state['west_date_max'].strftime('%Y/%m/%d')}"
        )
    else:
        messages.append("データはありません。")
    if "df_customers" in st.session_state and st.session_state["east_pos"]:
        messages.append(
            f"{st.session_state['east_date_min'].strftime('%Y/%m/%d')}～{st.session_state['east_date_max'].strftime('%Y/%m/%d')}"
        )
    else:
        messages.append("データはありません。")
    return messages


#--------------syllabus--------------

def when_syllabus_changed() -> None:
    """
    Callback function for `st.file_uploader()` for syllabus data.\\
    When a different set of files is uploaded, set the session state of `syllabus_changed` to `True`.\\
    This function is used to control the success message.\\
    The message is shown only when the user has not changed the uploaded files since the last successful upload.
    """
    st.session_state["syllabus_changed"] = True


def load_uploaded_syllabus() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load the uploaded xlsx file of syllabus data and return DataFrames.
    """
    # Load the xlsx file from session state
    file: UploadedFile = st.session_state["uploaded_syllabus"]
    # Read xlsx file
    df_syllabus_west = pd.read_excel(file, sheet_name="west", index_col=[0, 1])
    df_syllabus_east = pd.read_excel(file, sheet_name="east", index_col=[0, 1])
    return df_syllabus_west, df_syllabus_east


def set_session_state_syllabus(df_slb_west: pd.DataFrame, df_slb_east: pd.DataFrame) -> None:
    """
    Set the session states related with syllabus data.
    """
    st.session_state["df_syllabus_west"] = df_slb_west
    st.session_state["df_syllabus_east"] = df_slb_east

    terms = ["SPR", "SMR", "AUT", "WTR"]
    west_cols = sorted([[int(col[:4]), terms.index(col[4:]), col] for col in df_slb_west.columns])
    east_cols = sorted([[int(col[:4]), terms.index(col[4:]), col] for col in df_slb_east.columns])
    st.session_state["west_syllabus_range"] = [west_cols[0][2], west_cols[-1][2]]
    st.session_state["east_syllabus_range"] = [east_cols[0][2], east_cols[-1][2]]


def get_uploaded_syllabus_info() -> list[str]:
    """
    Return information about the uploaded syllabus data.
    """
    messages = []
    if "df_syllabus_west" in st.session_state:
        messages.append(
            f"{st.session_state['west_syllabus_range'][0]}～{st.session_state['west_syllabus_range'][1]}"
        )
    else:
        messages.append("データはありません。")
    if "df_syllabus_east" in st.session_state:
        messages.append(
            f"{st.session_state['east_syllabus_range'][0]}～{st.session_state['east_syllabus_range'][1]}"
        )
    else:
        messages.append("データはありません。")
    return messages


#--------------calendar--------------

def when_calendar_changed() -> None:
    """
    Callback function for `st.file_uploader()` for calendar-format data.\\
    When a different set of files is uploaded, set the session state of `calendar_changed` to `True`.\\
    This function is used to control the success message.\\
    The message is shown only when the user has not changed the uploaded files since the last successful upload.
    """
    st.session_state["calendar_changed"] = True


def load_uploaded_calendar() -> pd.DataFrame:
    """
    Load the uploaded xlsx file of calendar data and return a DataFrame.\\
    If the file format is not correct, return an empty DataFrame.
    """
    # Load the xlsx file from session state
    file: UploadedFile = st.session_state["uploaded_calendar"]
    cols = ["date", "academic_year", "term", "class", "info"]
    df_cal = pd.read_excel(file)
    for col in df_cal.columns:
        if col not in cols:
            return pd.DataFrame()
    return df_cal


def set_session_state_calendar(df_cal: pd.DataFrame) -> None:
    """
    Set the session states related with calendar data.
    """
    st.session_state["df_calendar"] = df_cal
    st.session_state["calendar_range"] = [
        df_cal["date"].min().strftime("%Y/%m/%d"), 
        df_cal["date"].max().strftime("%Y/%m/%d")
    ]


def get_uploaded_calendar_info() -> str:
    """
    Return information about the uploaded calendar data.
    """
    if "df_calendar" in st.session_state:
        return f"{st.session_state['calendar_range'][0]}～{st.session_state['calendar_range'][1]}"
    else:
        return "データはありません。"


#-----------------------------------------Contents-----------------------------------------

# Initialize session states
if "zip_pos_changed" not in st.session_state:
    st.session_state["zip_pos_changed"] = False
if "syllabus_changed" not in st.session_state:
    st.session_state["syllabus_changed"] = False
if "calendar_changed" not in st.session_state:
    st.session_state["calendar_changed"] = False

# logo in the sidebar
st.logo(favicon, size="large")

st.header("データアップロード")

# Upload POS data
with st.container(border=True):
    st.subheader(":material/point_of_sale: POSデータ")
    st.file_uploader(
        label="ユビレジからエクスポートした`ZIP`ファイル（`CSV`形式）をアップロードしてください。", 
        type=["zip"], 
        accept_multiple_files=True, 
        key="uploaded_zip_pos", 
        on_change=when_zip_pos_changed
    )
    if st.button(label="使用するデータを決定する", key="button_pos", disabled=button_controller("uploaded_zip_pos")):
        with st.spinner("データを読み込んでいます...", show_time=True):
            try:
                df_checkouts, df_items, df_payments = load_uploaded_zip_pos()
                if df_checkouts.shape[0] > 0:
                    df_cus, df_itm = cleanup_pos(df_checkouts, df_items, df_payments)
                    set_session_state_pos(df_cus, df_itm)
                    st.session_state["zip_pos_changed"] = False
                else:
                    st.error(
                        """
                        データの読み込みに失敗しました。\\
                        アップロードされたファイルには有効なデータが含まれていません。
                        """
                    )
                    st.session_state["zip_pos_changed"] = False
            except:
                st.error(
                    """
                    データの読み込みに失敗しました。\\
                    データ形式が正しくない可能性があります。
                    """
                )
    # Information about the uploaded POS data
    messages = get_uploaded_pos_info()
    st.info(
        f"""
        :material/check_circle: アップロードされているPOSデータ
         - 西食堂：{messages[0]}
         - 東カフェテリア：{messages[1]}
        """
    )

# space
st.write("")

# Upload syllabus data
with st.container(border=True):
    st.subheader(":material/school: 履修者数データ")
    st.file_uploader(
        label="対面講義履修者数のデータを含む`XLSX`ファイルをアップロードしてください。", 
        type=["xlsx"], 
        accept_multiple_files=False, 
        key="uploaded_syllabus", 
        on_change=when_syllabus_changed
    )
    if st.button(label="使用するデータを決定する", key="button_syllabus", disabled=button_controller("uploaded_syllabus")):
        with st.spinner("データを読み込んでいます...", show_time=True):
            try:
                df_slb_west, df_slb_east = load_uploaded_syllabus()
                if not df_slb_west.empty and not df_slb_east.empty:
                    set_session_state_syllabus(df_slb_west, df_slb_east)
                    st.session_state["syllabus_changed"] = False
                else:
                    st.error(
                        """
                        データの読み込みに失敗しました。\\
                        アップロードしたファイルに有効なデータが含まれていることを確認してください。
                        """
                    )
                    st.session_state["syllabus_changed"] = False
            except:
                st.error(
                    """
                    データの読み込みに失敗しました。\\
                    データ形式が正しくない可能性があります。
                    """
                )
    # Information about the uploaded POS data
    messages = get_uploaded_syllabus_info()
    st.info(
        f"""
        :material/check_circle: アップロードされている履修者数データ
         - 西キャンパス：{messages[0]}
         - 東キャンパス：{messages[1]}
        """
    )
    # About file format
    with st.expander(":material/warning: （重要）データの形式について"):
        st.markdown(
            """
            東西キャンパスにおける、各年度・学期・曜日・時限の対面講義履修者数が1つにまとめられた
            `XLSX`ファイルをアップロードする必要があります。
            形式が正しくない場合、ファイルを読み込むことができませんのでご注意ください。

            ファイルの形式は以下の通りです。
             - 2つのシート（`west`と`east`）を含む。
             - `west`シートには西キャンパス、`east`シートには東キャンパスのデータがまとめられている。
             - 行ラベルは、曜日（月～金）と時限（1～5）の組み合わせ。
             - 列ラベルは、年度（西暦4桁）と学期（SPR, SMR, AUT, WTR）の組み合わせ。
             - 各セルには、対応する対面講義履修者数が記録されている。
            
            具体的には、以下のような表です。
            """
        )
        tab1, tab2 = st.tabs(["west", "east"])
        with tab1:
            st.dataframe(
                pd.DataFrame(
                    {
                        "曜日": [d for d in ["月", "火", "水", "木", "金"] for _ in range(5)], 
                        "時限": [i for _ in range(5) for i in range(1, 6)], 
                        "2024SPR": np.random.randint(100, 500, size=25), 
                        "2024SMR": np.random.randint(100, 500, size=25), 
                        "2024AUT": np.random.randint(100, 500, size=25), 
                        "2024WTR": np.random.randint(100, 500, size=25), 
                        "2025SPR": np.random.randint(100, 500, size=25), 
                        "2025SMR": np.random.randint(100, 500, size=25), 
                        "2025AUT": np.random.randint(100, 500, size=25), 
                        "2025WTR": np.random.randint(100, 500, size=25)
                    }
                ).set_index(["曜日", "時限"])
            )
        with tab2:
            st.dataframe(
                pd.DataFrame(
                    {
                        "曜日": [d for d in ["月", "火", "水", "木", "金"] for _ in range(5)], 
                        "時限": [i for _ in range(5) for i in range(1, 6)], 
                        "2024SPR": np.random.randint(100, 500, size=25), 
                        "2024SMR": np.random.randint(100, 500, size=25), 
                        "2024AUT": np.random.randint(100, 500, size=25), 
                        "2024WTR": np.random.randint(100, 500, size=25), 
                        "2025SPR": np.random.randint(100, 500, size=25), 
                        "2025SMR": np.random.randint(100, 500, size=25), 
                        "2025AUT": np.random.randint(100, 500, size=25), 
                        "2025WTR": np.random.randint(100, 500, size=25)
                    }
                ).set_index(["曜日", "時限"])
            )

#space
st.write("")

# upload calendar-format data
with st.container(border=True):
    st.subheader(":material/calendar_month: カレンダー形式データ")
    st.file_uploader(
        label="カレンダー形式のデータを含む`XLSX`ファイルをアップロードしてください。", 
        type=["xlsx"], 
        accept_multiple_files=False, 
        key="uploaded_calendar", 
        on_change=when_calendar_changed
    )
    if st.button(label="使用するデータを決定する", key="button_calendar", disabled=button_controller("uploaded_calendar")):
        with st.spinner("データを読み込んでいます...", show_time=True):
            try:
                df_cal = load_uploaded_calendar()
                if not df_cal.empty:
                    set_session_state_calendar(df_cal)
                    st.session_state["calendar_changed"] = False
                else:
                    st.error(
                        """
                        データの読み込みに失敗しました。\\
                        アップロードされたファイルには有効なデータが含まれていません。
                        """
                    )
                    st.session_state["calendar_changed"] = False
            except:
                st.error(
                    """
                    データの読み込みに失敗しました。\\
                    データ形式が正しくない可能性があります。
                    """
                )
    # Information about the uploaded calendar data
    message = get_uploaded_calendar_info()
    st.info(
        f"""
        :material/check_circle: アップロードされているカレンダー形式データ
         - 期間：{message}
        """
    )
    # About file format
    with st.expander(":material/warning: （重要）データの形式について"):
        st.markdown(
            """
            各日付に対して、年度・学期・授業情報などを記録した`XLSX`ファイルをアップロードする必要があります。

            ファイルの形式は以下の通りです。
             - `date`, `academic_year`, `term`, `class`, `info`の5つの列を持つ。
             - `date`：日付（YYYY/MM/DD）
             - `academic_year`：年度（YYYY）
             - `term`：学期（SPR, SMR, AUT, WTR）+ その他の情報（VAC, INT）
             - `class`：授業情報（NoClass, MON~FRI, IntCourse）
             - `info`：その他情報（Replaced, Holiday, TOEFL, OnlineExam, IkkyoFes）
            
            なお、日付は学期途中から始めないようにしてください。\\
            例えば、2022年度の春学期は2022/04/11から始まりますが、その際に、2022/04/18など学期途中から
            カレンダーの日程を始めると、客数予測モデルを構築する際に正しく処理されませんので注意してください。
            
            最も確実な方法は、04/01から始めることです。\\
            具体的には、以下のような表です。
            """
        )
        
        st.dataframe(
            pd.DataFrame(
                {
                    "date": list(map(lambda x: x.strftime("%Y/%m/%d"), pd.date_range(start="2024/04/01", end="2024/4/30", freq="D").tolist())), 
                    "academic_year": [2024] * 30, 
                    "term": ["SPRVAC"] * 10 + ["SPR"] * 20, 
                    "class": ["NoClass"] * 10 + ["MON", "TUE", "WED", "THU", "FRI", "NoClass", "NoClass"] * 2 + ["MON", "TUE", "WED", "THU", "FRI", "NoClass"], 
                    "info": ["TOEFL"] + [pd.NA] * 29
                }
            ), 
            hide_index=True
        )

