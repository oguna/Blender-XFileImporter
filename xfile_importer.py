from __future__ import annotations
import bpy
import os
from .xfile_parser import (XFileParser, Mesh, Node)
from mathutils import Matrix
from bpy_extras import node_shader_utils
import numpy as np
import math


def convert_mesh(mesh: Mesh, basepath: str) -> bpy.types.Mesh:
    # vertex list
    positions = []
    normals = []
    uvs = []
    materialIndices = []
    triangleCount = 0
    for i in range(len(mesh.posFaces)):
        if len(mesh.posFaces[i].indices) == 3:
            # triangle
            indexLine = [0, 1, 2]
            materialIndices.append(mesh.faceMaterials[i])
            triangleCount += 1
        elif len(mesh.posFaces[i].indices) == 4:
            # Quadrilateral
            indexLine = [0, 1, 2, 0, 2, 3]
            materialIndices.append(mesh.faceMaterials[i])
            materialIndices.append(mesh.faceMaterials[i])
            triangleCount += 2
        else:
            raise ValueError()
        for j in indexLine:
            positions.append(mesh.positions[mesh.posFaces[i].indices[j]])
            normals.append(mesh.normals[mesh.normalFaces[i].indices[j]])
            if mesh.numTextures > 0:
                a = mesh.texCoords[mesh.posFaces[i].indices[j]]
                uvs.append(a)

    indexBufferSource = []
    for i in range(len(materialIndices)):
        indexBufferSource.append((i*3+0, i*3+1, i*3+2))

    # generate blender mesh
    newMesh = bpy.data.meshes.new(mesh.materials[0].name)
    newMesh.from_pydata(positions, [], indexBufferSource)
    
    newMesh.normals_split_custom_set(normals)
    
    if uvs:
        uvl = newMesh.uv_layers.new()
        uv_data = uvl.data
        for i in range(len(uv_data)):
            uv_data[i].uv = uvs[i]
            uv_data[i].uv[1] = -uv_data[i].uv[1]

    # load textures
    image_dic = {}
    for oldMat in mesh.materials:
        if oldMat.textures:
            texEntry = oldMat.textures[0]
            if not texEntry.name:
                continue
            # for MMD
            tex_name = texEntry.name.decode('shift-jis')
            tex_name = tex_name.split('*')[0]

            if tex_name in image_dic:
                continue

            tex_path = os.path.join(basepath, tex_name)
            img = None
            try:
                img = bpy.data.images.load(filepath=tex_path)
            except:
                print(f"texture not found: {tex_path}")
            
            image_dic[tex_name] = img

    # add material
    for oldMat in mesh.materials:
        temp_material = bpy.data.materials.new(oldMat.name)
        temp_material_wrap = node_shader_utils.PrincipledBSDFWrapper(
            temp_material, is_readonly=False)
        temp_material_wrap.use_nodes = True
        # Diffuse (RGBA) -> Base Color & Alpha
        temp_material_wrap.base_color = oldMat.diffuse[:3]
        temp_material_wrap.alpha = oldMat.diffuse[3]
        # Emissive -> Emission Color
        temp_material_wrap.emission_color = oldMat.emissive
        # Specular -> Specular
        spec_color = oldMat.specular
        spec_intensity = spec_color[0] * 0.299 + spec_color[1] * 0.587 + spec_color[2] * 0.114
        temp_material_wrap.specular = spec_intensity
        # Specular Exponent -> Roughness
        if oldMat.specularExponent > 0:
            roughness = math.sqrt(2 / (oldMat.specularExponent + 2))
            temp_material_wrap.roughness = roughness
        else:
            temp_material_wrap.roughness = 1.0

        newMesh.materials.append(temp_material)

        # texture
        if oldMat.textures:
            texEntry = oldMat.textures[0]
            tex_name = texEntry.name.decode('shift-jis') # TODO: to be provided from import setting
            tex_name = tex_name.split('*')[0] # MMD Settings
            
            if tex_name in image_dic and image_dic[tex_name] is not None:
                temp_material_wrap.base_color_texture.image = image_dic[tex_name]
                temp_material_wrap.base_color_texture.texcoords = "UV"

                if img.channels == 4:
                    # TODO: Only set transparency if the image file has an alpha channel.
                    # Get related nodes from the node tree
                    node_tree = temp_material.node_tree
                    principled_bsdf_node = temp_material_wrap.node_principled_bsdf
                    texture_node = temp_material_wrap.base_color_texture.node_image

                    # Link texture alpha to material alpha
                    node_tree.links.new(principled_bsdf_node.inputs['Alpha'], texture_node.outputs['Alpha'])

    # set material
    for i in range(len(materialIndices)):
        newMesh.polygons[i].material_index = materialIndices[i]

    newMesh.update()

    return newMesh


def convert_node(node: Node, basepath: str, transform: Matrix):
    if not node:
        return
    for mesh in node.meshes:
        mesh = convert_mesh(mesh, basepath)
        obj_mesh = bpy.data.objects.new(node.name, mesh)
        obj_mesh.matrix_world = transform
        bpy.context.collection.objects.link(obj_mesh)
    for child in node.children:
        convert_node(child, basepath, transform)


def load(filepath: str, transform: Matrix):

    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')

    if bpy.ops.object.select_all.poll():
        bpy.ops.object.select_all(action='DESELECT')

    basepath = os.path.dirname(filepath)
    filename_wo_ext = os.path.splitext(os.path.basename(filepath))[0]
    with open(filepath, 'br') as f:
        buffer = f.read()
    parser = XFileParser(buffer)
    oldScene = parser.getImportedData()

    for mesh in oldScene.globalMeshes:
        mesh = convert_mesh(mesh, basepath)
        obj_mesh = bpy.data.objects.new(filename_wo_ext, mesh)
        obj_mesh.matrix_world = transform
        bpy.context.collection.objects.link(obj_mesh)
    convert_node(oldScene.rootNode, basepath, transform)

    return
