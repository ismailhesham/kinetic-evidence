from pipeline import director, visual_plan

def test_plain_scene_uses_card_last_resort(tmp_path):
    # هذا الاختبار يعتمد على وجود ffmpeg لتوليد الصورة
    # (يمكن تخطيه لو ffmpeg غير موجود)
    import shutil
    if not shutil.which("ffmpeg"):
        return
    from pipeline.renderer import scene_compositor
    sc = director.split_into_scenes("The rain continued through the long afternoon.", use_llm=False)[0]
    sc.visual_plan = visual_plan.build_visual_plan(sc)
    sc.narration.scene_duration_sec = 1.0
    media_result = {"primary": None, "fallback": {}}
    out = str(tmp_path / "scene.mp4")
    log = scene_compositor.compose_scene(sc, media_result, tmp_path, out)
    assert log["base_source"] == "card_last_resort"