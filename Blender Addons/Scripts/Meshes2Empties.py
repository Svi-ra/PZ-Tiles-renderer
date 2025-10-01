#Meshes2Empties
bl_info = {
    "name": "Meshes2Empties",
    "author": "svi-ra",
    "version": (1, 1),
    "blender": (2, 80, 0),
    "location": "Object > Convert",
    "description": "Replaces selected objects with empties, preserving transforms",
    "category": "Object",
}

import bpy

class OBJECT_OT_convert_selected_to_empties(bpy.types.Operator):
    """Replace selected objects with empties (preserve transforms)"""
    bl_idname = "object.convert_selected_to_empties"
    bl_label = "Meshes2Empties"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = context.selected_objects.copy()

        for obj in selected_objects:
            # Create empty
            empty = bpy.data.objects.new(name=f"{obj.name}_Empty", object_data=None)
            empty.empty_display_size = 1
            empty.empty_display_type = 'PLAIN_AXES'

            # Copy transform
            empty.matrix_world = obj.matrix_world.copy()

            # Link empty to same collections
            for collection in obj.users_collection:
                collection.objects.link(empty)

            # Unlink and remove original object
            for collection in obj.users_collection:
                collection.objects.unlink(obj)
            bpy.data.objects.remove(obj)

        return {'FINISHED'}

# Добавляем в Object > Convert
def convert_menu_func(self, context):
    self.layout.operator(OBJECT_OT_convert_selected_to_empties.bl_idname, text="Convert to Empty")

def register():
    bpy.utils.register_class(OBJECT_OT_convert_selected_to_empties)
    bpy.types.VIEW3D_MT_object_convert.append(convert_menu_func)

def unregister():
    bpy.types.VIEW3D_MT_object_convert.remove(convert_menu_func)
    bpy.utils.unregister_class(OBJECT_OT_convert_selected_to_empties)

if __name__ == "__main__":
    register()
