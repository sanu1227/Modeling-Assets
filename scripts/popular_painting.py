"""Small deterministic painting utility for original Blender character surfaces.

Creates packed sRGB PNG artwork and planar UVs on the forward-facing surface.
This module performs no I/O until paint_front() is called.
"""
import math
from pathlib import Path
import struct
import zlib
import bpy
import numpy as np


def ellipse(x,z,rx,rz,count=48):
    return [(x+rx*math.cos(2*math.pi*i/count),z+rz*math.sin(2*math.pi*i/count)) for i in range(count)]


def paint_front(obj,name,path,base_color,regions,bounds,resolution=2048,roughness=.55,normal_sign=-1):
    """regions = [(hex_color, XZ polygon), ...], in painter's order."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    xmin,xmax,zmin,zmax=bounds
    # PNG rows run downward, whereas UV V runs upward.
    u=(np.arange(resolution)+.5)/resolution
    v=1-(np.arange(resolution)+.5)/resolution
    x=xmin+u[None,:]*(xmax-xmin);z=zmin+v[:,None]*(zmax-zmin)
    def rgb(color):return np.array([int(color[i:i+2],16) for i in (0,2,4)],dtype=np.uint8)
    pixels=np.empty((resolution,resolution,3),dtype=np.uint8);pixels[:]=rgb(base_color)
    for color,polygon in regions:
        inside=np.zeros((resolution,resolution),dtype=bool)
        for i in range(len(polygon)):
            ax,az=polygon[i];bx,bz=polygon[(i+1)%len(polygon)]
            if abs(bz-az)<1e-12:continue
            crossing=((az>z)!=(bz>z))&(x<(bx-ax)*(z-az)/(bz-az)+ax)
            inside^=crossing
        pixels[inside]=rgb(color)
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',resolution,resolution,8,2,0,0,0))
    png+=chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row.tobytes() for row in pixels)))+chunk(b'IEND',b'')
    path.write_bytes(png)
    image=bpy.data.images.load(str(path),check_existing=False);image.name=name+' image';image.pack()
    material=bpy.data.materials.new(name);material.use_nodes=True
    shader=material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value=roughness;shader.inputs['Specular IOR Level'].default_value=.23
    node=material.node_tree.nodes.new('ShaderNodeTexImage');node.image=image;node.interpolation='Linear'
    material.node_tree.links.new(node.outputs['Color'],shader.inputs['Base Color'])
    obj.data.materials.append(material);paint_index=len(obj.data.materials)-1
    uv=obj.data.uv_layers.new(name='Painted front UV')
    matrix=obj.matrix_world
    points=[matrix@vertex.co for vertex in obj.data.vertices]
    normal_matrix=matrix.to_3x3().inverted().transposed()
    for polygon in obj.data.polygons:
        normal=normal_matrix@polygon.normal
        if normal.y*normal_sign>.015:polygon.material_index=paint_index
        for index in polygon.loop_indices:
            p=points[obj.data.loops[index].vertex_index]
            uv.data[index].uv=((p.x-xmin)/(xmax-xmin),(p.z-zmin)/(zmax-zmin))
    obj.data.uv_layers.active=uv
    return material
