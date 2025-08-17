from bpy.types import Operator
from bpy.props import (EnumProperty, FloatProperty)
from bpy_extras.io_utils import (ImportHelper, axis_conversion)
import bpy
from mathutils import Matrix
from .xfile_importer import load

bl_info = {
    "name": "DirectX XFile format",
    "author": "oguna",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "category": "Import-Export",
}


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.


class ImportSomeData(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "import_scene.x"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import DirectX XFile"

    # ImportHelper mixin class uses this
    filename_ext = ".x"

    scale: FloatProperty(
        name="Scale",
        default=1.0,
        min=0.001,
        soft_min=0.01,
        soft_max=100.0,
        precision=3,
    )

    forward_axis: EnumProperty(
        name="Forward Axis",
        items=[
            ('X', "X", ""),
            ('Y', "Y", ""),
            ('Z', "Z", ""),
            ('-X', "-X", ""),
            ('-Y', "-Y", ""),
            ('-Z', "-Z", ""),
        ],
        default='Z',
    )

    up_axis: EnumProperty(
        name="Up Axis",
        items=[
            ('X', "X", ""),
            ('Y', "Y", ""),
            ('Z', "Z", ""),
            ('-X', "-X", ""),
            ('-Y', "-Y", ""),
            ('-Z', "-Z", ""),
        ],
        default='Y',
    )

    def execute(self, context):
        orientation_matrix = axis_conversion(
            from_forward=self.forward_axis,
            from_up=self.up_axis,
        ).to_4x4()
        scale_matrix = Matrix.Scale(self.scale, 4)
        global_matrix = orientation_matrix @ scale_matrix
        load(self.filepath, global_matrix)
        return {'FINISHED'}

# Only needed if you want to add into a dynamic menu


def menu_func_import(self, context):
    self.layout.operator(ImportSomeData.bl_idname, text="DirectX XFile (.x)")

# Register and add to the "file selector" menu (required to use F3 search "Text Import Operator" for quick access)


def register():
    bpy.utils.register_class(ImportSomeData)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportSomeData)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()
