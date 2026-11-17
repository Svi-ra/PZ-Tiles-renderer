bl_info = {
    "name": "Camera Background Nearest (Texel Fetch)",
    "author": "OpenAI",
    "version": (1, 0, 0),
    "blender": (5, 0, 1),
    "location": "Camera Data Properties > NN Camera Background",
    "description": "Draw a camera background with exact nearest-pixel sampling in the 3D viewport",
    "category": "3D View",
}

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

_HANDLER = None
_SHADER = None
_TEXTURE_CACHE = {}
_ORIGINAL_BG_VISIBILITY = {}

def _redraw_viewports(self, context):
    wm = context.window_manager
    if not wm:
        return
    for window in wm.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

_VERTEX_SHADER = """
void main() {
    gl_Position = viewProjectionMatrix * vec4(pos, 1.0);
    uv_interp = texCoord;
}
"""

_FRAGMENT_SHADER = """
void main() {
    vec2 viewport_pos = gl_FragCoord.xy - comparison_origin;
    int axis = comparison_axis;
    if (viewport_pos[axis] < comparison_size[axis] * comparison_position) {
        discard;
    }
    vec2 uv = clamp(uv_interp, vec2(0.0), vec2(0.99999994));
    ivec2 p = ivec2(floor(uv * vec2(image_size)));
    vec4 c = texelFetch(image, p, 0);
    vec3 srgb = mix(12.92 * c.rgb,
                    1.055 * pow(max(c.rgb, vec3(0.0)), vec3(1.0 / 2.4)) - 0.055,
                    step(vec3(0.0031308), c.rgb));
    FragColor = vec4(srgb, c.a * opacity);
}
"""


def _get_shader():
    global _SHADER
    if _SHADER is None:
        interface = gpu.types.GPUStageInterfaceInfo("nn_camera_background_iface")
        interface.smooth('VEC2', "uv_interp")
        info = gpu.types.GPUShaderCreateInfo()
        info.push_constant('MAT4', "viewProjectionMatrix")
        info.push_constant('IVEC2', "image_size")
        info.push_constant('FLOAT', "opacity")
        info.push_constant('VEC2', "comparison_origin")
        info.push_constant('VEC2', "comparison_size")
        info.push_constant('FLOAT', "comparison_position")
        info.push_constant('INT', "comparison_axis")
        info.sampler(0, 'FLOAT_2D', "image")
        info.vertex_in(0, 'VEC3', "pos")
        info.vertex_in(1, 'VEC2', "texCoord")
        info.vertex_out(interface)
        info.fragment_out(0, 'VEC4', "FragColor")
        info.vertex_source(_VERTEX_SHADER)
        info.fragment_source(_FRAGMENT_SHADER)
        _SHADER = gpu.shader.create_from_info(info)
    return _SHADER


def _get_texture(image):
    key = (image.as_pointer(), tuple(image.size), image.is_dirty)
    texture = _TEXTURE_CACHE.get(key)
    if texture is None:
        # Drop stale entries for this image after edits/reloads.
        ptr = image.as_pointer()
        for old_key in list(_TEXTURE_CACHE):
            if old_key[0] == ptr:
                del _TEXTURE_CACHE[old_key]
        texture = gpu.texture.from_image(image)
        _TEXTURE_CACHE[key] = texture
    return texture


