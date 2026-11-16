import streamlit as st
import os
import json
import uuid
from pathlib import Path
from dotenv import load_dotenv
from pipeline import render

load_dotenv()

st.set_page_config(page_title="Kinetic Evidence Studio", layout="wide", page_icon="🎬")

# ستايل فخم مستوحى من Velvet Engine (أسود وذهبي)
VELVET_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&family=Playfair+Display:ital,wght@0,600;0,700;1,600&display=swap');

/* الخلفية العامة */
.stApp {
    background: radial-gradient(circle at top center, #14131a 0%, #070709 65%) !important;
    font-family: 'Cairo', sans-serif !important;
    color: #f4f0e8 !important;
}

/* العناوين */
h1, h2, h3 {
    font-family: 'Playfair Display', serif !important;
    color: #d4af37 !important;
}

/* الكروت */
.velvet-card {
    background: rgba(16, 16, 22, 0.85) !important;
    border: 1px solid rgba(255, 255, 255, 0.07) !important;
    border-radius: 14px !important;
    padding: 24px !important;
    margin-bottom: 20px;
}

/* شريط الإحصائيات */
.script-stats-bar {
    display: flex;
    justify-content: space-between;
    background: rgba(212, 175, 55, 0.06);
    border: 1px solid rgba(212, 175, 55, 0.2);
    border-radius: 10px;
    padding: 12px 20px;
    margin-top: 10px;
    font-size: 14px;
    color: #d8d2c7;
}
.script-stats-bar span b { color: #d4af37; font-size: 16px; }

/* مربع النص */
.stTextArea textarea {
    background-color: #0a0a0f !important;
    color: #f4f0e8 !important;
    border: 1px solid rgba(212, 175, 55, 0.3) !important;
    font-family: monospace !important;
}

/* زرار الرندر الذهبي */
.stButton button {
    background: linear-gradient(135deg, #e5c158 0%, #b88e22 100%) !important;
    color: #09090b !important;
    font-weight: 800 !important;
    font-size: 18px !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 16px 24px !important;
    width: 100%;
    transition: 0.3s;
}
.stButton button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(212, 175, 55, 0.4);
}

/* تنسيقات إضافية */
div[data-testid="stExpander"] {
    border: 1px solid rgba(212, 175, 55, 0.2) !important;
    background: rgba(16, 16, 22, 0.6) !important;
    border-radius: 10px !important;
}
div[data-testid="stMetricValue"] { color: #d4af37 !important; }
"""
st.markdown(f"<style>{VELVET_CSS}</style>", unsafe_allow_html=True)

# الهيدر الفخم
st.markdown("""
    <div style="text-align: center; padding: 20px; margin-bottom: 20px; background: linear-gradient(180deg, rgba(212,175,55,0.08) 0%, rgba(14,14,19,0.4) 100%); border: 1px solid rgba(212,175,55,0.28); border-radius: 16px;">
        <div style="display: inline-block; padding: 4px 14px; font-size: 12px; font-weight: 700; letter-spacing: 2px; color: #d4af37; border: 1px solid rgba(212,175,55,0.45); border-radius: 999px; background: rgba(212,175,55,0.08); margin-bottom: 10px;">
            KINETIC EVIDENCE ENGINE v1.0 • HYBRID
        </div>
        <h1 style="margin: 0; font-size: 38px; color: #f6f2eb;">KINETIC DOCUMENTARY STUDIO</h1>
        <p style="color: #9e988e; font-size: 15px; margin-top: 8px;">محرك إنتاج الأفلام الوثائقية الاستقصائية — أدلة بصرية، موشن جرافيك، ومكساج صوتي احترافي</p>
    </div>
""", unsafe_allow_html=True)

# تقسيم الشاشة
col1, col2 = st.columns([7, 4], gap="large")

with col1:
    st.markdown('<div class="velvet-card">', unsafe_allow_html=True)
    st.markdown("### ✍️ مساحة السكريبت الوثائقي (Script Workspace)")
    
    script = st.text_area("English Script", height=350, placeholder="Paste your continuous English documentary script here...", label_visibility="collapsed")
    
    # شريط الإحصائيات الديناميكي
    stats_placeholder = st.empty()
    
    def update_stats(text):
        words = len(text.split()) if text.strip() else 0
        mins = round(words / 140.0, 1)
        scenes = max(1, round(words / 25.0)) if words > 0 else 0
        stats_placeholder.markdown(f"""
        <div class="script-stats-bar">
            <span>📝 الكلمات: <b>{words:,}</b></span>
            <span>⏱️ المدة المتوقعة: <b>~{mins}</b> دقيقة</span>
            <span>🎞️ المشاهد المقدرة: <b>~{scenes}</b> مشهد</span>
        </div>
        """, unsafe_allow_html=True)
    
    update_stats(script)
    script_input = st.empty() # placeholder just to catch changes
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_mode, col_dur = st.columns(2)
    with col_mode:
        mode = st.radio("وضع الريندر", ["Final Render", "Preview Render"])
    with col_dur:
        preview_dur = st.slider("مدة المعاينة السريعة (ثانية)", 15, 90, 25, step=5)
        
    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("🎬 بدء إنتاج الفيلم الوثائقي (Produce Documentary)")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="velvet-card">', unsafe_allow_html=True)
    st.markdown("### 🎛️ إعدادات الصوت والإخراج")
    
    voice_name = st.radio("نبرة المعلق الصوتي (TTS)", [
        "🇬🇧 البريطاني الفخم (George)", 
        "🇺🇸 الأمريكي العميق (Michael)",
        "🇬🇧 البريطاني الروائي (Daniel)"
    ])
    
    with st.expander("🎨 إعدادات الصورة والصوت والمصادر", expanded=False):
        style = st.selectbox("النمط البصري", ["Investigative Essay", "Archival Historical", "Natural Environment"])
        res = st.selectbox("دقة الفيديو", ["1080p Full HD", "720p HD Fast", "480p Quick Draft"])
        providers = st.multiselect("مصادر الميديا", ["pixabay", "wikimedia", "internet_archive", "nasa", "ai_generated"], default=["pixabay", "wikimedia", "ai_generated"])
        enable_captions = st.checkbox("تفعيل الترجمة السفلية", value=False)
        enable_music = st.checkbox("تفعيل الموسيقى الخلفية", value=True)
        enable_ai_images = st.checkbox("السماح بتوليد صور AI (كحل أخير)", value=True)

    with st.expander("🔑 مفاتيح الـ API", expanded=True):
        deepseek_key = st.text_input("مفتاح DeepSeek API", type="password", value=os.getenv("DEEPSEEK_API_KEY", ""))
        pixabay_key = st.text_input("مفتاح Pixabay API", type="password", value=os.getenv("PIXABAY_API_KEY", ""))
    st.markdown('</div>', unsafe_allow_html=True)

# شاشة العرض والنتائج
st.markdown("<hr style='border-color: rgba(212,175,55,0.2);'>", unsafe_allow_html=True)
st.markdown("### 📽️ شاشة العرض النهائية والملفات")

res_col1, res_col2 = st.columns([7, 4])

with res_col1:
    video_placeholder = st.empty()
    status_text = st.empty()

with res_col2:
    st.markdown("#### 📂 ملفات المشروع")
    st.info("ستظهر ملفات JSON الخاصة بالمشاهد والميديا والتقرير هنا بعد اكتمال الرندر.")
    json_file = st.empty()
    report_file = st.empty()

# تحديث الإحصائيات لما النص يتغير
script_input.text_area("hidden", key="update_trigger", on_change=update_stats, args=[script], label_visibility="collapsed")

# دالة الرندر
if run_btn:
    if not script.strip():
        status_text.error("❌ يرجى إدخال السكريبت أولاً.")
    else:
        # تحديث المفاتيح في البيئة
        if deepseek_key: os.environ["DEEPSEEK_API_KEY"] = deepseek_key
        if pixabay_key: os.environ["PIXABAY_API_KEY"] = pixabay_key
        os.environ["ALLOW_AI_IMAGES"] = "true" if enable_ai_images else "false"
        
        with st.spinner("⏳ جاري إنتاج الفيلم الوثائقي... (قد يستغرق وقتاً طويلاً)"):
            try:
                # تمرير الإعدادات للـ Pipeline
                is_preview = "Preview" in mode
                
                # هنا بنشغل البايبلاين (كمثال بنبعت المتغيرات)
                result = render.run(
                    script_text=script, 
                    preview=is_preview, 
                    use_llm=True,
                    # ممكن نضيف بارامترات تانية للـ render.run في المستقبل
                )
                
                if result.get("ok"):
                    status_text.success(f"✅ اكتمل الإنتاج! (Job ID: {result.get('ws', 'N/A')})")
                    video_placeholder.video(result["output_mp4"])
                    
                    # عرض الملفات
                    report_path = result.get("technical_report_path")
                    if report_path and Path(report_path).exists():
                        with open(report_path, "rb") as f:
                            report_file.download_button("⬇️ تحميل التقرير التقني (JSON)", f, file_name="technical_report.json")
                else:
                    status_text.error(f"❌ فشل الرندر: {result.get('error')}")
            except Exception as e:
                status_text.error(f"⚠️ خطأ غير متوقع: {str(e)}")
