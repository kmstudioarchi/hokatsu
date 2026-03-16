import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import seaborn as sns
import re

# --- 1. ページ設定 ---
st.set_page_config(page_title="【目黒区】保育園の空き数推移グラフ 生成サービス（直近2ヶ年）")
st.caption("出典：目黒区オープンデータ（CC BY 4.0）を加工して作成")

# --- 2. データの高速読み込み（キャッシュ機能 + 2年分限定 + 最新優先） ---
@st.cache_data(ttl=3600)
def load_nursery_data_2years():
    package_id = "131105_available_child_care"
    package_url = f"https://data.bodik.jp/api/3/action/package_show?id={package_id}"
    res_package = requests.get(package_url).json()
    
    # 全リソース取得（通常、新しい順に並んでいます）
    resources = res_package['result']['resources']
    
    # 直近24個（約2年分）に絞る
    target_resources = resources[:24]
    
    all_data = []
    for r in target_resources:
        try:
            df = pd.read_csv(r['url'], encoding='shift-jis')
            # リソース名（例：令和6年4月1日現在）を保存
            df['調査時点'] = r['name']
            # メタデータの作成日時なども考慮できるようリソース情報を付与
            df['作成日時'] = r.get('created', '') 
            all_data.append(df)
        except:
            continue
    
    if not all_data:
        return None
        
    df_full = pd.concat(all_data, sort=False)

    # 日付クレンジング関数の定義（重複排除のため先に処理）
    def clean_date(text):
        nums = re.findall(r'\d+', str(text))
        if len(nums) >= 2:
            year, month = int(nums[0]), int(nums[1])
            if year < 100: year += 2018
            return f"{year}/{month:02d}"
        return text

    df_full['表示月'] = df_full['調査時点'].apply(clean_date)

    # ★ 同月内で「後から出たデータ」のみを残す処理 ★
    # 作成日時やリソースの並び順を利用して、同じ「表示月」の中で最新の1つに絞り込む
    df_full = df_full.sort_values(['表示月', '作成日時'], ascending=[True, True])
    # 各月・各園の組み合わせで、一番最後のデータ（最新）を保持
    # 園名カラムを特定
    name_col = next((c for c in df_full.columns if '名' in c or '施設' in c), None)
    if name_col:
        df_full = df_full.drop_duplicates(subset=['表示月', name_col], keep='last')

    return df_full

# --- 3. 認証と決済の設定 ---
CORRECT_PASSWORD = "hokatsu0123" 
STRIPE_LINK = "https://buy.stripe.com/test_eVq14n7W27ZOcumeKJ0co00" # あなたのリンク

user_password = st.sidebar.text_input("パスワードを入力してください", type="password")

# --- 4. メイン処理 ---
if user_password != CORRECT_PASSWORD:
    st.info("💡 このツールは有料（300円）です。")
    st.link_button("決済してパスワードを取得する", STRIPE_LINK)
    st.stop()
else:
    st.title("【目黒区】保育園の空き数推移グラフ 生成サービス（直近2ヶ年）")
    
    with st.spinner('過去24ヶ月分のデータを解析中...'):
        df_all = load_nursery_data_2years()

    if df_all is not None:
        # 1. データの中から「園名」が入っている列を探す
        name_col = next((c for c in df_all.columns if '名' in c or '施設' in c), None)
        
        if name_col:
            # 2. 全データから重複のない園名リストを作成（あいうえお順に並べ替え）
            nursery_list = sorted(df_all[name_col].unique().tolist())
            
            # 3. プルダウン（セレクトボックス）を表示
            # 最初に空の選択肢を入れたい場合は ["選択してください..."] + nursery_list にします
            selected_nursery = st.selectbox(
                "表示したい保育園を選択してください",
                options=["選択してください..."] + nursery_list
            )

            # 4. 選択された園がある場合にグラフを描画
            if selected_nursery != "選択してください...":
                match = df_all[df_all[name_col] == selected_nursery].copy()


            if not match.empty:
                # グラフ用の年齢別カラム特定
                plot_cols = []
                for age in ['0歳', '０歳', '1歳', '１歳', '2歳', '２歳']:
                    col = next((c for c in match.columns if age in c and '児' in c), None)
                    if col and col not in plot_cols:
                        plot_cols.append(col)

                df_plot = match.melt(id_vars='表示月', value_vars=plot_cols, var_name='年齢', value_name='空き数')
                df_plot = df_plot.sort_values('表示月')

                fig, ax = plt.subplots(figsize=(10, 5))
                sns.lineplot(data=df_plot, x='表示月', y='空き数', hue='年齢', marker='o', ax=ax)
                plt.xticks(rotation=45)
                plt.grid(True, linestyle=':', alpha=0.6)
                st.pyplot(fig)
            else:
                st.warning("該当する園が見つかりません。")