def _draw_background():
    context = bpy.context
    area = context.area
    if not area or area.type != 'VIEW_3D':
        return
    space = area.spaces.active
    rv3d = space.region_3d
    if rv3d.view_perspective != 'CAMERA':
        return
    scene = context.scene
    camera_obj = scene.camera
    if not camera_obj or camera_obj.type != 'CAMERA':
        return
    cam = camera_obj.data
    slot = next((s for s in cam.background_images
                 if s.show_background_image and s.source == 'IMAGE' and s.image), None)
    if slot is None:
        return
    image = slot.image
    if image.size[0] < 1 or image.size[1] < 1:
        return

    frame = cam.view_frame(scene=scene)
    z0 = abs(frame[0].z)
    depth = cam.clip_end * 0.98
    # Perspective frame coordinates describe a plane at z0, so scale the
    # frame outward to preserve its camera-view coverage at the chosen depth.
    # Orthographic frame dimensions are independent of depth and must remain
    # unchanged when placing the image plane farther down the camera axis.
    if cam.type == 'ORTHO':
        factor = 1.0
    else:
        if z0 <= 1e-8:
            return
        factor = depth / z0
    xs = [v.x for v in frame]
    ys = [v.y for v in frame]
    left, right = min(xs), max(xs)
    bottom, top = min(ys), max(ys)
    frame_w, frame_h = right - left, top - bottom
    if frame_w <= 0 or frame_h <= 0:
        return

    iw, ih = image.size
    pixel_aspect = image.display_aspect
    frame_aspect = frame_w / frame_h
    image_aspect = (iw * pixel_aspect.x) / (ih * pixel_aspect.y)
    # Respect the camera background fit/crop/stretch mode.
    u0, v0, u1, v1 = 0.0, 0.0, 1.0, 1.0
    draw_left, draw_right, draw_bottom, draw_top = left, right, bottom, top
    if slot.frame_method == 'FIT':
        if image_aspect > frame_aspect:
            h = frame_w / image_aspect
            draw_bottom, draw_top = (bottom + top - h) * 0.5, (bottom + top + h) * 0.5
        else:
            w = frame_h * image_aspect
            draw_left, draw_right = (left + right - w) * 0.5, (left + right + w) * 0.5
    elif slot.frame_method == 'CROP':
        if image_aspect > frame_aspect:
            visible = frame_aspect / image_aspect
            u0, u1 = (1.0 - visible) * 0.5, (1.0 + visible) * 0.5
        else:
            visible = image_aspect / frame_aspect
            v0, v1 = (1.0 - visible) * 0.5, (1.0 + visible) * 0.5

    # Match Blender's camera background transform: frame fit/crop, slot scale,
    # offset, rotation, and flips. Camera view_frame is in camera-local units.
    center_x, center_y = (left + right) * 0.5, (bottom + top) * 0.5
    offset_x = slot.offset.x * min(1.0, frame_aspect)
    offset_y = (slot.offset.y / max(1.0, frame_aspect) *
                (image_aspect / frame_aspect))
    angle = -slot.rotation
    cos_a, sin_a = __import__('math').cos(angle), __import__('math').sin(angle)
    local = ((draw_right, draw_top), (draw_right, draw_bottom),
             (draw_left, draw_bottom), (draw_left, draw_top))
    verts = []
    for x, y in local:
        dx = (x - center_x) * slot.scale
        dy = (y - center_y) * slot.scale
        rx = dx * cos_a - dy * sin_a + center_x + offset_x
        ry = dx * sin_a + dy * cos_a + center_y + offset_y
        verts.append(camera_obj.matrix_world @ Vector((rx * factor, ry * factor, -depth)))
    if slot.use_flip_x:
        u0, u1 = 1.0 - u1, 1.0 - u0
    if slot.use_flip_y:
        v0, v1 = 1.0 - v1, 1.0 - v0
    uvs = ((u1, v1), (u1, v0), (u0, v0), (u0, v1))
    shader = _get_shader()
    batch = batch_for_shader(shader, 'TRI_FAN', {"pos": verts, "texCoord": uvs})
    viewport = gpu.state.viewport_get()
    view_projection = context.region_data.perspective_matrix
    frame_screen = []
    for point in frame:
        world_point = camera_obj.matrix_world @ Vector((point.x * factor,
                                                        point.y * factor,
                                                        -depth))
        clip_point = view_projection @ world_point.to_4d()
        ndc_x, ndc_y = clip_point.x / clip_point.w, clip_point.y / clip_point.w
        frame_screen.append((viewport[0] + (ndc_x + 1.0) * viewport[2] * 0.5,
                             viewport[1] + (ndc_y + 1.0) * viewport[3] * 0.5))
    comparison_origin = (min(p[0] for p in frame_screen),
                         min(p[1] for p in frame_screen))
    comparison_size = (max(p[0] for p in frame_screen) - comparison_origin[0],
                       max(p[1] for p in frame_screen) - comparison_origin[1])

    gpu.state.depth_test_set(
        'NONE' if scene.nn_camera_background_foreground else 'LESS_EQUAL')
    gpu.state.depth_mask_set(False)
    gpu.state.blend_set('ALPHA')
    try:
        shader.bind()
        shader.uniform_float("viewProjectionMatrix", view_projection)
        shader.uniform_sampler("image", _get_texture(image))
        shader.uniform_int("image_size", (iw, ih))
        shader.uniform_float("opacity", slot.alpha)
        shader.uniform_float("comparison_origin", comparison_origin)
        shader.uniform_float("comparison_size", comparison_size)
        shader.uniform_float("comparison_position", scene.nn_camera_background_split)
        shader.uniform_int("comparison_axis",
                           0 if scene.nn_camera_background_axis == 'VERTICAL' else 1)
        batch.draw(shader)
    finally:
        gpu.state.blend_set('NONE')
        gpu.state.depth_mask_set(True)
        gpu.state.depth_test_set('NONE')


