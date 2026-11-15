"""Arabic Gradio UI — Pro Studio Version with Background Rendering."""
import threading
import gradio as gr
import os
from pathlib import Path
from pipeline import render
from pipeline import demo as demo_mod

# حالة الرندر عشان نتابعها من غير ما نقفل الصفحة
RENDER_STATE = {"is_running": False, "result": None}

def _do_analyze(script):
    from pipeline import director
    if not script.strip():
        return "❌ السكريبت فارغ.", ""
    scenes = director.split_into_scenes(script)
    plan = "\n\n".join(
        f"**مشهد {s.scene_id}** [{s.beat_type}]:\n{s.narration.original_narration}"
        for s in scenes
    )
    return f"✅ تم تحليل {len(scenes)} مشهد بنجاح.", plan

def _do_render_bg(script, preview, use_llm, ai_images):
    RENDER_STATE["is_running"] = True
    RENDER_STATE["result"] = None
    os.environ["ALLOW_AI_IMAGES"] = "true" if ai_images else "false"
    
    try:
        result = render.run(script, preview=preview, use_llm=use_llm,
                            max_scenes=2 if preview else None)
        RENDER_STATE["result"] = result
    except Exception as e:
        RENDER_STATE["result"] = {"ok": False, "error": str(e)}
    finally:
        RENDER_STATE["is_running"] = False

def _start_render(script, preview, use_llm, ai_images):
    if not script.strip():
        return "❌ السكريبت فارغ.", None, ""
    if RENDER_STATE["is_running"]:
        return "⏳ يوجد رندر قيد التنفيذ بالفعل... اضغط تحديث الحالة.", None, ""
    
    # ابدأ الرندر في الخلفية
    t = threading.Thread(target=_do_render_bg, args=(script, preview, use_llm, ai_images))
    t.daemon = True
    t.start()
    
    return "🚀 بدأ الرندر في الخلفية... (قد يستغرق وقتاً طويلاً للفيديوهات الطويلة)", None, ""

def _check_status():
    if RENDER_STATE["is_running"]:
        return "⏳ جاري الرندر... (قد يستغرق عدة دقائق أو ساعات، اضغط تحديث الحالة باستمرار)", None, ""
        
    res = RENDER_STATE["result"]
    if not res:
        return "لا يوجد رندر سابق أو لم يبدأ بعد.", None, ""
        
    if not res.get("ok"):
        return f"❌ فشل الرندر: {res.get('error')}", None, str(res)
        
    out_file = res["output_mp4"]
    status = (f"✅ اكتمل الرندر!\n"
              f"⏱️ المدة: {res['total_duration_sec']:.1f} ثانية\n"
              f"🎬 عدد المشاهد: {res['scene_count']}")
              
    report_text = ""
    try:
        report_path = Path(res['technical_report_path'])
        if report_path.exists():
            report_text = report_path.read_text(encoding="utf-8")[:2000] + "\n...(مختصر)"
    except Exception:
        pass
        
    return status, out_file, report_text

def _do_demo():
    try:
        demo_mod.main()
        path = "outputs/demo.mp4"
        if os.path.exists(path):
            return "✅ تم إنشاء الديمو (أوفلاين).", path
    except Exception:
        pass
    return "❌ فشل إنشاء الديمو.", None


# Custom Dark Theme
custom_theme = gr.themes.Base(
    primary_hue="blue",
    secondary_hue="slate",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Cairo"), "sans-serif"],
).set(
    body_background_fill="#0f1216",
    block_background_fill="#1a1f26",
    block_border_width="1px",
    block_border_color="#2b333e",
    input_background_fill="#0f1216",
    button_primary_background_fill="#4f9dff",
    button_primary_text_color="white",
)

with gr.Blocks(rtl=True, title="Kinetic Evidence Studio", theme=custom_theme) as ui:
    
    gr.Markdown(
        """
        # 🎬 استوديو الأدلة الحركية (Kinetic Evidence)
        **محرك إنتاج فيديوهات وثائقية مدعوم بالذكاء الاصطناعي.**
        أدخل السكريبت الإنجليزي، وسيقوم المحرك بإنشاء الفيديو، الصوت، والمؤثرات.
        """
    )
    
    with gr.Row():
        # --- Left Column: Input & Controls ---
        with gr.Column(scale=1, min_width=400):
            script_in = gr.Textbox(
                label="📝 سكريبت الفيديو (إنجليزي)", 
                lines=12,
                placeholder="Paste your English documentary script here...",
                show_copy_button=True,
            )
            
            with gr.Accordion("⚙️ إعدادات متقدمة", open=False):
                use_llm_cb = gr.Checkbox(label="استخدام DeepSeek (يتطلب مفتاح)", value=True)
                ai_images_cb = gr.Checkbox(label="السماح بتوليد صور AI (كحل أخير)", value=False)
            
            gr.Markdown("---")
            
            with gr.Row():
                btn_analyze = gr.Button("🔍 تحليل السكريبت", variant="secondary")
                btn_demo = gr.Button("▶️ ديمو سريع", variant="secondary")
                
            with gr.Row():
                btn_preview = gr.Button("🎞️ Preview (أول مشهدين)", variant="primary")
                btn_final = gr.Button("🚀 رندر نهائي", variant="primary", scale=2)
                
            with gr.Row():
                btn_status = gr.Button("🔄 تحديث الحالة", variant="secondary", scale=1)

        # --- Right Column: Output & Status ---
        with gr.Column(scale=2):
            video_out = gr.Video(
                label="🎥 الفيديو الناتج", 
                interactive=False,
                format="mp4",
            )
            
            status_out = gr.Textbox(
                label="📊 حالة النظام", 
                lines=3, 
                interactive=False,
            )
            
            with gr.Accordion("📋 تقرير الإنتاج التقني", open=False):
                report_out = gr.Textbox(
                    label="Technical Report", 
                    lines=10, 
                    interactive=False
                )
                
            with gr.Accordion("🎬 خطة المشاهد (Scene Plan)", open=False):
                plan_out = gr.Textbox(
                    label="Scene Breakdown", 
                    lines=10, 
                    interactive=False
                )

    # --- Event Handlers ---
    btn_analyze.click(_do_analyze, inputs=[script_in], outputs=[status_out, plan_out])
    
    btn_preview.click(
        lambda s, u, a: _start_render(s, True, u, a), 
        inputs=[script_in, use_llm_cb, ai_images_cb], 
        outputs=[status_out, video_out, report_out]
    )
    
    btn_final.click(
        lambda s, u, a: _start_render(s, False, u, a), 
        inputs=[script_in, use_llm_cb, ai_images_cb], 
        outputs=[status_out, video_out, report_out]
    )
    
    btn_status.click(_check_status, outputs=[status_out, video_out, report_out])
    btn_demo.click(_do_demo, outputs=[status_out, video_out])


if __name__ == "__main__":
    ui.launch(server_name="0.0.0.0", server_port=7860, show_error=True)