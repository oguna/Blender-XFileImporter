import sys
import struct
import array
from XFileHelper import *
from XFileParser import *
from bpy_extras.image_utils import load_image
import bpy
import os

if bpy.ops.object.mode_set.poll():
    bpy.ops.object.mode_set(mode='OBJECT')

if bpy.ops.object.select_all.poll():
    bpy.ops.object.select_all(action='DESELECT')
		
		
print('Hello World')
filepath = 'XFilePath'
basepath = os.path.dirname(filepath)
infile = open(filepath,'br')
buffer = infile.read()
parser = XFileParser(buffer)
oldScene = parser.getImportedData()

if oldScene.globalMeshes:
    oldMesh = oldScene.globalMeshes[0]
else:
    oldMesh = oldScene.rootNode.children[0].meshes[0]
    
# create mesh
scene = bpy.context.scene
mesh = bpy.data.meshes.new('MyMesh')
obj_mesh = bpy.data.objects.new('MyObj',mesh)
scene.objects.link(obj_mesh)
scene.update()

# vertex position and indices
faces = []
for i in oldMesh.posFaces:
    faces.append(tuple(i.indices))
mesh.from_pydata(oldMesh.positions, [], faces)
# vertex normal
print('numNormals = '+str(len(oldMesh.normals)))
if len(oldMesh.normals) > 0:
    for i,v in enumerate(mesh.vertices):
        v.normal = oldMesh.normals[i]
# add vertex
#mesh.vertices.add(len(oldMesh.positions))
#for i in range(len(oldMesh.positions)):
#    mesh.vertices[i].co = oldMesh.positions[i]
#    mesh.vertices[i].normal = oldMesh.normals[i]
#mesh.update()

# add face
#poly_count = len(oldMesh.posFaces)
#mesh.polygons.add(poly_count)
#mesh.polygons.foreach_set("loop_start",range(0, poly_count * 3 , 3))
#mesh.polygons.foreach_set("loop_total",(3,) * poly_count)
#mesh.polygons.foreach_set("use_smooth",(True,)* poly_count)
#mesh.polygons.foreach_set(poly_count*3)
#for i in range(poly_count):
#    mesh.loops[i*3+0].vertex_index = oldMesh.posFaces[i].indices[0]
#    mesh.loops[i*3+1].vertex_index = oldMesh.posFaces[i].indices[1]
#    mesh.loops[i*3+2].vertex_index = oldMesh.posFaces[i].indices[2]#!! NaRaBi KaERu
mesh.update()

# add textures
texture_dic = {}
for oldMat in oldMesh.materials:
    if oldMat.textures:
        texEntry = oldMat.textures[0]
        if not texEntry.name:
            continue
        tex_path = os.path.join(basepath,texEntry.name.decode())
        tex_name = texEntry.name.decode()
        bpy.ops.image.open(filepath=tex_path)
        texture_dic[tex_name] = bpy.data.textures.new(os.path.basename(tex_path),type='IMAGE')
        texture_dic[tex_name].image = bpy.data.images[os.path.basename(tex_name)]
        # use alpha
        texture_dic[tex_name].image.use_alpha = True
        texture_dic[tex_name].image.alpha_mode = 'PREMUL'
mesh.update()

# add material
for oldMat in oldMesh.materials:
    temp_material = bpy.data.materials.new(oldMat.name)
    temp_material.diffuse_color = oldMat.diffuse[0:3]
    temp_material.alpha = oldMat.diffuse[3]
    temp_material.specular_color = oldMat.specular
    temp_material.specular_hardness = oldMat.specularExponent
    temp_material['Ambient'] = oldMat.emissive
    temp_material.use_transparency = True

    mesh.materials.append(temp_material)

    # texture
    if oldMat.textures:
        texEntry = oldMat.textures[0]
        if temp_material.texture_slots[0] == None:
            temp_material.texture_slots.add()
        temp_material.texture_slots[0].texture = texture_dic[texEntry.name.decode()]
        temp_material.texture_slots[0].texture_coords = "UV"
        temp_material.texture_slots[0].uv_layer = "UV_Data"
        # MMD Settings
        temp_material.texture_slots[0].use_map_color_diffuse = True
        temp_material.texture_slots[0].use_map_alpha = True
        temp_material.texture_slots[0].blend_type = 'MULTIPLY'
        

# set material & uv
if mesh.uv_textures.active_index < 0:
    mesh.uv_textures.new("UV_Data")
mesh.uv_textures.active_index = 0
uv_data = mesh.uv_layers.active.data[:]
for i in range(len(oldMesh.posFaces)):
    face = oldMesh.posFaces[i]
    # set material
    mesh.polygons[i].material_index = oldMesh.faceMaterials[i]
    # set texture
    if oldMesh.materials[oldMesh.faceMaterials[i]].textures:
        tex_name = oldMesh.materials[oldMesh.faceMaterials[i]].textures[0].name.decode()
        mesh.uv_textures[0].data[i].image = texture_dic[tex_name].image
    # set uv
    poly_vert_index = mesh.polygons[i].loop_start
    uv_data[poly_vert_index+0].uv = oldMesh.texCoords[mesh.polygons[i].vertices[0]]
    uv_data[poly_vert_index+1].uv = oldMesh.texCoords[mesh.polygons[i].vertices[1]]
    uv_data[poly_vert_index+2].uv = oldMesh.texCoords[mesh.polygons[i].vertices[2]]
    # Inv UV V
    uv_data[poly_vert_index + 0].uv[1]=1-uv_data[poly_vert_index+0].uv[1]
    uv_data[poly_vert_index + 1].uv[1]=1-uv_data[poly_vert_index+1].uv[1]
    uv_data[poly_vert_index + 2].uv[1]=1-uv_data[poly_vert_index+2].uv[1]
mesh.update()

scene.update()
