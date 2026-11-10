bl_info = {
    "name": "Quick FBX Export Panel",
    "author": "Custom Script",
    "version": (1, 1),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Quick FBX Export",
    "description": "Export selected objects to FBX (per object or combined) from N-panel",
    "category": "Import-Export",
}

import bpy
import os
from bpy.props import StringProperty, EnumProperty


class QFBX_PT_panel(bpy.types.Panel):
    bl_label = "Quick FBX Export"
    bl_idname = "QFBX_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Quick FBX"

    def draw(self, context):
        layout = self.layout
        props = context.scene.qfbx_props

        layout.prop(props, "export_path")
        layout.prop(props, "export_mode")

        layout.operator("qfbx.export", text="Export FBX")


class QFBX_Props(bpy.types.PropertyGroup):
    export_path: StringProperty(
        name="Export Path",
        subtype="DIR_PATH",
        description="Folder to export FBX files"
    )

    export_mode: EnumProperty(
        name="Export Mode",
        description="Choose export mode",
        items=[
            ('SEPARATE', "Separate FBX per object", ""),
            ('COMBINED', "Single FBX (all objects)", "")
        ],
        default='SEPARATE'
    )


class QFBX_OT_export(bpy.types.Operator):
    bl_idname = "qfbx.export"
    bl_label = "Export Selected Objects"

    def execute(self, context):
        props = context.scene.qfbx_props
        export_path = bpy.path.abspath(props.export_path)

        if not os.path.exists(export_path):
            self.report({'ERROR'}, f"Path does not exist: {export_path}")
            return {'CANCELLED'}

        selected_objects = context.selected_objects

        if not selected_objects:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}

        if props.export_mode == 'SEPARATE':
            for obj in selected_objects:
                obj_path = os.path.join(export_path, f"{obj.name}.fbx")
                # временно оставляем только этот объект выделенным
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                context.view_layer.objects.active = obj

                bpy.ops.export_scene.fbx(
                    filepath=obj_path,
                    use_selection=True,
                    use_active_collection=False,
                    object_types={'MESH', 'EMPTY', 'ARMATURE'},
                    apply_unit_scale=True,
                    apply_scale_options='FBX_SCALE_UNITS',
                    use_space_transform=True,
                    bake_space_transform=True,
                    add_leaf_bones=True
                )

        else:  # COMBINED
            first_obj = selected_objects[0]
            combined_path = os.path.join(export_path, f"{first_obj.name}.fbx")

            # восстановим выделение
            bpy.ops.object.select_all(action='DESELECT')
            for obj in selected_objects:
                obj.select_set(True)
            context.view_layer.objects.active = first_obj

            bpy.ops.export_scene.fbx(
                filepath=combined_path,
                use_selection=True,
                use_active_collection=False,
                object_types={'MESH', 'EMPTY', 'ARMATURE'},
                apply_unit_scale=True,
                apply_scale_options='FBX_SCALE_UNITS',
                use_space_transform=True,
                bake_space_transform=True,
                add_leaf_bones=True
            )

        self.report({'INFO'}, "Export complete")
        return {'FINISHED'}


classes = [QFBX_PT_panel, QFBX_Props, QFBX_OT_export]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.qfbx_props = bpy.props.PointerProperty(type=QFBX_Props)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.qfbx_props


if __name__ == "__main__":
    register()
