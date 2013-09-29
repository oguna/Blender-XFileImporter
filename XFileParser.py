import codecs
import struct
import sys
from warnings import *
from XFileHelper import *
import array
import threading
import re

class XFileParser(object): 
    """The XFileParser reads a XFile either in text or binary form and builds a temporary
    data structure out of it.

    Attributes:
        majorVersion: version numbers
        minorVersion: version numbers
        isBinaryFormat: true if the file is in binary, false if it's in text form
        binaryFloatSize: float size, either 32 or 64 bits
        binaryNumCout: counter for number arrays in binary format
        lineNumber: Line number when reading in text format
        scene: Imported data
    """

    def __init__(self, buffer):
        """ Constructor. Creates a data structure out of the XFile given in the memory block. 
	    Args:
            pBuffer: Null-terminated memory buffer containing the XFile
        """
        self.majorVersion = 0
        self.minorVersion = 0
        self.isBinaryFormat = False
        self.binaryFloatSize = 0
        self.binaryNumCout = 0
        self.p = -1
        self.end = -1
        self.buffer = buffer
        self.lineNumber = 0
        self.scene = None
        self.mytimer = None # o-guna-
        self.binaryList = []
        self.binaryIndex = 0

        # set up memory pointers
        self.p = 0
        self.end = buffer.__len__()

        # check header
        if self.buffer[self.p:self.p+4] != b'xof ':
            self.ThrowException('Header mismatch, file is not an XFile.')

        # read version. It comes in a four byte format such as "0302"
        self.majorVersion = int(self.buffer[4:4+2])
        self.minorVersion = int(self.buffer[6:6+2])

        compressed = False

        # txt - pure ASCII text format
        if (self.buffer[8:12] == b'txt '):
            self.isBinaryFormat = False
        elif(self.buffer[8:12] == b'bin '):
            self.isBinaryFormat = True
        elif(self.buffer[8:13] == b'tzip '):
            self.isBinaryFormat = False
            compressed = True
        elif(self.buffer[8:13] == b'bzip '):
            self.isBinaryFormat = True
            compressed = True
        else:
            self.ThrowException('Unsupported xfile format '+self.buffer[8:12])
        # float size
        self.binaryFloatSize = int(self.buffer[12:16])
        print(self.buffer[8:12])

        if self.binaryFloatSize!=32 and self.binaryFloatSize!=64:
            self.ThrowException('Unknown float size %d specified in xfile header.'%self.binaryFloatSize)

        self.p += 16

        # If this is a compressed X file, apply the inflate algorithm to it
        if compressed:
            raise ImportError("Assimp was built without compressed X support")
        else:
            self.ReadUntilEndOfLine()

        self.scene = Scene()
        self.ParseFile()

        # filter the imported hierarchy for some degenerated cases
        if self.scene.rootNode:
            self.FilterHierarchy(self.scene.rootNode)

    def __del__(self):
        """ Destructor. Destroys all imported data along with it """
        
    
    def getImportedData(self):
        return self.scene

    def debug_output(self):
        print('Now Point = %d / %d (%f)'%(self.p,self.end,(float(self.p)/self.end)))
        if self.p != self.end:
            self.mytimer = threading.Timer(1,self.debug_output)
            self.mytimer.start()
        else:
            print('Parse End')
            
    def ParseFile(self):
        # o-guna-: for debug
        #self.mytimer = threading.Timer(1,self.debug_output)
        #self.mytimer.start()

        running = True
        while(running):
            objectName = self.GetNextToken()
            if not objectName:
                break
            if objectName==b'template':
                self.ParseDataObjectTemplate()
            elif objectName==b'Frame':
                self.ParseDataObjectFrame()
            elif objectName==b'Mesh':
                mesh = self.ParseDataObjectMesh();
                self.scene.globalMeshes.append(mesh)
            elif objectName==b'AnimTicksPerSecond':
                self.ParseDataObjectAnimationSet()
            elif objectName==b'Material':
                material = self.ParseDataObjectMaterial()
                self.scene.globalMaterial.append(material)
            elif objectName==b'}':
                print("} found in dataObject")
            else:
                warn("Unknown data object in animation of .x file")
                self.ParseUnknownDataObject()

    def ParseDataObjectTemplate(self):
        name = self.ReadHeadOfDataObject()
        guid = self.GetNextToken()
        running = True
        while(running):
            s = self.GetNextToken()
            if (s == b'}'):
                break
            if not s:
                self.ThrowException("Unexpected end of file reached while parsing template definition")

    def ParseDataObjectFrame(self, parent=None):
        name = self.ReadHeadOfDataObject()
        node = Node(parent)
        node.name = name.decode()
        if parent:
            parent.children.append(node)
        else:
            if self.scene.rootNode:
                if self.scene.rootnode.name != '$dummy_root':
                    exroot = self.scene.rootNode
                    self.scene.rootNode = Node()
                    self.scene.rootNode.children.append(exroot)
                    exroot.parent = self.scene.rootNode
                self.scene.rootNode.children.append(node)
                node.parent = self.scene.rootNode
            else:
                self.scene.rootNode = node
        
        running = True
        while running:
            objectName = self.GetNextToken()
            if not objectName:
                self.ThrowException("Unexpected end of file reached while parsing frame")
            if objectName == b'}':
                break
            elif objectName==b'Frame':
                self.ParseDataObjectFrame(node)
            elif objectName==b'FrameTransformMatrix':
                node.trafoMatrix = self.ParseDataObjectTransformationMatrix()
            elif objectName==b'Mesh':
                mesh = self.ParseDataObjectMesh()
                node.meshes.append(mesh)
            else:
                warn("Unknown data object in frame in x file")
                self.ParseUnknownDataObject()

    def ParseDataObjectTransformationMatrix(self):
        # read header, we're not interested if it has a name
        self.ReadHeadOfDataObject()

        # read its components
        M11 = self.ReadFloat()
        M21 = self.ReadFloat()
        M31 = self.ReadFloat()
        M41 = self.ReadFloat()
        M12 = self.ReadFloat()
        M22 = self.ReadFloat()
        M32 = self.ReadFloat()
        M42 = self.ReadFloat()
        M13 = self.ReadFloat()
        M23 = self.ReadFloat()
        M33 = self.ReadFloat()
        M43 = self.ReadFloat()
        M14 = self.ReadFloat()
        M24 = self.ReadFloat()
        M34 = self.ReadFloat()
        M44 = self.ReadFloat();

        # trailing symbols
        self.CheckForSemicolon()
        self.CheckForClosingBrace()

        return ((M11,M21,M31,M41),(M12,M22,M32,M42),(M13,M23,M33,M43),(M14,M24,M34,M44))

    def ParseDataObjectMesh(self):
        mesh = Mesh()
        name = self.ReadHeadOfDataObject()

        # read veretx count
        numVertices = self.ReadInt()

        # read vertices
        mesh.positions = self.ReadVector3Array(numVertices)

        # read position faces
        numPosFaces = self.ReadInt()

        mesh.posFaces = self.ReadMeshFaceArray(numPosFaces)
        #mesh.posFaces = [0] * numPosFaces
        #for a in range(numPosFaces):
        #    numIndices = self.ReadInt()
        #    if numIndices<3:
        #        self.ThrowException("Invalid index count %1% for face %2%.")
        #    # read indices
        #    face = Face()
        #    for b in range(numIndices):
        #        face.indices.append(self.ReadInt())
        #    mesh.posFaces[a] = face
        #    self.CheckForSeparator()

        # here, other data objects may follow
        running = True
        while running:
            objectName = self.GetNextToken()

            if not objectName:
                self.ThrowException("Unexpected end of file while parsing mesh structure")
            elif objectName==b'}':
                break # mesh finished
            elif objectName==b'MeshNormals':
                self.ParseDataObjectMeshNormals(mesh)
            elif objectName==b'MeshTextureCoords':
                self.ParseDataObjectMeshTextureCoords(mesh)
            elif objectName==b'MeshVertexColors':
                self.ParseDataObjectMeshVertexColors(mesh)
            elif objectName==b'MeshMaterialList':
                self.ParseDataObjectMeshMaterialList(mesh)
            elif objectName==b'VertexDuplicationIndices':
                self.ParseUnknownDataObject(mesh) # we'll ignore vertex duplication indices
            elif objectName == b'XSkinMeshHeader':
                self.ParseDataObjectSkinMeshHeader(mesh)
            elif objectName == b'SkinWeights':
                self.ParseDataObjectSkinWeights(mesh)
            else:
                print("Unknown data object in mesh in x file")
                self.ParseUnknownDataObject()

        return mesh

    def ParseDataObjectSkinWeights(self,mesh):
        self.ReadHeadOfDataObject()

        transformNodeName = self.GetNextTokenAsString()

        mesh.bones.append(Bone())
        bone = mesh.bones[len(mesh.bones)-1]
        bone.name = transformNodeName.decode()

        # read vertex weights
        numWeights = self.ReadInt()
        bone.weights = []

        for a in range(0, numWeights):
            weight = BoneWeight()
            weight.vertex = self.ReadInt()
            bone.weights.append(weight)

        # read vertex weights
        for a in range(0, numWeights):
            bone.weights[a].weight = self.ReadInt()

        # read matrix offset
        a1 = ReadFloat()
        b1 = ReadFloat()
        c1 = ReadFloat()
        d1 = ReadFloat()
        a2 = ReadFloat()
        b2 = ReadFloat()
        c2 = ReadFloat()
        d2 = ReadFloat()
        a3 = ReadFloat()
        b3 = ReadFloat()
        c3 = ReadFloat()
        d3 = ReadFloat()
        a4 = ReadFloat()
        b4 = ReadFloat()
        c4 = ReadFloat()
        d4 = ReadFloat()
        bone.offsetMatrix = ((a1,b1,c1,d1),(a2,b2,c2,d2),(a3,b3,c3,d3),(a4,b4,c4,d4))
             
        self.CheckForSemicolon()
        self.CheckForClosingBrace()

    def ParseDataObjectSkinMeshHeader(self):
        self.ReadHeadOfDataObject()

        self.ReadInt() # maxSkinWeightsPerVertex
        self.ReadInt() # maxSkinWeightsPerFace
        self.ReadInt() # numBonesInMesh

        self.CheckForClosingBrace()

    def ParseDataObjectMeshNormals(self,mesh):
        self.ReadHeadOfDataObject()
        
        # read count
        numNormals = self.ReadInt()

        # read normal vectors  
        mesh.normals = self.ReadVector3Array(numNormals)

        # read normal indices
        numFaces = self.ReadInt()
        if numFaces != len(mesh.posFaces):
            self.ThrowException("Normal face count does not match vertex face count.")
        
        #for a in range(0, numFaces):
        #    numIndices = self.ReadInt()
        #    face = Face()
        #    face.indices = []
        #    for b in range(0,numIndices):
        #        face.indices.append(self.ReadInt())
        #    mesh.normalFaces.append(face)
        #    self.CheckForSeparator()
        mesh.normalFaces = self.ReadMeshFaceArray(numFaces)

        self.CheckForClosingBrace()

    def ParseDataObjectMeshTextureCoords(self,mesh):
        self.ReadHeadOfDataObject()
        if mesh.numTextures +1 > AI_MAX_NUMBER_OF_TEXTURECOORDS:
            self.ThrowException("Too many sets of texture coordinates")

        numCoords = self.ReadInt()
        if numCoords != len(mesh.positions):
            self.ThrowException("Texture coord count does not match vertex count")

        coords = self.ReadVector2Array(numCoords)
        mesh.texCoords = coords
        mesh.numTextures += 1

        self.CheckForClosingBrace()

    def ParseDataObjectMeshVertexColors(self,mesh):
        self.ReadHeadOfDataObject()
        if mesh.numColorSets+1>AI_MAX_NUMBER_OF_COLOR_SETS:
            self.ThrowException( "Too many colorsets")
        colors = mesh.colors[mesh.numColorSets]

        numColors = self.ReadInt()
        if numColors!=len(mesh.positions):
            self.ThrowException( "Vertex color count does not match vertex count")

        colors.clear()
        for i in range(0,numColors):
            colors.append((0,0,0,1))
        for a in range(0,numColors):
            #index = self.ReadInt()
            #if index >= len(mesh.positions):
            #    self.ThrowException( "Vertex color index out of bounds")
            #colors[index] = self.ReadRGBA()
            #if not self.isBinaryFormat:
            #    self.FindNextNoneWhiteSpace()
            #    if self.buffer[self.p]==b';' or self.buffer[self.p]==b',':
            #        self.p+=1
            tmp = re.split(b'[,;][,;]',self.buffer[self.p:],numColors)
            self.p = self.end - len(tmp[len(tmp)-1])
            for b in tmp[0:-1]:
                tmp_ = re.split(b'[,;]', b, 5)
                index = int(tmp_[0])
                if index >= len(mesh.positions):
                    self.ThrowException( "Vertex color index out of bounds")
                colors[index] = (float(tmp_[1]),float(tmp_[2]),float(tmp_[3]),float(tmp_[4]))
        self.CheckForClosingBrace()


    def ParseDataObjectMeshMaterialList(self, mesh):
        self.ReadHeadOfDataObject()
        
        # read material count
        # unsigned int numMaterials =
        self.ReadInt();
        # read non triangulated face material index count
        numMatIndices = self.ReadInt();

        if numMatIndices != len(mesh.posFaces) and numMatIndices != 1:
            self.ThrowException( "Per-Face material index count does not match face count.")

        # read per-face material indices
        #for a in range(0, numMatIndices):
        #    mesh.faceMaterials.append(self.ReadInt())
        mesh.faceMaterials = self.ReadIntArray(numMatIndices)

        # in version 03.02, the face indices end with two semicolons.
        # commented out version check, as version 03.03 exported from blender also has 2 semicolons
        if not self.isBinaryFormat: # && MajorVersion == 3 && MinorVersion <= 2)
            if self.p<self.end and self.buffer[self.p]==';':
                self.p+=1

        # if there was only a single material index, replicate it on all faces
        while len(mesh.faceMaterials) < len(mesh.posFaces):
            mesh.faceMaterials.append(mesh.faceMaterials[0])

        # read following data objects
        running = True
        while running:
            objectName = self.GetNextToken()
            if len(objectName) == 0:
                self.ThrowException( "Unexpected end of file while parsing mesh material list.")
            elif objectName==b'}':
                break # material list finished
            elif objectName == 'b{':
                matName = self.GetNextToken()
                material = Material()
                material.isReference = True
                material.name = matName.decode()
                mesh.materials.append(material)

                self.CheckForClosingBrace()
            elif objectName == b'Material':
                material = self.ParseDataObjectMaterial()
                mesh.materials.append(material)
            elif objectName == b';':
                pass
                #ignore
            else:
                warn("Unknown data object in material list in x file")
                self.ParseUnknownDataObject()


    def ParseDataObjectMaterial(self):
        material = Material()

        matName = self.ReadHeadOfDataObject()
        if not matName:
            matName = b'material'+(str(self.lineNumber)).encode('ascii')
        material.name = matName.decode()
        material.isReference = False;

        # read material values
        material.diffuse = self.ReadRGBA()
        material.specularExponent = self.ReadFloat()
        material.specular = self.ReadRGB()
        material.emissive = self.ReadRGB()
        
        # read other data objects
        running = True
        while running:
            objectName = self.GetNextToken()
            if not objectName:
                self.ThrowException( "Unexpected end of file while parsing mesh material")
            elif objectName==b'}':
                break # material finished
            elif objectName==b'TextureFilename' or objectName==b'TextureFileName':
                # some exporters write "TextureFileName" instead.
                texname = self.ParseDataObjectTextureFilename()
                material.textures.append(TexEntry(texname))
            elif objectName==b'NormalmapFilename' or objectName==b'NormalmapFileName':
                # one exporter writes out the normal map in a separate filename tag
                texname = self.ParseDataObjectTextureFilename()
                material.textures.append(TexEntry(texname,True))
            else:
                warn("Unknown data object in material in x file")
                self.ParseUnknownDataObject()
        
        return material

    def ParseDataObjectAnimTicksPerSecond(self):
        ReadHeadOfDataObject()
        scene.AnimTicksPerSecond = ReadInt()
        CheckForClosingBrace()

    def ParseDataObjectAnimationSet(self):
        animName = ReadHeadOfDataObject()

        anim = Animation()
        scene.anims.append(anim)
        anim.name = animName.decode()

        running = True
        while running:
            objectName = GetNextToken()
            if not objectName:
                self.ThrowException( "Unexpected end of file while parsing animation set.")
            elif objectName==b'}':
                break # animation set finished
            elif objectName==b'Animation':
                ParseDataObjectAnimation(anim)
            else:
                warn('Unknown data object in animation set in x file')
                ParseUnknownDataObject()

    def ParseDataObjectAnimation(self,anim):
        ReadHeadOfDataObject()
        banim = AnimBone()
        anim.anims.append(banim)

        running = True
        while running:
            objectName = GetNextToken()

            if not objectName:
                self.ThrowException( "Unexpected end of file while parsing animation.")
            elif objectName == b'}':
                break
            elif objectName == b'AnimationKey':
                ParseDataObjectAnimationKey(banim)
            elif objectName == b'AnimationOptions':
                ParseUnknownDataObject()
            elif objectName == b'{':
                banim.boneName = GetNextToken()
                CheckForClosingBrace()
            else:
                warn("Unknown data object in animation in x file")
                ParseUnknownDataObject()

    def ParseDataObjectAnimationKey(self, animBone):
        ReadHeadOfDataObject()

        # read key type
        keyType = ReadInt()

        # read number of keys
        numKeys = ReadInt()

        for a in range(0, numKeys):
            # read time
            time = ReadInt()

            # read keys
            if keyType==0:
                # read count
                if ReadInt()!=4:
                    self.ThrowException( "Invalid number of arguments for quaternion key in animation")

                time = float(time)
                w = ReadFloat()
                x = ReadFloat()
                y = ReadFloat()
                z = ReadFloat()
                key = (time,(w,x,y,z))
                animBone.rotKeys.appen(key)

                CheckForSemicolon()

            elif keyType==1 or KeyTime==2:
                # read count
                if ReadInt()!=3:
                    self.ThrowException( "Invalid number of arguments for vector key in animation")
                
                time = float(time)
                value = ReadVector3()
                key = (time,value)

                if keyType==2:
                    animBone.posKeys.append(key)
                else:
                    animBone.scaleKeys.append(key)

            elif KeyTime == 3 or KeyTime==4:
                # read count
                if ReadInt()!=16:
                    self.ThrowException( "Invalid number of arguments for matrix key in animation")
                
                # read matrix
                time = float(time)
                a1 = ReadFloat()
                b1 = ReadFloat()
                c1 = ReadFloat()
                d1 = ReadFloat()
                a2 = ReadFloat()
                b2 = ReadFloat()
                c2 = ReadFloat()
                d2 = ReadFloat()
                a3 = ReadFloat()
                b3 = ReadFloat()
                c3 = ReadFloat()
                d3 = ReadFloat()
                a4 = ReadFloat()
                b4 = ReadFloat()
                c4 = ReadFloat()
                d4 = ReadFloat()
                animBone.trafoKeys.append((time,(a1,b1,c1,d1,a2,b2,c2,d2,a3,b3,c3,d3,a4,b4,c4,d4)))
                CheckForSemicolon()
            else:
                ThrowException('Unknown key type %1 in animation.' % KeyType)
            CheckForSeparator()
        CheckForClosingBrace()

    def ParseDataObjectTextureFilename(self):
        self.ReadHeadOfDataObject()
        name = self.GetNextTokenAsString()
        self.CheckForClosingBrace()
        # FIX: some files (e.g. AnimationTest.x) have "" as texture file name
        if not name:
            warn('Unexpected end of file while parsing unknown segment.')
        # some exporters write double backslash paths out. We simply replace them if we find them
        while name.find(b'\\\\')>0:
            name = name.replace(b'\\\\',b'\\',1)
        return name
        

    def ParseUnknownDataObject(self):
        return

    def FindNextNoneWhiteSpace(self):
        """ places pointer to next begin of a token, and ignores comments """
        if self.isBinaryFormat:
            return

        running = True
        while running:
            while (self.p<self.end)and(self.buffer[self.p:self.p+1]==b' ' or self.buffer[self.p:self.p+1]==b'\r' or self.buffer[self.p:self.p+1]==b'\n'):
                if self.buffer[self.p:self.p+1] == b'\n':
                    self.lineNumber += 1
                self.p += 1
            if self.p>=self.end:
                return
            # check if this is a comment
            if (self.buffer[self.p:self.p+2] == b'//') or self.buffer[self.p:self.p+1]==b'#':
                self.ReadUntilEndOfLine()
                pass
            else:
                break

    def GetNextToken(self):
        """ returns next parseable token. Returns empty string if no token there """
        s = b''

        # process binary-formatted file
        if self.isBinaryFormat:
            # in binary mode it will only return NAME and STRING token
            # and (correctly) skip over other tokens.
            if self.end-self.p < 2:
                return s
            tok = self.ReadBinWord()
            len = 0

            # standalone tokens
            if tok==1:
                # name token
                if self.end-self.p<4:
                    return s
                len = self.ReadBinDWord()
                if self.end-self.p<len:
                    return s
                s = self.buffer[self.p:self.p+len]
                self.p += len
                return s
            elif tok == 2:
                # string token
                if self.end-self.p<4:
                    return s
                len = self.ReadBinDWord()
                if self.end-self.p<len:
                    return s
                s = self.buffer[self.p:self.p+len]
                self.p +=len+2
                return s
            elif tok==3:
                # integer token
                self.p+=4
                return b'<integer>'
            elif tok== 5:
                # GUID token
                self.p += 16
                return b'<guid>'
            elif tok == 6:
                if self.end -self.p<4:
                    return s
                len = self.ReadBinDWord()
                p += len*4
                return b'<int_list>'
            elif tok == 0x0a:
                return b'{'
            elif tok == 0x0b:
                return b'}'
            elif tok == 0x0c:
                return b'('
            elif tok == 0x0d:
                return b')'
            elif tok == 0x0e:
                return b'['
            elif tok == 0x0f:
                return b']'
            elif tok == 0x10:
                return b'<'
            elif tok == 0x11:
                return b'>'
            elif tok == 0x12:
                return b"."
            elif tok ==  0x13:
                return b","
            elif tok ==  0x14:
                return b";"
            elif tok ==  0x1f:
                return b"template"
            elif tok ==  0x28:
                return b"WORD"
            elif tok ==  0x29:
                return b"DWORD"
            elif tok ==  0x2a:
                return b"FLOAT"
            elif tok ==  0x2b:
                return b"DOUBLE"
            elif tok ==  0x2c:
                return b"CHAR"
            elif tok ==  0x2d:
                return b"UCHAR"
            elif tok ==  0x2e:
                return b"SWORD"
            elif tok ==  0x2f:
                return b"SDWORD"
            elif tok ==  0x30:
                return b"void"
            elif tok ==  0x31:
                return b"string"
            elif tok ==  0x32:
                return b"unicode"
            elif tok ==  0x33:
                return b"cstring"
            elif tok ==  0x34:
                return b"array"

        # process text-formatted file
        else:
            self.FindNextNoneWhiteSpace()
            if self.p>=self.end:
                return s

            while (self.p<self.end)and(self.buffer[self.p:self.p+1]!=b' '):
                # either keep token delimiters when already holding a token, or return if first valid char
                tmp = self.buffer[self.p:self.p+1]
                if tmp==b';' or tmp ==b'}' or tmp==b'{' or tmp==b',':
                    if not s:
                        s += tmp
                        self.p+=1
                    break # stop for delimiter
                s+=self.buffer[self.p:self.p+1]
                self.p+=1

        return s

    def ReadHeadOfDataObject(self):
        """reads header of dataobject including the opening brace.
	    areturns false if error happened, and writes name of object
	    if there is one
        """
        nameOrBrace = self.GetNextToken()
        if nameOrBrace != b'{':
            if self.GetNextToken() != b'{':
                self.ThrowException("Opening brace expected.")
            return nameOrBrace
        return b''

    def CheckForClosingBrace(self):
        """ checks for closing curly brace, throws exception if not there """
        if self.GetNextToken() != b'}':
            self.ThrowException("Closing brace expected.")

    def CheckForSemicolon(self):
        """ checks for one following semicolon, throws exception if not there """
        if self.isBinaryFormat:
            return
        token = self.GetNextToken()
        if token != b';':
            self.ThrowException("Semicolon expected.")


    def CheckForSeparator(self):
        """ checks for a separator char, either a ',' or a ';' """
        if self.isBinaryFormat:
            return
        token = self.GetNextToken()
        if token != b',' and token != b';':
            self.ThrowException("Separator character (';' or ',') expected.")

    def TestForSeparator(self):
        """ tests and possibly consumes a separator char, but does nothing if there was no separator """
        if self.isBinaryFormat:
            return
        self.FindNextNoneWhiteSpace()
        if self.p>=self.end:
            return
        # test and skip
        #if self.buffer[self.p:self.p+1] == b';' or self.buffer[self.p:self.p+1] == b',':
        if self.buffer[self.p] == 59 or self.buffer[self.p] == 44:
            self.p+=1

    def GetNextTokenAsString(self):
        poString = b''
        """ reads a x file style string """
        if self.isBinaryFormat:
            return self.GetNextToken()

        self.FindNextNoneWhiteSpace()
        if self.p>=self.end:
            self.ThrowException("Unexpected end of file while parsing string")

        if self.buffer[self.p:self.p+1]!=b'"':
            self.ThrowException("Expected quotation mark.")
        self.p+=1
        while self.p<self.end and self.buffer[self.p:self.p+1] !=b'"':
            poString += self.buffer[self.p:self.p+1]
            self.p+=1

        if self.p>=self.end-1:
            self.ThrowException("Unexpected end of file while parsing string")
        if self.buffer[self.p+1:self.p+2] != b';' or self.buffer[self.p:self.p+1] != b'"':
            self.ThrowException("Expected quotation mark and semicolon at the end of a string.")
        self.p+=2

        return poString

    def ReadUntilEndOfLine(self):
        if self.isBinaryFormat:
            return
        while self.p<self.end:
            tmp = self.buffer[self.p:self.p+1]
            if tmp==b'\n' or tmp==b'\r':
                self.p+=1
                self.lineNumber+=1
                return
            self.p+=1

    def ReadBinWord(self):
        assert (self.end-self.p>=2)
        tmp = struct.unpack('H',self.buffer[self.p:self.p+2])[0]
        self.p+=2
        return tmp

    def ReadBinDWord(self):
        assert (self.end-self.p>=4)
        tmp = struct.unpack('I',self.buffer[self.p:self.p+4])[0]
        self.p+=4
        return tmp

    def ReadInt(self):
        if self.isBinaryFormat:
            if self.binaryNumCout==0 and (self.end-self.p >= 2):
                tmp = self.ReadBinWord()
                if tmp==0x06 and (self.end-self.p>=4):
                    self.binaryNumCout = self.ReadBinDWord()
                else:
                    self.binaryNumCout = 1
                self.binaryList = array.array('L')
                self.binaryIndex = -1
                self.binaryList.fromstring(self.buffer[self.p:self.p+4*self.binaryNumCout])
                self.p += self.binaryNumCout*4
            self.binaryNumCout -= 1
            self.binaryIndex += 1
            return self.binaryList[self.binaryIndex]
            #if self.end-self.p>=4:
            #    return self.ReadBinDWord()
            #else:
            #    self.p = self.end
            #    return 0
        else:
            self.FindNextNoneWhiteSpace()

            # check preceeding minus sign
            isNegative = False
            if self.buffer[self.p:self.p+1]==b'-':
                isNegative = False
                self.p+=1
            # at least one digit expected
            if not self.buffer[self.p:self.p+1].isdigit():
                self.ThrowException( 'Number expected.')
                
            # read digits
            number = 0
            while self.p<self.end:
                if not self.buffer[self.p:self.p+1].isdigit():
                    break
                number = number * 10 + int(self.buffer[self.p:self.p+1])
                self.p+=1

            self.CheckForSeparator()
            if isNegative:
                return -number
            else:
                return number

    def ReadFloat(self):
        if self.isBinaryFormat:
            if (self.binaryNumCout == 0) & (self.end -self.p >= 2):
                tmp = self.ReadBinWord()
                if(tmp == 0x07 ) &(self.end -self.p>=4):
                    self.binaryNumCout = self.ReadBinDWord()
                else:
                    self.binaryNumCout = 1
                self.binaryList = array.array('f')
                self.binaryIndex = -1
                self.binaryList.fromstring(self.buffer[self.p:self.p+self.binaryNumCout*4])
                self.p = self.p+self.binaryNumCout*4
            self.binaryIndex += 1
            self.binaryNumCout-=1
            #if self.binaryFloatSize == 8:
            #    if self.end-self.p>=8 :
            #        result = struct.unpack('f', self.buffer[self.p:self.p+8])[0]
            #    else:
            #        self.p = self.end
            #        return 0
            #else:
            #    if self.end -self.p >= 4:
            #        result = struct.unpack('f', self.buffer[self.p:self.p+4])[0]
            #        self.p += 4
            #        return result
            #    else:
            #        self.p = self.end
            #        return 0
            return self.binaryList[self.binaryIndex]

        # text version
        self.FindNextNoneWhiteSpace()
        # check for various special strings to allow reading files from faulty exporters
        # I mean you, Blender!
        # Reading is safe because of the terminating zero

        if self.buffer[self.p:self.p+9] == b'-1.#IND00' or self.buffer[self.p:self.p+8] == b'1.#IND00':
            self.p+=9
            self.CheckForSeparator()
            return 0.0
        elif self.buffer[self.p:self.p+8] == b'1.#QNAN0':
            self.p+=8
            self.CheckForSeparator()
            return 0.0
        result_ = 0.0
        #tmp_ = ''
        digitStart = self.p
        digitEnd = self.p
        notSplitChar = [b'0',b'1',b'2',b'3',b'4',b'5',b'6',b'7',b'8',b'9',b'+',b'.',b'-',b'e',b'E']
        while self.p<self.end:
            c =self.buffer[self.p:self.p+1]
            #if c.isdigit() or c=='+' or c=='.' or c=='-' or c=='e' or c=='E':
            if c in notSplitChar:
                #tmp_ += c
                digitEnd = self.p
                self.p+=1
            else:
                break
        tmp = self.buffer[digitStart:digitEnd]
        result_ = float(tmp)
        self.CheckForSeparator()
        return result_

    def ReadVector2(self):
        x = self.ReadFloat()
        y = self.ReadFloat()
        self.TestForSeparator()
        return (x,y)

    def ReadVector3(self):
        x = self.ReadFloat()
        y = self.ReadFloat()
        z = self.ReadFloat()
        self.TestForSeparator()
        return (x,y,z)

    def ReadRGB(self):
        r = self.ReadFloat()
        g = self.ReadFloat()
        b = self.ReadFloat()
        self.TestForSeparator()
        return (r,g,b)

    def ReadRGBA(self):
        r = self.ReadFloat()
        g = self.ReadFloat()
        b = self.ReadFloat()
        a = self.ReadFloat()
        self.TestForSeparator()
        return (r,g,b,a)


    def ThrowException(self,text):
        """Throws an exception with a line number and the given text."""
        if(self.isBinaryFormat):
            raise ImportError( text)
        else:
            raise ImportError('Line %d: %s' % (self.lineNumber, text))
        pass

    def FilterHierarchy(self,node):
        """Filters the imported hierarchy for some degenerated cases that some
        exporters produce."""

        # if the node has just a single unnamed child containing a mesh, remove
        # the anonymous node inbetween. The 3DSMax kwXport plugin seems to produce this
        # mess in some cases
        if(len(node.children)==1 and not node):
            child = node.children[0]
            if (not child.name and child.meshes.cout > 0):
                # transfer its meshes to us
                for a in range(0, child.meshes.cout):
                    node.meshes.append(child.meshes[a])
                child.meshes = []

                # transfer the transform as well
                node.trafoMatrix = node.trafoMatrix * child.trafoMatrix

                # then kill it
                del(child)
                node.children = []

        # recurse
        for a in range(0,len(node.children)):
            self.FilterHierarchy(node.children[a])

    def ReadVector3Array(self,num):
        result = []
        if self.isBinaryFormat:
            tmp = self.ReadBinWord()
            if tmp==0x07 and (self.end-self.p>=4):
                self.binaryNumCout = self.ReadBinDWord()
            else:
                self.binaryNumCout = 1
            self.binaryList = array.array('f')
            self.binaryList.fromstring(self.buffer[self.p:self.p+4*self.binaryNumCout])
            self.p += self.binaryNumCout*4
            for i in range(0,num):

                result.append(tuple(self.binaryList[i*3:i*3+3]))
            self.binaryList = []
            self.binaryNumCout = 0
            return result
        # for text
        #for i in range(num):
        #    result = self.ReadVector3()
        #return result
        tmp = re.split(b'[,;][,;]',self.buffer[self.p:],num)
        self.p = self.end - len(tmp[len(tmp)-1])
        for a in range(num):
            tmp_ = re.split(b'[,;]',tmp[a])
            result.append((float(tmp_[0]),float(tmp_[1]),float(tmp_[2])))
        return result

    def ReadVector2Array(self,num):
        result = []
        print("ReadVector2Array")
        if self.isBinaryFormat:
            tmp = self.ReadBinWord()
            if tmp==0x07 and (self.end-self.p>=4):
                self.binaryNumCout = self.ReadBinDWord()
            else:
                self.binaryNumCout = 1
            self.binaryList = array.array('f')
            self.binaryList.fromstring(self.buffer[self.p:self.p+4*self.binaryNumCout])
            self.p += self.binaryNumCout*4
            for i in range(num):
                result.append(tuple(self.binaryList[i*2:i*2+2]))
            self.binaryList = []
            self.binaryNumCout = 0
            print("ReadVector2Array")
            return result
        # for text
        tmp = re.split(b'[,;][,;]',self.buffer[self.p:],num)
        self.p = self.end - len(tmp[len(tmp)-1])
        for a in range(num):
            tmp_ = re.split(b'[,;]',tmp[a])
            result.append((float(tmp_[0]),float(tmp_[1])))
        return result
        
    def ReadIntArray(self,num):
        if self.isBinaryFormat:
            result=[]
            for i in range(num):
                result.append(self.ReadInt())
            return result
            ## list nagakatara tukuru
            #if not self.binaryList:
            #    tmp = self.ReadBinWord()
            #    if tmp==0x06 and (self.end-self.p>=4):
            #        self.binaryNumCout = self.ReadBinDWord()
            #    else:
            #        self.binaryNumCout = 1
            #    self.binaryList = array.array('L')
            #    self.binaryIndex = -1
            #    self.binaryList.fromstring(self.buffer[self.p:self.p+4*self.binaryNumCout])
            #    self.p += self.binaryNumCout*4
            ## list no nagasa ga tarinai...
            #if len(self.binaryList)-self.binaryIndex < num:
            #    raise Exception()
            #start = self.binaryIndex
            #self.binaryIndex += num
            #return self.binaryList[start:self.binaryIndex]
        # text version
        tmp = re.split(b'[,;]',self.buffer[self.p:],num)
        self.p = self.end - len(tmp[len(tmp)-1])
        for a in range(num):
            tmp[a] = int(tmp[a])
        return tmp[:-1]

    def ReadMeshFaceArray(self,numPosFaces):
        # read position faces
        posFaces = []
        if self.isBinaryFormat:
            for a in range(numPosFaces):
                self.binaryIndex += 1
                self.binaryNumCout -= 1
                numIndices = self.binaryList[self.binaryIndex]
                if numIndices < 3:
                    self.ThrowException("Invalid index count %d for face %d." % (numIndices, a))
                # read indices
                face = Face()
                face.indices = self.binaryList[self.binaryIndex:self.binaryIndex+numIndices]
                self.binaryIndex += numIndices
                self.binaryNumCout -= (numPosFaces)
                posFaces.append(face)
                self.CheckForSeparator()
            return posFaces
        # text version
        tmp = re.split(b'[,;][,;]',self.buffer[self.p:],numPosFaces)
        self.p = self.end - len(tmp[len(tmp)-1])
        for a in range(numPosFaces):
            tmp_ = re.split(b'[,;]',tmp[a])
            for b in range(len(tmp_)):
                tmp_[b] = int(tmp_[b])
            ind = tuple(tmp_[1:])
            if (len(ind)!=tmp_[0]):
                self.ThrowException("MeshFaceArray Error")
            f = Face()
            f.indices = ind
            posFaces.append(f)
        return posFaces

