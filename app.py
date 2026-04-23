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

# --- 3. САЙДБАР: КАСКАДНІ ФІЛЬТРИ ТА ГРОШІ ---
with st.sidebar:
    st.markdown("### 🎛 Фільтри")
    
    # КРОК 1: Менеджери
    managers_list = sorted(df["Менеджер"].dropna().unique()) if "Менеджер" in df.columns else []
    selected_managers = st.multiselect("👤 Менеджери", managers_list, default=managers_list)
    
    df_step1 = df[df["Менеджер"].isin(selected_managers)] if selected_managers else df
    
    # КРОК 2: Готовність (залежить від обраних менеджерів)
    intents_list = sorted(df_step1["Готовність"].dropna().unique()) if "Готовність" in df_step1.columns else []
    selected_intents = st.multiselect("🎯 Готовність до покупки", intents_list, default=intents_list)

    df_step2 = df_step1[df_step1["Готовність"].isin(selected_intents)] if selected_intents else df_step1

    # КРОК 3: Причина (залежить від менеджерів і готовності)
    root_list = sorted(df_step2["ROOT_PROBLEM"].dropna().unique()) if "ROOT_PROBLEM" in df_step2.columns else []
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
    [Написати в Telegram](https://t.me/Твій_Нікнейм)
    """)

# Фінальний відфільтрований датафрейм для всіх вкладок
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
        manager_loss = df_filtered.groupby("М
