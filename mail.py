import streamlit as st
import pandas as pd
import requests
import re

# --- 1. ページ設定 ---
st.set_page_config(
    page_title="保育園の空き数 推移グラフ 生成【目黒区ver.】",
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

# --- 3. noteのURL設定 ---
# 作成したnote記事（使い方や想いを書いたもの）のURLをここに入れてください
NOTE_URL = "https://note.com/あなたのID/n/記事のID"

# --- 4. メイン画面のヘッダー ---
st.title("🏠 保育園の空き数 推移グラフ 生成【目黒区ver.】")
st.markdown(f"""
### 過去2年間のデータを可視化して、保活をサポート。
目黒区が公表している過去24ヶ月分の空き状況を自動集計し、特定の園の推移をグラフ化します。
活用方法や開発の背景については [こちらのnote記事]({https://note.com/kmstudioarchi/n/nf03d774279a0}) をご覧ください。
""")

st.divider()

# --- 5. メイン処理（誰でも利用可能） ---
with st.spinner('⌛ 最新データを解析中... 最大2分ほどかかります。そのままお待ちください。'):
    df_all = load_nursery_data_2years()

if df_all is not None:
    name_col = next((c for c in df_all.columns if '名' in c or '施設' in c), None)
    
    if name_col:
        st.markdown("### 🔍 1. 保育園と年齢を選ぶ")
        
        nursery_list = sorted(df_all[name_col].unique().tolist())
        selected_nursery = st.selectbox("保育園名を選択", options=["選択してください..."] + nursery_list)

        age_options = ['0歳児', '1歳児', '2歳児', '3歳児', '4歳児', '5歳児']
        selected_ages = []
        cols = st.columns(6)
        for i, age in enumerate(age_options):
            if cols[i].checkbox(age, value=(i <= 2)):
                selected_ages.append(age)

        if selected_nursery != "選択してください...":
            st.divider()
            
            match = df_all[df_all[name_col] == selected_nursery].copy()
            match = match.sort_values('表示月')

            plot_cols = []
            for age in selected_ages:
                age_num = age[0]
                col = next((c for c in match.columns if (age_num in c) and ('児' in c)), None)
                if col: plot_cols.append(col)

            if plot_cols:
                st.subheader(f"📈 {selected_nursery} の空き数推移")
                chart_data = match.set_index('表示月')[plot_cols]
                
                # グラフ表示
                st.line_chart(chart_data)

                # --- 寄付・サポートへの誘導（グラフの直後） ---
                st.success("✅ グラフの生成が完了しました！")
                st.info(f"""
                ☕ **開発を応援しませんか？**
                
                このツールは個人が無料で開発・維持しています。もし保活のお役に立てましたら、
                今後の運営維持（データ更新やサーバー代）のために、noteでのサポート（寄付）をいただけますと大変励みになります。
                
                [👉 **noteで開発をサポートする（100円〜）**]({https://note.com/kmstudioarchi/n/nf03d774279a0})
                """)
                
                with st.expander("詳細データ（数値テーブル）を確認する"):
                    st.dataframe(match[['表示月'] + plot_cols].sort_values('表示月', ascending=False))
            else:
                st.warning("表示する年齢を選択してください。")

        # --- 6. 免責事項 ---
        st.divider()
        with st.expander("⚠️ データの取り扱いと免責事項について"):
            st.caption("出典：[目黒区オープンデータ](https://data.bodik.jp/dataset/131105_available_child_care)（CC BY 4.0）")
            st.markdown("""
            * 目黒区より同月内に複数の空き数データが公表されている場合、**より公表日時の新しいデータ**を自動的に採用しています。
            * 本サービスの情報は、実際の入所申し込みにあたっての補助的な材料としてご利用ください。
            * 必ず[目黒区公式ホームページ](https://www.city.meguro.tokyo.jp/)や最新の募集要項をご確認ください。
            * 本サービスの情報により生じた損害について、当方は一切の責任を負いかねます。
            """)
