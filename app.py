import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- 1. НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(page_title="AI Sales Audit | Demo Case", layout="wide")

st.title("🚀 AI-Аудит Відділу Продажів")
st.subheader("Демонстраційний кейс: Аналіз ефективності та пошук втраченого прибутку")

st.info("""
**Як це працює?** Нейромережа прослуховує 100% дзвінків, оцінює навички менеджерів за 10+ критеріями та виявляє причини відмов. 
На цьому дашборді ви бачите реальні дані (анонімізовані), які допомагають СЕО приймати рішення на основі цифр, а не відчуттів.
""")

st.markdown("""
<style>
    .stApp { background-color: #F8F9FA; color: #1E293B; }
    h1, h2, h3 { font-weight: 800; color: #0F172A; }
    [data-testid="stMetricValue"] { font-size: 2.2rem; font-weight: 800; color: #DC2626; }
    [data-testid="stMetricLabel"] { font-weight: 600; color: #64748B; text-transform: uppercase; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { padding-top: 10px; padding-bottom: 10px; font-size: 1.2rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- 2. РОЗУМНЕ ЗАВАНТАЖЕННЯ ДАНИХ ---
@st.cache_data(ttl=60)
def load_data():
    df = pd.DataFrame()
    
    try:
        from streamlit_gsheets import GSheetsConnection
        conn = st.connection("gsheets", type=GSheetsConnection)
        url = "https://docs.google.com/spreadsheets/d/1ngMU3jHZV_zFP6RSOeIjxMBs6xd0PTE7ijD09kgBeKw/edit"
        df = conn.read(spreadsheet=url)
    except Exception:
        pass
    
    if df.empty:
        try:
            df = pd.read_excel(r"D:\виход\REPORT_EXIST_CEO.xlsx")
        except Exception:
            pass

    if not df.empty:
        rename_dict = {}
        for col in df.columns:
            if "OOT" in col and "PROBLEM" in col: rename_dict[col] = "ROOT_PROBLEM"
            if "Готовність" in col: rename_dict[col] = "Готовність"
            if "Крос_Сел" in col and "проба" in col: rename_dict[col] = "Спроба_Крос_Селу"
            if "Дотиснув" in col: rename_dict[col] = "Зафіксував_Наступний_Крок"
        df.rename(columns=rename_dict, inplace=True)
        
        # Примусово робимо ці колонки текстом
        if "Менеджер" in df.columns:
            df["Менеджер"] = df["Менеджер"].astype(str)
        if "Дзвінок" in df.columns:
            df["Дзвінок"] = df["Дзвінок"].astype(str)
            
    return df

df = load_data()

if df.empty:
    st.error("❌ Не вдалося знайти дані. Перевірте Google Sheets або наявність локального файлу.")
    st.stop()

# --- 3. САЙДБАР: ФІЛЬТРИ ТА ГРОШІ ---
with st.sidebar:
    st.markdown("### 🎛 Фільтри")
    
    managers_list = sorted(df["Менеджер"].dropna().unique()) if "Менеджер" in df.columns else []
    selected_managers = st.multiselect("👤 Менеджери", managers_list, default=managers_list)
    
    intents_list = sorted(df["Готовність"].dropna().unique()) if "Готовність" in df.columns else []
    selected_intents = st.multiselect("🎯 Готовність до покупки", intents_list, default=intents_list)

    root_list = sorted(df["ROOT_PROBLEM"].dropna().unique()) if "ROOT_PROBLEM" in df.columns else []
    selected_roots = st.multiselect("🚨 Причина втрати", root_list, default=root_list)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 💰 Фінансові параметри")
    avg_check = st.number_input("Середній чек (грн)", value=1500, step=100)
    
    st.markdown("#### Параметри Крос-селу")
    avg_cross_check = st.number_input("Середній чек доп. товару (грн)", value=100, step=10)
    cross_conv = st.slider("Конверсія у доп. продаж (%)", 0, 100, 10)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Вага потенціалу:")
    st.write("🔥 High: 100%")
    st.write("⚡ Medium: 50%")

    st.markdown("---")
    st.markdown("### 🛠 Бажаєте такий аудит?")
    st.markdown("""
    Я можу налаштувати таку систему для вашого бізнесу за 3 дні:
    - ✅ Автоматичне прослуховування дзвінків
    - ✅ Інтеграція з вашою CRM/телефонією
    - ✅ Щоденні звіти про втрачений прибуток
    
    **Зв'язатися з розробником:**
    [Написати в Telegram](https://t.me/sharkobogdan)
    """)

df_filtered = df[
    (df["Менеджер"].isin(selected_managers)) & 
    (df["Готовність"].isin(selected_intents)) &
    (df["ROOT_PROBLEM"].isin(selected_roots))
].copy()

# --- 4. МАТЕМАТИКА ВТРАТ ---
intent_weights = {"High": 1.0, "Medium": 0.5, "Low": 0.0}
df_filtered['Потенціал_грн'] = df_filtered['Готовність'].map(intent_weights).fillna(0) * avg_check

df_filtered['Втрачено_Головна'] = df_filtered.apply(
    lambda x: x['Потенціал_грн'] if x['ROOT_PROBLEM'] != 'Немає' else 0, axis=1
)

df_filtered['Втрачено_Крос'] = df_filtered.apply(
    lambda x: (avg_cross_check * (cross_conv/100)) if (x['ROOT_PROBLEM'] == 'Немає' and x['Спроба_Крос_Селу'] == 'Ні') else 0, axis=1
)

df_filtered['Втрачено_грн'] = df_filtered['Втрачено_Головна'] + df_filtered['Втрачено_Крос']

# --- 5. ЗАГОЛОВОК І ВКЛАДКИ ---
tab_ceo, tab_coach, tab_call = st.tabs(["💰 CEO: Втрачений прибуток", "🎓 Навчання: Розбір навичок", "🎧 Картка дзвінка"])

# ==========================================
# ПАНЕЛЬ 1: CEO (Гроші та Ефективність)
# ==========================================
with tab_ceo:
    st.markdown("""
        <div style="background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 25px; margin-bottom: 25px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <h3 style="margin-top: 0; margin-bottom: 20px; font-size: 20px; border-bottom: 2px solid #F1F5F9; padding-bottom: 10px;">📊 Ключові показники втрат та ефективності</h3>
        </div>
    """, unsafe_allow_html=True)

    total_lost_main = df_filtered["Втрачено_Головна"].sum()
    total_lost_cross = df_filtered["Втрачено_Крос"].sum()
    total_lost_all = df_filtered["Втрачено_грн"].sum()
    
    hot_med_deals = df_filtered[df_filtered['Готовність'].isin(['High', 'Medium'])]
    hot_med_total = len(hot_med_deals)
    hot_med_lost = len(hot_med_deals[hot_med_deals['ROOT_PROBLEM'] != 'Немає'])
    hot_loss_rate = (hot_med_lost / hot_med_total * 100) if hot_med_total > 0 else 0

    success_deals = df_filtered[df_filtered['ROOT_PROBLEM'] == 'Немає']
    
    missed_cross_count = len(success_deals[success_deals['Спроба_Крос_Селу'] == 'Ні'])
    missed_cross_rate = (missed_cross_count / len(success_deals) * 100) if len(success_deals) > 0 else 0
    
    if 'Екосистема' in success_deals.columns:
        eco_scores = pd.to_numeric(success_deals['Екосистема'], errors='coerce').fillna(0)
        missed_eco_count = len(success_deals[eco_scores == 0])
    else:
        missed_eco_count = 0
        
    missed_eco_rate = (missed_eco_count / len(success_deals) * 100) if len(success_deals) > 0 else 0

    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric("🔥 ЗАГАЛЬНІ ВТРАТИ", f"{total_lost_all:,.0f} ₴")
    m_col2.metric("💰 Втрати (Основні)", f"{total_lost_main:,.0f} ₴")
    m_col3.metric("📦 Втрати (Крос-сел)", f"{total_lost_cross:,.0f} ₴")

    st.markdown("<div style='margin: 20px 0;'></div>", unsafe_allow_html=True)

    p_col1, p_col2, p_col3 = st.columns(3)
    p_col1.metric("📉 % втрат ГАРЯЧИХ", f"{hot_loss_rate:.0f}%", help="Відсоток клієнтів з High/Medium готовністю, які нічого не купили")
    p_col2.metric("🛒 % без CROSS-SELL", f"{missed_cross_rate:.0f}%", help="Відсоток успішних угод, де менеджер не запропонував супутній товар")
    p_col3.metric("🌐 % без ЕКОСИСТЕМИ", f"{missed_eco_rate:.0f}%", help="Відсоток успішних угод, де не було пропозиції сервісів екосистеми")

    st.markdown("<hr style='margin: 30px 0;'>", unsafe_allow_html=True)
    
    row1_col1, row1_col2 = st.columns([1.2, 1])
    
    with row1_col1:
        st.markdown("### 🎯 Причини втрат (включаючи недоотриманий крос-сел)")
        reasons_data = df_filtered[df_filtered['Втрачено_грн'] > 0].groupby('ROOT_PROBLEM')['Втрачено_грн'].sum().reset_index()
        
        if total_lost_cross > 0:
            reasons_data.loc[reasons_data['ROOT_PROBLEM'] == 'Немає', 'ROOT_PROBLEM'] = 'Відсутність Крос-селу'
            
        reasons_data = reasons_data.sort_values(by='Втрачено_грн', ascending=False).head(5)
        
        if not reasons_data.empty:
            fig_reasons = px.bar(reasons_data, x='Втрачено_грн', y='ROOT_PROBLEM', orientation='h', 
                                 color='Втрачено_грн', color_continuous_scale='Reds',
                                 labels={'Втрачено_грн': 'Втрати в гривнях', 'ROOT_PROBLEM': 'Причина'})
            fig_reasons.update_layout(showlegend=False, height=350, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_reasons, use_container_width=True)
        else:
            st.success("Втрат немає!")

    with row1_col2:
        st.markdown("### 🚨 Рейтинг фінансових втрат")
        manager_loss = df_filtered.groupby("Менеджер")['Втрачено_грн'].sum().reset_index().sort_values("Втрачено_грн", ascending=False)
        styled_loss = manager_loss.style.format({'Втрачено_грн': '{:,.0f}'}) \
            .background_gradient(cmap='Reds', subset=['Втрачено_грн'])
        st.dataframe(styled_loss, use_container_width=True, hide_index=True)

    st.markdown("<br>### 🔎 Деталізація втраченого прибутку", unsafe_allow_html=True)
    all_lost_details = df_filtered[df_filtered['Втрачено_грн'] > 0].copy()
    
    if not all_lost_details.empty:
        all_lost_details['Деталі_втрати'] = all_lost_details.apply(
            lambda x: "Не запропоновано крос-сел" if (x['ROOT_PROBLEM'] == 'Немає' and x['Втрачено_Крос'] > 0) else x.get('Інсайт_для_CEO', ''), axis=1
        )
        cols_to_show = ['Менеджер', 'Дзвінок', 'Готовність', 'ROOT_PROBLEM', 'Втрачено_грн', 'Деталі_втрати']
        st.dataframe(all_lost_details[cols_to_show], use_container_width=True, hide_index=True)
else:
        st.success("Втрат не виявлено!")

    st.markdown("---")
    st.warning("💡 **Висновок для інвестора:** Система виявляє точки втрат і показує, де можна повернути частину угод за рахунок покращення роботи менеджерів.")

# ==========================================
# ПАНЕЛЬ 2: MANAGER COACHING
# ==========================================
with tab_coach:
    st.success("🎯 **Для РОПа:** ШІ не просто ставить бали, а підказує, які саме фрази менеджера завадили продажу. Дивіться блок 'Поради' праворуч.")
    st.markdown("### 📊 Детальний розбір навичок")
    
    skill_cols = ['Привітання', 'Експертиза', 'Презентація', 'Крос_сел', 'Екосистема', 'Закриття', 'Привітність', 'Активне_Слухання', 'Впевненість_Мовлення', 'Емпатія']
    existing_skills = [c for c in skill_cols if c in df_filtered.columns]
    
    agg_dict = {"Дзвінків": pd.NamedAgg(column="Дзвінок", aggfunc="count")}
    if "Hard_Бал" in df_filtered.columns: agg_dict["Середній_Hard"] = pd.NamedAgg(column="Hard_Бал", aggfunc="mean")
    if "Soft_Бал" in df_filtered.columns: agg_dict["Середній_Soft"] = pd.NamedAgg(column="Soft_Бал", aggfunc="mean")
    
    for skill in existing_skills:
        agg_dict[skill] = pd.NamedAgg(column=skill, aggfunc="mean")
        
    coach_stats = df_filtered.groupby("Менеджер").agg(**agg_dict).reset_index()
    
    col_c1, col_c2 = st.columns([2, 1.2])
    
    with col_c1:
        gradient_cols_main = [c for c in ['Середній_Hard', 'Середній_Soft'] if c in coach_stats.columns]
        gradient_cols_skills = [c for c in existing_skills if c in coach_stats.columns]
        
        styled_coach = coach_stats.style.format(precision=1) \
            .background_gradient(cmap='Greens', subset=gradient_cols_main) \
            .background_gradient(cmap='Blues', subset=gradient_cols_skills, vmin=0, vmax=2)
            
        st.dataframe(styled_coach, use_container_width=True, hide_index=True)
        
    with col_c2:
        st.markdown("**Рекомендації ШІ для вибраних менеджерів:**")
        if "Порада_для_менеджера" in df_filtered.columns:
            for mgr in selected_managers:
                mgr_skills_df = df_filtered[df_filtered["Менеджер"] == mgr]
                if not mgr_skills_df.empty:
                    with st.expander(f"Поради для: {mgr}", expanded=False):
                        for _, row in mgr_skills_df.iterrows():
                            st.write(f"**Файл:** {row['Дзвінок']} (Готовність: {row.get('Готовність', 'N/A')})")
                            st.info(row['Порада_для_менеджера'])
                            st.write("---")
        else:
            st.write("Поради не знайдені.")
                    
    st.markdown("<br>### Матриця компетенцій (Raw Data)", unsafe_allow_html=True)
    raw_cols = ['Менеджер', 'Дзвінок'] + existing_skills
    styled_raw = df_filtered[raw_cols].style.format(precision=0) \
        .background_gradient(cmap='Blues', subset=existing_skills, vmin=0, vmax=2)
    st.dataframe(styled_raw, use_container_width=True, hide_index=True)

# ==========================================
# ПАНЕЛЬ 3: КАРТКА КОНКРЕТНОГО ДЗВІНКА
# ==========================================
with tab_call:
    st.markdown("### 🔎 Детальний розбір розмови")

    if 'Дзвінок' in df_filtered.columns and not df_filtered.empty:
        selected_file = st.selectbox("Оберіть файл дзвінка для розбору:", df_filtered['Дзвінок'].unique())

        if selected_file:
            row = df_filtered[df_filtered['Дзвінок'] == selected_file].iloc[0]

            score_12 = int(row.get('Hard_Бал', 0))
            score_color = "#16A34A" if score_12 >= 10 else ("#F59E0B" if score_12 >= 6 else "#DC2626")
            score_text = "Відмінно" if score_12 >= 10 else ("Задовільно" if score_12 >= 6 else "Погано")

            hard_skill_keys = ['Привітання', 'Експертиза', 'Презентація', 'Крос_сел', 'Екосистема', 'Закриття']
            likes, norms, dislikes = 0, 0, 0
            for key in hard_skill_keys:
                val = row.get(key, 0)
                if val == 2: likes += 1
                elif val == 1: norms += 1
                else: dislikes += 1

            deg = (score_12 / 12) * 360
            
            # --- БЕЗПЕЧНИЙ HTML-БЛОК 1 ---
            html_skills = f"""
            <div style="background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); display: flex; align-items: center; gap: 40px; flex-wrap: wrap;">
                <div style="text-align: center; min-width: 130px;">
                    <div style="width: 120px; height: 120px; border-radius: 50%; background: conic-gradient({score_color} {deg}deg, #E2E8F0 0deg); display: flex; justify-content: center; align-items: center; margin: 0 auto 12px auto;">
                        <div style="width: 95px; height: 95px; border-radius: 50%; background: white; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                            <span style="font-size: 32px; font-weight: 800; color: #0F172A; line-height: 1;">{score_12}</span>
                            <span style="font-size: 13px; color: #64748B; font-weight: 600;">з 12</span>
                        </div>
                    </div>
                    <span style="background: {score_color}15; color: {score_color}; padding: 6px 16px; border-radius: 20px; font-size: 13px; font-weight: 700;">{score_text}</span>
                </div>
                <div style="flex: 1;">
                    <h3 style="margin: 0 0 15px 0; color: #0F172A; font-size: 18px;">📊 Аналіз навичок продажу</h3>
                    <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                        <div style="flex: 1; background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 10px; padding: 15px; text-align: center; min-width: 120px;">
                            <div style="font-size: 24px; margin-bottom: 5px;">👍</div>
                            <div style="font-size: 20px; font-weight: 800; color: #166534;">{likes}</div>
                            <div style="font-size: 13px; color: #15803D; font-weight: 600;">Сильні сторони</div>
                        </div>
                        <div style="flex: 1; background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 10px; padding: 15px; text-align: center; min-width: 120px;">
                            <div style="font-size: 24px; margin-bottom: 5px;">😐</div>
                            <div style="font-size: 20px; font-weight: 800; color: #B45309;">{norms}</div>
                            <div style="font-size: 13px; color: #B45309; font-weight: 600;">Зона уваги</div>
                        </div>
                        <div style="flex: 1; background: #FEF2F2; border: 1px solid #FECACA; border-radius: 10px; padding: 15px; text-align: center; min-width: 120px;">
                            <div style="font-size: 24px; margin-bottom: 5px;">🚩</div>
                            <div style="font-size: 20px; font-weight: 800; color: #991B1B;">{dislikes}</div>
                            <div style="font-size: 13px; color: #B91C1C; font-weight: 600;">Зони росту</div>
                        </div>
                    </div>
                </div>
            </div>
            """
            st.markdown(html_skills, unsafe_allow_html=True)

            is_success = row.get("ROOT_PROBLEM", "Немає") == "Немає"
            result_bg = "#F0FDF4" if is_success else "#FEF2F2"
            result_border = "#BBF7D0" if is_success else "#FECACA"
            result_title = "Угода успішна / Дотиснуто" if is_success else "Угоду втрачено"
            result_desc = "Менеджер довів клієнта до цільової дії." if is_success else f"Причина втрати ліда: <b>{row.get('ROOT_PROBLEM', 'Невідомо')}</b>."
            status_icon = '✅' if is_success else '❌'

            # --- БЕЗПЕЧНИЙ HTML-БЛОК 2 ---
            html_result = f"""
            <div style="background: {result_bg}; border: 1px solid {result_border}; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <div style="display: flex; gap: 15px; align-items: center;">
                    <div style="font-size: 24px;">{status_icon}</div>
                    <div>
                        <h4 style="margin: 0 0 4px 0; color: #111827; font-size: 16px;">Результат розмови: {result_title}</h4>
                        <p style="margin: 0; color: #374151; font-size: 14px;">{result_desc} <br> Готовність: <b>{row.get('Готовність', 'N/A')}</b> | Зафіксовано крок: <b>{row.get('Зафіксував_Наступний_Крок', 'Ні')}</b> | Крос-сел: <b>{row.get('Спроба_Крос_Селу', 'Ні')}</b></p>
                    </div>
                </div>
            </div>
            """
            st.markdown(html_result, unsafe_allow_html=True)

            tone_text = row.get("Тон_Розмови", "Тон розмови не проаналізовано.")
            
            # --- БЕЗПЕЧНИЙ HTML-БЛОК 3 ---
            html_tone = f"""
            <div style="background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
                <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 8px;">
                    <div style="font-size: 20px;">🎙️</div>
                    <h4 style="margin: 0; color: #0F172A; font-size: 16px;">Тон розмови</h4>
                </div>
                <p style="margin: 0; color: #475569; font-size: 14px; line-height: 1.5; padding-left: 30px;">{tone_text}</p>
            </div>
            """
            st.markdown(html_tone, unsafe_allow_html=True)

            # --- БЕЗПЕЧНИЙ HTML-БЛОК 4 ---
            html_footer = f"""
            <div style="display: flex; gap: 20px; margin-bottom: 20px;">
                <div style="flex: 1; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; background: #F8FAFC;">
                    <p style="margin: 0 0 4px 0; color: #64748B; font-size: 12px; text-transform: uppercase;">Менеджер</p>
                    <h4 style="margin: 0; color: #0F172A; font-size: 16px;">👤 {row.get('Менеджер', 'N/A')}</h4>
                </div>
                <div style="flex: 2; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; background: #F8FAFC;">
                    <p style="margin: 0 0 4px 0; color: #64748B; font-size: 12px; text-transform: uppercase;">Файл дзвінка (Ідентифікатор)</p>
                    <h4 style="margin: 0; color: #0F172A; font-size: 14px; word-break: break-all;">📄 {row.get('Дзвінок', 'N/A')}</h4>
                </div>
            </div>

            <div style="background: #FFFBEB; border: 1px solid #FEF3C7; border-radius: 12px; padding: 20px;">
                <h4 style="margin: 0 0 8px 0; color: #92400E; font-size: 16px;">💡 Аналітика для бізнесу (Інсайт)</h4>
                <p style="margin: 0; color: #92400E; line-height: 1.5;">{row.get('Інсайт_для_CEO', 'Немає інсайтів')}</p>
            </div>
            """
            st.markdown(html_footer, unsafe_allow_html=True)
    else:
        st.info("Немає даних.")
