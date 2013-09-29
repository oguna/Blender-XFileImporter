class Face:
    def __init__(self):
        self.indices = []

class TexEntry:
    def __init__(self,name = '', isNormalMap=False):
        self.name = name;
        self.isNormalMap = isNormalMap

class Material:
    def __init__(self):
        self.name = '';
        self.isReference = False;
        self.diffuse = ()
        self.specularExponent = 0.0
        self.specular = ()
        self.emissive = ()
        self.textures = []

class BoneWeight:
    def __init__(self):
        self.vertex = 0
        self.weight = 0.0

class Bone:
    def __init__(self):
        self.name = ''
        self.weights = []
        self.offsetMatrix = ()

class Mesh:
    def __init__(self):
        self.positions = []
        self.posFaces = []
        self.normals = []
        self.normalFaces = []
        self.numTextures = 0
        self.texCoords = []
        self.numColorSets = 0
        self.colors = [[],[]]
        self.faceMaterials = []
        self.materials = []
        self.bones = []

class Node:
    def __init__(self,parent=None):
        self.name = ''
        self.trafoMatrix = ()
        self.parent = parent
        self.children = []
        self.meshes = []

class MatrixKey(object):
    def __init__(self):
        self.time = 0.0
        self.matrix = ()

class AnimBone(object):
    def __init__(self):
        self.boneName = ''
        self.posKeys = []
        self.rotKeys = []
        self.scaleKeys = []
        self.trafoKeys = []

class Animation(object):
    def __init__(self):
        self.name = ''
        self.anims = []

class Scene(object):
    def __init__(self):
        self.rootNode = None
        self.globalMeshes = []
        self.globalMaterials = []
        self.anims = []
        self.animTicksPerSecond = 0

AI_MAX_NUMBER_OF_TEXTURECOORDS = 2
AI_MAX_NUMBER_OF_COLOR_SETS = 1