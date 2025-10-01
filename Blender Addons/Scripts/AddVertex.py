bl_info = {
    "name": "Add Single Vertex",
    "author": "OpenAI / ChatGPT",
    "version": (1, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Add > Mesh > Single Vertex",
    "description": "Adds a mesh with a single vertex and enters edit mode",
    "category": "Add Mesh",
}

import bpy
import bmesh
from bpy.types import Operator
from bpy.utils import register_class, unregister_class

class MESH_OT_add_single_vertex(Operator):
    bl_idname = "mesh.add_single_vertex"
    bl_label = "Add Single Vertex"
    bl_description = "Create a mesh with a single vertex and enter edit mode"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Создание меша с одной вершиной
        mesh = bpy.data.meshes.new("SingleVertex")
        obj = bpy.data.objects.new("SingleVertex", mesh)
        context.collection.objects.link(obj)

        bm = bmesh.new()
        bm.verts.new((0.0, 0.0, 0.0))
        bm.to_mesh(mesh)
        bm.free()

        # Установка объекта на курсор
        obj.location = context.scene.cursor.location

        # Сделать его активным и выбранным
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        # Перейти в режим редактирования
        bpy.ops.object.mode_set(mode='EDIT')

        # Включить выбор по вершинам
        bpy.context.tool_settings.mesh_select_mode[:] = (True, False, False)

        # Выделить вершину
        bpy.ops.mesh.select_all(action='SELECT')

        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(MESH_OT_add_single_vertex.bl_idname, icon='VERTEXSEL')

classes = (MESH_OT_add_single_vertex,)

def register():
    for cls in classes:
        register_class(cls)
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)

def unregister():
    for cls in classes:
        unregister_class(cls)
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)

if __name__ == "__main__":
    register()
