# __init__.py
from . import watertight_checker

def register():
    watertight_checker.register()

def unregister():
    watertight_checker.unregister()