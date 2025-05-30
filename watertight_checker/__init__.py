from . import watertight_checker

bl_info = {
    "name": "Watertight Mesh Checker",
    "author": "Roman Ilyin",
    "version": (2025, 5, 30, 5),
    "blender": (4, 4, 0),
    "location": "View3D > Tools",
    "description": "Проверяет замкнутость геометрии для корректной работы Cull Front и shadow maps",
    "warning": "",
    "doc_url": "https://t.me/gamedev_stinger",
    "category": "Mesh",
}

def register():
    watertight_checker.register()

def unregister():
    watertight_checker.unregister()