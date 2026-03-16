import streamlit as st
import pandas as pd
import requests
import re

# --- 1. ページ設定 ---
st.set_page_config(page_title="【目黒区】保育園の空き数推移グラフ 生成サービス")
st.caption("出典：目黒区オープンデータ（CC BY 4.0）を加工して作成")

# --- 2. データの高速読み込み（2年分限定 + 最新優先） ---
@st.cache_data(ttl=3600)
def load_nursery_data_2years():
    package_id = "131105_available_child_care"
    package_url = f"https://data.bodik.jp/api/3/action/package_show?id={package_id}"
    
    try:
        res_package = requests.get(package_url).json()
        resources = res_package['result']['resources']
        
        # 最新の24個（約2年分）に絞る
        target_resources = resources[:24]
        
        all_data = []
        for r in target_resources:
            try:
                df = pd.read_csv(r['url'], encoding='shift-jis')
                df['調査時点'] = r['name']
                df['作成日時'] = r.get('created', '') 
                all_data.append(df)
            except:
                continue
        
        if not all_data:
            return None
            
        df_full = pd.concat(all_data, sort=False)

        # 日付クレンジング
        def clean_date(text):
            nums = re.findall(r'\d+', str(text))
            if len(nums) >= 2:
                year, month = int(nums[0]), int(nums[1])
                if year < 100: year += 2018
                return f"{year}/{month:02d}"
            return text

        df_full['表示月'] = df_full['調査時点'].apply(clean_date)
        df_full = df_full.sort_values(['表示月', '作成日時'], ascending=[True, True])
        
        name_col = next((c for c in df_full.columns if '名' in c or '施設' in c), None)
        if name_col:
            df_full = df_full.drop_duplicates(subset=['表示月', name_col], keep='last')

        return df_full
    except Exception as e:
        st.error(f"データ取得中にエラーが発生しました: {e}")
        return None

# --- 3. 認証と決済の設定 ---
CORRECT_PASSWORD = "hokatsu0123" 
STRIPE_LINK = "https://buy.stripe.com/test_eVq14n7W27ZOcumeKJ0co00" 

user_password = st.sidebar.text_input("パスワードを入力してください", type="password")

# --- 4. メイン処理 ---
if user_password != CORRECT_PASSWORD:
    st.info("💡 このツールは有料（300円）です。決済後に発行されるパスワードを入力してください。")
    st.link_button("決済してパスワードを取得する", STRIPE_LINK)
    st.stop()
else:
    st.success("認証に成功しました！")
    st.title("【目黒区】保育園の空き数推移（直近2ヶ年）")
    
    with st.spinner('データを解析中...'):
        df_all = load_nursery_data_2years()

    if df_all is not None:
        name_col = next((c for c in df_all.columns if '名' in c or '施設' in c), None)
        
        if name_col:
            # 園名リスト作成
            nursery_list = sorted(df_all[name_col].unique().tolist())
            selected_nursery = st.selectbox(
                "表示したい保育園名を選択してください",
                options=["選択してください..."] + nursery_list
            )

            if selected_nursery != "選択してください...":
                match = df_all[df_all[name_col] == selected_nursery].copy()
                match = match.sort_values('表示月')

                # --- 年齢選択機能（5歳児まで） ---
                st.write("▼ 表示したい年齢を選択してください（複数選択可）")
                
                # 目黒区のデータに含まれる可能性のある表記を網羅
                age_options = ['0歳児', '1歳児', '2歳児', '3歳児', '4歳児', '5歳児']
                
                # ユーザーがチェックボックスで選択
                # デフォルトでは0~2歳児にチェックを入れておく
                selected_ages = []
                cols = st.columns(6)
                for i, age in enumerate(age_options):
                    if cols[i].checkbox(age, value=(i <= 2)):
                        selected_ages.append(age)

                # データから対応する列を特定
                plot_cols = []
                for age in selected_ages:
                    # 全角・半角両方の「歳」と「児」を検索
                    age_num = age[0] # '0', '1' など
                    col = next((c for c in match.columns if (age_num in c) and ('児' in c)), None)
                    if col:
                        plot_cols.append(col)

                # グラフの表示
                if plot_cols:
                    st.subheader(f"📊 {selected_nursery} の空き数推移")
                    
                    # Streamlitの標準グラフを使用（文字化け対策）
                    chart_data = match.set_index('表示月')[plot_cols]
                    st.line_chart(chart_data)

                    with st.expander("詳細データ（数値）を確認する"):
                        st.dataframe(match[['表示月'] + plot_cols].sort_values('表示月', ascending=False))
                else:
                    st.warning("表示する年齢を選択するか、データが存在するか確認してください。")
