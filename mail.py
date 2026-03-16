import streamlit as st
import pandas as pd
import requests
import re

# --- 1. ページ設定 ---
st.set_page_config(
    page_title="保育園の空き数 推移グラフ 生成【目黒区ver.】",
    page_icon="🏠",
    layout="centered"
)

# --- 2. データの高速読み込み（進捗表示付き） ---
@st.cache_data(ttl=3600)
def load_nursery_data_2years():
    package_id = "131105_available_child_care"
    package_url = f"https://data.bodik.jp/api/3/action/package_show?id={package_id}"
    
    try:
        res_package = requests.get(package_url).json()
        resources = res_package['result']['resources']
        target_resources = resources[:24]
        
        all_data = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, r in enumerate(target_resources):
            percent = int((i + 1) / len(target_resources) * 100)
            progress_bar.progress(percent)
            status_text.text(f"データ解析中... ({i+1}/24ヶ月分を完了)")
            
            try:
                df = pd.read_csv(r['url'], encoding='shift-jis')
                df['調査時点'] = r['name']
                df['作成日時'] = r.get('created', '') 
                all_data.append(df)
            except:
                continue
        
        progress_bar.empty()
        status_text.empty()
        
        if not all_data: return None
            
        df_full = pd.concat(all_data, sort=False)

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

# --- 3. 認証・決済設定 ---
CORRECT_PASSWORD = "hokatsu0123" 
STRIPE_LINK = "https://buy.stripe.com/test_eVq14n7W27ZOcumeKJ0co00" 

st.sidebar.header("🔑 認証")
user_password = st.sidebar.text_input("パスワードを入力", type="password")

# --- 4. メイン画面のヘッダー ---
st.title("🏠 保育園の空き数 推移グラフ 生成【目黒区ver.】")
st.markdown("""
### 「いつ、どの園なら入りやすい？」を過去2年のデータから可視化。
目黒区が公表している過去の空き状況データを集計し、特定の保育園の空き数の変化をグラフで見ることができるツールです。
**保活の戦略（いつ頃空きが出やすいか、0歳と1歳の違いなど）**を立てるのにお役立てください。
""")

st.divider()

# --- 5. メイン処理 ---
if user_password != CORRECT_PASSWORD:
    st.info("💡 **このツールは有料（300円）です。**")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **【このツールでわかること】**
        * 特定の園の過去24ヶ月の空き数推移
        * 年齢別（0歳〜5歳）の空き状況比較
        * 同月内の最新修正データの自動反映
        """)
    with col2:
        st.markdown("""
        **【ご利用の流れ】**
        1. 下のボタンから決済を完了
        2. 発行されるパスワードを左の欄に入力
        3. 園名を選んでグラフを表示
        """)
    
    st.link_button("👉 決済してパスワードを取得する", STRIPE_LINK, use_container_width=True)
    st.stop()
else:
    st.success("認証に成功しました。データの読み込みを開始します。")
    
    with st.spinner('⌛ 最新データを解析中... 最大2分ほどかかります。そのままお待ちください。'):
        df_all = load_nursery_data_2years()

    if df_all is not None:
        name_col = next((c for c in df_all.columns if '名' in c or '施設' in c), None)
        
        if name_col:
            st.markdown("### 🔍 ステップ1：保育園を選ぶ")
            nursery_list = sorted(df_all[name_col].unique().tolist())
            selected_nursery = st.selectbox(
                "表示したい保育園名を選択してください",
                options=["選択してください..."] + nursery_list
            )

            if selected_nursery != "選択してください...":
                st.markdown("### 👶 ステップ2：年齢を選ぶ")
                match = df_all[df_all[name_col] == selected_nursery].copy()
                match = match.sort_values('表示月')

                age_options = ['0歳児', '1歳児', '2歳児', '3歳児', '4歳児', '5歳児']
                selected_ages = []
                cols = st.columns(6)
                for i, age in enumerate(age_options):
                    if cols[i].checkbox(age, value=(i <= 2)):
                        selected_ages.append(age)

                plot_cols = []
                for age in selected_ages:
                    age_num = age[0]
                    col = next((c for c in match.columns if (age_num in c) and ('児' in c)), None)
                    if col: plot_cols.append(col)

                if plot_cols:
                    st.divider()
                    st.subheader(f"📈 {selected_nursery} の空き数推移")
                    chart_data = match.set_index('表示月')[plot_cols]
                    
                    # グラフ表示
                    st.line_chart(chart_data)

                    st.caption("出典：[目黒区オープンデータ](https://data.bodik.jp/dataset/131105_available_child_care)（CC BY 4.0）")
                    
                    with st.expander("⚠️ データの取り扱いと免責事項について"):
                        st.markdown("""
                        **【データの集計ルールについて】**
                        * 目黒区より同月内に複数の空き数データが公表されている場合、当システムでは**より公表日時の新しいデータ（修正版等）を自動的に採用**してグラフ化しています。
                        
                        **【免責事項】**
                        * 本サービスは目黒区のオープンデータを加工して提供していますが、データの正確性や最新性を保証するものではありません。
                        * 実際の入所申し込みにあたっては、必ず[目黒区公式ホームページ](https://www.city.meguro.tokyo.jp/)や最新の募集要項をご確認ください。
                        * 本サービスの情報に基づいて行われた判断や行動により生じた損害について、当方は一切の責任を負いかねます。
                        """)
                    
                    with st.expander("詳細データ（数値）を確認する"):
                        st.dataframe(match[['表示月'] + plot_cols].sort_values('表示月', ascending=False))
                else:
                    st.warning("表示する年齢を選択してください。")
