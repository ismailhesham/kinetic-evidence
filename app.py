import streamlit as st
import os
import time
from dotenv import load_dotenv
from pipeline import render

load_dotenv()

st.set_page_config(page_title="Kinetic Evidence Studio", layout="wide", page_icon="🎬")

st.markdown("""
    <style>
    .stApp { background-color: #0f1216; color: #f3f7fb; direction: rtl; font-family: 'Cairo', sans-serif; }
    h1, h2, h3 { color: #4f9dff !important; text-align: right; }
    .stTextArea textarea { direction: ltr !important; text-align: left !important; background-color: #1a1f26 !important; color: #ffffff !important; border: 1px solid #2b333e !important; border-radius: 8px; font-family: monospace; }
    .stButton button { background-color: #4f9dff !important; color: white !important; font-weight: bold !important; border-radius: 8px !important; width: 100%; border: none; transition: 0.3s; }
    .stButton button:hover { background-color: #3b82f6 !important; transform: translateY(-2px); }
    .stRadio > div { direction: rtl; text-align: right; }
    .stRadio label { color: #f3f7fb !important; }
    hr { border-color: #2b333e; }
    .stProgress > div > div > div > div { background-color: #4f9dff; }
    [data-testid="stMetricValue"] { color: #4f9dff !important; font-size: 2rem !important; }
    [data-testid="stMetricLabel"] { color: #a0aec0 !important; font-size: 1.1rem !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🎬 استوديو الأدلة الحركية (Kinetic Evidence)")
st.markdown("**محرك إنتاج فيديوهات وثائقية مدعوم بالذكاء الاصطناعي.** أدخل السكريبت الإنجليزي بالأسفل.")

st.markdown("---")

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📝 لوحة التحكم")
    script = st.text_area("نص السكريبت (English Script):", height=300, placeholder="Paste your English documentary script here...")
    
    if script.strip():
        word_count = len(script.split())
        expected_mins = word_count / 140.0
        vid_minutes = int(expected_mins)
        vid_seconds = int((expected_mins - vid_minutes) * 60)
        render_mins = max(1, int(expected_mins * 1.5) + 1)
        
        st.markdown("### 📊 الإحصائيات المتوقعة")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("عدد الكلمات", f"{word_count}")
        col_b.metric("مدة الفيديو", f"{vid_minutes}د {vid_seconds}ث")
        col_c.metric("وقت الرندر", f"~{render_mins} دقائق")
    
    st.markdown("---")
    st.markdown("### ⚙️ إعدادات الرندر")
    mode = st.radio("اختر نوع الرندر:", ["Preview (سريع - أول مشهدين)", "Final Render (فيديو كامل)"])
    
    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("🚀 بدء الرندر الآن")

with col2:
    st.subheader("📺 شاشة العرض")
    progress_bar = st.progress(0.0)
    status_text = st.empty()
    status_text.info("في انتظار بدء الرندر...")
    video_placeholder = st.empty()

def update_ui_progress(pct, msg):
    progress_bar.progress(min(float(pct / 100.0), 1.0))
    status_text.markdown(f"**الحالة الحالية:** {msg} `({pct:.2f}%)`")

if run_btn:
    if not script.strip():
        status_text.error("❌ يرجى إدخال السكريبت أولاً.")
    else:
        try:
            is_preview = "Preview" in mode
            result = render.run(script, preview=is_preview, use_llm=True, progress_callback=update_ui_progress)
            
            if result.get("ok"):
                status_text.success(f"✅ اكتمل الرندر بنجاح! مدة الفيديو النهائية: {result['total_duration_sec']:.1f} ثانية.")
                video_placeholder.video(result["output_mp4"])
            else:
                status_text.error(f"❌ فشل الرندر: {result.get('error')}")
        except Exception as e:
            status_text.error(f"⚠️ خطأ غير متوقع: {str(e)}")
