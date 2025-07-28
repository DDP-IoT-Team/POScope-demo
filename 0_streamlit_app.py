import streamlit as st

pages = [
    st.Page(
        "1_home.py", 
        title="ホーム", 
        icon=":material/home:"
    ), 
    st.Page(
        "2_upload.py", 
        title="アップロード", 
        icon=":material/upload_file:"
    ), 
    st.Page(
        "3_visualize.py", 
        title="データ可視化", 
        icon=":material/visibility:"
    ), 
    st.Page(
        "4_forecast.py", 
        title="予測", 
        icon=":material/query_stats:"
    )
]

page = st.navigation(pages)
page.run()
