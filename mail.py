import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import seaborn as sns
import re

# --- 1. ページ設定 ---
st.set_page_config(page_title="【目黒区】保育園の月別空き数 推移グラフ生成")
st.caption("出典：目黒区オープンデータ（CC BY 4.0）を加工して作成")

# --- 2. データの高速読み込み（キャッシュ機能） ---
@st.cache_data(ttl=3600)  # 1時間はデータを保存して使い回す
def load_all_meguro_data():
    package_id = "131105_available_child_care"
    package_url = f"https://data.bodik.jp/api/3/action/package_show?id={package_id}"
    res_package = requests.get(package_url).json()
    resources = res_package['result']['resources']
    
    all_data = []
    for r in resources:
        try:
            df = pd.read_csv(r['url'], encoding='shift-jis')
            df['調査時点'] = r['name']
            all_data.append(df)
        except:
            continue
    return pd.concat(all_data, sort=False) if all_data else None

# --- 3. 認証と決済の設定 ---
CORRECT_PASSWORD = "hokatsu0123" 
STRIPE_LINK = "https://buy.stripe.com/test_eVq14n7W27ZOcumeKJ0co00" # あなたのStripeリンク

# サイドバーにパスワード入力欄
user_password = st.sidebar.text_input("パスワードを入力してください", type="password")

# --- 4. メイン処理 ---
if user_password != CORRECT_PASSWORD:
    # パスワードが違う場合の画面
    st.info("💡 このツールは有料（300円）です。")
    st.link_button("決済してパスワードを取得する", STRIPE_LINK)
    st.stop() 
else:
    # パスワードが合っている場合の画面
    st.success("認証されました！")
    st.title("【目黒区】保育園の月別空き数 推移グラフ生成")
    
    # データのロード（キャッシュにより2回目以降は爆速）
    with st.spinner('最新データを準備中...'):
        df_full = load_all_meguro_data()

    if df_full is not None:
        search_keyword = st.text_input("保育園名を入力してください（例：双葉の園ひがしやま保育園）")

        if search_keyword:
            with st.spinner('グラフを生成中...'):
                # キーワードで絞り込み
                name_col = next((c for c in df_full.columns if '名' in c or '施設' in c), None)
                if name_col:
                    match = df_full[df_full[name_col].astype(str).str.contains(search_keyword, na=False)].copy()
                    
                    if not match.empty:
                        # 日付クレンジング
                        def clean_date(text):
                            nums = re.findall(r'\d+', str(text))
                            if len(nums) >= 2:
                                year, month = int(nums[0]), int(nums[1])
                                if year < 100: year += 2018
                                return f"{year}/{month:02d}"
                            return text

                        match['表示日付'] = match['調査時点'].apply(clean_date)
                        df_final = match.groupby('表示日付').mean(numeric_only=True).reset_index()
                        df_final = df_final.sort_values('表示日付')

                        # 年齢別カラムの特定
                        plot_cols = []
                        for age in ['0歳', '０歳', '1歳', '１歳', '2歳', '２歳']:
                            col = next((c for c in df_final.columns if age in c and '児' in c), None)
                            if col and col not in plot_cols:
                                plot_cols.append(col)

                        # 描画
                        df_plot = df_final.melt(id_vars='表示日付', value_vars=plot_cols, var_name='年齢', value_name='空き数')
                        
                        fig, ax = plt.subplots(figsize=(10, 5))
                        sns.lineplot(data=df_plot, x='表示日付', y='空き数', hue='年齢', marker='o', errorbar=None, ax=ax)
                        plt.xticks(rotation=45)
                        plt.grid(True, linestyle=':', alpha=0.6)
                        st.pyplot(fig)
                    else:
                        st.warning("該当する保育園が見つかりませんでした。正確な名前を入力してください。")
    else:
        st.error("データの読み込みに失敗しました。時間をおいて再度お試しください。")
