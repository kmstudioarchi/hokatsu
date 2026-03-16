import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import seaborn as sns
import re

# --- ページ設定と出典表示 ---
st.set_page_config(page_title="保育園空き状況シミュレーター")
st.caption("出典：目黒区オープンデータ（CC BY 4.0）を加工して作成")

# --- ステップ4で説明する「鍵」の仕組み ---
CORRECT_PASSWORD = "your-password-here" # Stripe決済後に教える合言葉
user_password = st.sidebar.text_input("パスワードを入力", type="password")

if user_password != CORRECT_PASSWORD:
    st.info("💡 このツールは有料（300円）です。")
    st.link_button("決済してパスワードを取得する", "https://stripe.com/your-link") # Stripeリンク
    st.stop() # パスワードが違う場合はここで処理を止める

# --- メイン機能 ---
st.title("保育園空き数推移グラフ")
search_keyword = st.text_input("保育園名を入力してください（例：双葉の園ひがしやま保育園）")

if search_keyword:
    with st.spinner('データを集計中...'):
        package_id = "131105_available_child_care"
        package_url = f"https://data.bodik.jp/api/3/action/package_show?id={package_id}"
        
        try:
            res_package = requests.get(package_url).json()
            resources = res_package['result']['resources']
            history_data = []

            for r in resources:
                url = r['url']
                try:
                    df_all = pd.read_csv(url, encoding='shift-jis')
                    name_col = next((c for c in df_all.columns if '名' in c or '施設' in c), None)
                    if name_col:
                        match = df_all[df_all[name_col].astype(str).str.contains(search_keyword, na=False)].copy()
                        if not match.empty:
                            match['調査時点'] = r['name']
                            history_data.append(match)
                except:
                    continue

            if history_data:
                df_final = pd.concat(history_data, sort=False)
                
                # 日付クレンジング関数の定義
                def clean_date(text):
                    nums = re.findall(r'\d+', text)
                    if len(nums) >= 2:
                        year, month = int(nums[0]), int(nums[1])
                        if year < 100: year += 2018
                        return f"{year}/{month:02d}"
                    return text

                df_final['表示日付'] = df_final['調査時点'].apply(clean_date)
                df_final = df_final.groupby('表示日付').mean(numeric_only=True).reset_index()
                df_final = df_final.sort_values('表示日付')

                plot_cols = []
                for age in ['0歳', '０歳', '1歳', '１歳', '2歳', '２歳']:
                    col = next((c for c in df_final.columns if age in c and '児' in c), None)
                    if col and col not in plot_cols: plot_cols.append(col)

                df_plot = df_final.melt(id_vars='表示日付', value_vars=plot_cols, var_name='年齢', value_name='空き数')

                # グラフ描画
                fig, ax = plt.subplots(figsize=(10, 5))
                sns.lineplot(data=df_plot, x='表示日付', y='空き数', hue='年齢', marker='o', errorbar=None, ax=ax)
                plt.xticks(rotation=45)
                plt.grid(True, linestyle=':', alpha=0.6)
                st.pyplot(fig) # Streamlitでグラフを表示
            else:
                st.warning("該当する保育園が見つかりませんでした。")
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")