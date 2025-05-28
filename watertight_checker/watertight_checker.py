import bpy
import bmesh
from bpy.types import Operator, Panel
from bpy.props import BoolProperty, StringProperty

class MESH_OT_check_watertight(Operator):
    bl_idname = "mesh.check_watertight"
    bl_label = "Check Watertight Geometry"
    bl_description = "Проверяет замкнутость меша и наличие проблемных граней"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        results = []
        has_errors = False
        scene = context.scene
        
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            mesh = obj.data
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

            # Проверка 1: Открытые границы
            boundary_edges = [e for e in bm.edges if e.is_boundary]
            
            # Проверка 2: Неплотные соединения
            loose_verts = [v for v in bm.verts if len(v.link_edges) < 2 and not v.hide]
            
            # Проверка 3: Не manifold геометрия
            non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
            non_manifold_verts = [v for v in bm.verts if not v.is_manifold]

            # Формирование отчета
            errors = []
            if boundary_edges:
                errors.append(f"Открытые границы: {len(boundary_edges)} ребер")
            if loose_verts:
                errors.append(f"Неплотные соединения: {len(loose_verts)} вершин")
            if non_manifold_edges or non_manifold_verts:
                errors.append(f"Non-manifold: {len(non_manifold_edges)} ребер, {len(non_manifold_verts)} вершин")

            status = "✅ Замкнут" if not errors else "❌ НЕ замкнут"
            results.append(f"{obj.name}: {status}")
            
            if errors:
                has_errors = True
                results.extend(["    • " + e for e in errors])

                if scene.watertight_select_problems:
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='DESELECT')
                    
                    # Выделяем проблемные элементы
                    bm.select_flush(False)
                    for e in boundary_edges + non_manifold_edges:
                        e.select = True
                    for v in loose_verts + non_manifold_verts:
                        v.select = True

            bm.free()

        # Формирование финального отчета
        report_msg = "\n".join(results)
        if not results:
            self.report({'INFO'}, "Нет мешей для проверки")
            return {'CANCELLED'}
        
        scene.watertight_report = report_msg
        self.report({'INFO'}, "Проверка завершена. Смотрите отчет в панели инструментов.")
        return {'FINISHED'}

class VIEW3D_PT_watertight_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Инструменты'
    bl_label = "Watertight Checker"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        col = layout.column()
        col.operator(MESH_OT_check_watertight.bl_idname)
        col.prop(scene, "watertight_select_problems", text="Выделить проблемы")
        
        if hasattr(scene, "watertight_report") and scene.watertight_report:
            box = layout.box()
            for line in scene.watertight_report.split('\n'):
                row = box.row()
                row.label(text=line)

classes = (
    MESH_OT_check_watertight,
    VIEW3D_PT_watertight_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.watertight_report = StringProperty(
        name="Watertight Report",
        default=""
    )
    bpy.types.Scene.watertight_select_problems = BoolProperty(
        name="Select Problems",
        default=True
    )

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.watertight_report
    del bpy.types.Scene.watertight_select_problems