class CAMERA_OT_nn_background_toggle(bpy.types.Operator):
    bl_idname = "camera.nn_background_toggle"
    bl_label = "Toggle NN Camera Background"
    bl_description = "Show or hide the custom nearest-sampled camera background"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global _HANDLER
        scene = context.scene
        if not scene.camera:
            self.report({'ERROR'}, "В сцене не назначена активная камера")
            return {'CANCELLED'}
        if _HANDLER is None:
            cam = scene.camera.data
            _ORIGINAL_BG_VISIBILITY[cam.as_pointer()] = cam.show_background_images
            cam.show_background_images = False
            _HANDLER = bpy.types.SpaceView3D.draw_handler_add(
                _draw_background, (), 'WINDOW', 'POST_VIEW')
            scene.nn_camera_background_enabled = True
            self.report({'INFO'}, "NN-фон включён для Camera View")
        else:
            _remove_handler()
            scene.nn_camera_background_enabled = False
            self.report({'INFO'}, "NN-фон выключен")
        return {'FINISHED'}


def _remove_handler():
    global _HANDLER, _SHADER, _TEXTURE_CACHE
    if _HANDLER is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_HANDLER, 'WINDOW')
        _HANDLER = None
    for obj in bpy.data.objects:
        if obj.type == 'CAMERA':
            was_visible = _ORIGINAL_BG_VISIBILITY.get(obj.data.as_pointer())
            if was_visible is not None:
                obj.data.show_background_images = was_visible
    _ORIGINAL_BG_VISIBILITY.clear()
    _TEXTURE_CACHE.clear()
    _SHADER = None


class CAMERA_PT_nn_background(bpy.types.Panel):
    bl_label = "NN Camera Background"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        return context.camera is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        enabled = getattr(scene, "nn_camera_background_enabled", False)
        layout.operator(CAMERA_OT_nn_background_toggle.bl_idname,
                        text="Disable NN Background" if enabled else "Enable NN Background",
                        icon='HIDE_OFF' if enabled else 'IMAGE')
        layout.prop(context.scene, "nn_camera_background_axis", expand=True)
        layout.prop(context.scene, "nn_camera_background_split",
                    text="Comparison", slider=True)
        layout.prop(context.scene, "nn_camera_background_foreground",
                    text="Draw in Foreground")
        layout.label(text="Uses texelFetch: source texels are sampled directly.", icon='INFO')
        layout.label(text="First visible static Image slot; Camera View only.")


_CLASSES = (CAMERA_OT_nn_background_toggle, CAMERA_PT_nn_background)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.nn_camera_background_enabled = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.nn_camera_background_foreground = bpy.props.BoolProperty(
        name="Draw in Foreground",
        description="Draw the background image over scene geometry",
        default=False,
        update=_redraw_viewports,
    )
    bpy.types.Scene.nn_camera_background_axis = bpy.props.EnumProperty(
        name="Comparison Direction",
        description="Choose whether the comparison divider runs vertically or horizontally",
        items=(
            ('VERTICAL', "Vertical", "Hide the image to the left of the divider"),
            ('HORIZONTAL', "Horizontal", "Hide the image below the divider"),
        ),
        default='VERTICAL',
        update=_redraw_viewports,
    )
    bpy.types.Scene.nn_camera_background_split = bpy.props.FloatProperty(
        name="Comparison",
        description="Position of the comparison divider; the image remains visible on the right or upper side",
        default=0.5,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
        update=_redraw_viewports,
    )


def unregister():
    _remove_handler()
    del bpy.types.Scene.nn_camera_background_enabled
    del bpy.types.Scene.nn_camera_background_foreground
    del bpy.types.Scene.nn_camera_background_axis
    del bpy.types.Scene.nn_camera_background_split
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
