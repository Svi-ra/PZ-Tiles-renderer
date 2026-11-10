#Bulk_export_Unity_FBX
bl_info = {
    "name": "Bulk Export Selected to FBX",
    "author": "Ваше Имя",
    "version": (1, 1),
    "blender": (2, 80, 0),
    "location": "F3 Search",
    "description": "Bulk export selected mesh objects to FBX with custom path",
    "category": "Export",
}

import bpy
import os

class EXPORT_OT_bulk_selected_fbx(bpy.types.Operator):
    """Bulk export selected mesh objects to FBX with custom path"""
    bl_idname = "export.bulk_selected_fbx"
    bl_label = "Bulk Export Selected to FBX"
    bl_options = {'REGISTER', 'UNDO'}

    export_path = bpy.props.StringProperty(
        name="Export Path",
        description="Folder where FBX files will be saved",
        subtype='DIR_PATH',
        default="//"
    )

    def execute(self, context):
        export_path = self.properties.export_path  # <- ключевой момент!
        export_folder = bpy.path.abspath(export_path)

        if not os.path.exists(export_folder):
            os.makedirs(export_folder)

        selected = context.selected_objects
        active = context.view_layer.objects.active

        for obj in selected:
            if obj.type == 'MESH':
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                context.view_layer.objects.active = obj

                filepath = os.path.join(export_folder, f"{obj.name}.fbx")

                bpy.ops.export_scene.fbx(
                    filepath=filepath,
                    use_selection=True,
                    path_mode='AUTO',
                    global_scale=1.0,
                    apply_unit_scale=True,
                    apply_scale_options='FBX_SCALE_UNITS',
                    axis_forward='-Z',
                    axis_up='Y',
                    bake_space_transform=True,
                    object_types={'MESH'},
                    use_mesh_modifiers=True,
                    mesh_smooth_type='FACE',
                    use_custom_props=False,
                    use_subsurf=False,
                    use_mesh_edges=False,
                    use_tspace=False,
                    colors_type='SRGB',
                    use_active_collection=False,
                    use_armature_deform_only=True,
                    add_leaf_bones=True,
                    primary_bone_axis='Y',
                    secondary_bone_axis='X',
                    armature_nodetype='NULL',
                )

                self.report({'INFO'}, f"Экспортировано: {filepath}")

        for obj in selected:
            obj.select_set(True)
        context.view_layer.objects.active = active

        return {'FINISHED'}


    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


def register():
    bpy.utils.register_class(EXPORT_OT_bulk_selected_fbx)

def unregister():
    bpy.utils.unregister_class(EXPORT_OT_bulk_selected_fbx)

if __name__ == "__main__":
    register()
