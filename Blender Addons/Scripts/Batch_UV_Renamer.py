bl_info = {
    "name": "Batch UV Renamer",
    "author": "ChatGPT",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "UV Editor > Sidebar > UV Tools",
    "description": "Переименовывает все UV-карты всех выделенных объектов в указанное имя",
    "category": "UV",
}

import bpy

class UVTOOLS_PT_panel(bpy.types.Panel):
    bl_label = "UV Batch Renamer"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "UV Tools"

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        layout.prop(scn, "uv_map_target_name")
        layout.operator("uv.rename_all_uv_maps", icon='GROUP_UVS')


class UVTOOLS_OT_rename(bpy.types.Operator):
    bl_idname = "uv.rename_all_uv_maps"
    bl_label = "Переименовать UV карты"
    bl_description = "Переименовать все UV карты выделенных объектов"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        target_name = context.scene.uv_map_target_name.strip()
        if not target_name:
            self.report({'WARNING'}, "Имя UV карты не может быть пустым.")
            return {'CANCELLED'}

        renamed_count = 0

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            uv_layers = obj.data.uv_layers
            for uv in uv_layers:
                uv.name = target_name
                renamed_count += 1

        self.report({'INFO'}, f"Переименовано {renamed_count} UV-карт.")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(UVTOOLS_PT_panel)
    bpy.utils.register_class(UVTOOLS_OT_rename)
    bpy.types.Scene.uv_map_target_name = bpy.props.StringProperty(
        name="Новое имя UV карты",
        description="Это имя будет применено ко всем UV картам выделенных объектов",
        default="UVMap"
    )


def unregister():
    bpy.utils.unregister_class(UVTOOLS_PT_panel)
    bpy.utils.unregister_class(UVTOOLS_OT_rename)
    del bpy.types.Scene.uv_map_target_name


if __name__ == "__main__":
    register()
