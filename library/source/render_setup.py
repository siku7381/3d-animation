"""House render settings: Cycles on the Apple GPU (Metal), 1920x1080, 24 fps, AgX.

Used by the library builder (so every library file renders on its own) and by scene
render scripts. GPU device choice lives in user preferences, not in the .blend, so
call use_metal_gpu() in every render process.
"""
import bpy

FPS = 24
RES = (1920, 1080)


def use_metal_gpu():
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    metal = [d for d in prefs.devices if d.type == 'METAL']
    if not metal:
        raise RuntimeError("no Metal GPU device available to Cycles")
    for d in prefs.devices:
        d.use = d.type == 'METAL'
    bpy.context.scene.cycles.device = 'GPU'
    return [d.name for d in metal]


def render_settings(scene=None, samples=384, res=RES):
    sc = scene or bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'GPU'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.012
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    sc.cycles.max_bounces = 8
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 6
    sc.cycles.transparent_max_bounces = 16
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.blur_glossy = 1.0
    sc.cycles_curves.shape = 'THICK'
    sc.cycles_curves.subdivisions = 2
    sc.render.use_persistent_data = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_depth = '16'
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0
