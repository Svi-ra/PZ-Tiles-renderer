bl_info = {
    "name": "Sync Mesh Name with Object Name",
    "blender": (2, 80, 0),
    "category": "Object",
    "author": "Your Name",
    "description": "Renames mesh data to match the names of selected objects",
}

import bpy

class OBJECT_OT_sync_mesh_name_to_object(bpy.types.Operator):
    bl_idname = "object.sync_mesh_name_to_object"
    bl_label = "Sync Mesh Name with Object"
    bl_description = "Renames mesh data to match the object's name for all selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        count = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data:
                mesh = obj.data
                old_name = mesh.name
                mesh.name = obj.name
                self.report({'INFO'}, f"{old_name} → {mesh.name}")
                count += 1
        self.report({'INFO'}, f"Updated {count} mesh name(s)")
        return {'FINISHED'}

def outliner_menu_func(self, context):
    layout = self.layout
    layout.separator()
    layout.operator(OBJECT_OT_sync_mesh_name_to_object.bl_idname)

def register():
    bpy.utils.register_class(OBJECT_OT_sync_mesh_name_to_object)
    bpy.types.OUTLINER_MT_context_menu.append(outliner_menu_func)

def unregister():
    bpy.types.OUTLINER_MT_context_menu.remove(outliner_menu_func)
    bpy.utils.unregister_class(OBJECT_OT_sync_mesh_name_to_object)

if __name__ == "__main__":
    register()
