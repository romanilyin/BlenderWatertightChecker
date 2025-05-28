import bpy
import bmesh
from bpy.types import Operator, Panel
from bpy.props import BoolProperty, StringProperty
from mathutils import Vector
import datetime

# Версия плагина в формате "год.месяцдень.minor"
PLUGIN_VERSION = "2025.528.8"  # 28 мая 2025, 8-я ревизия

class MESH_OT_check_watertight(Operator):
    bl_idname = "mesh.check_watertight"
    bl_label = "Check Watertight Geometry"
    bl_description = "Проверяет замкнутость меша и наличие проблемных граней"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        results = []
        has_errors = False
        error_types = set()
        scene = context.scene
        
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            mesh = obj.data
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            bm.verts.ensure_lookup_table()

            # Проверка 1: Открытые границы (ребра с <2 граней)
            boundary_edges = [e for e in bm.edges if e.is_boundary]
            if boundary_edges:
                error_types.add("BOUNDARY")
            
            # Проверка 2: Неплотные соединения (вершины с <2 ребер)
            loose_verts = [v for v in bm.verts if len(v.link_edges) < 2 and not v.hide]
            if loose_verts:
                error_types.add("LOOSE")
            
            # Проверка 3: Перевернутые нормали
            inverted_normals = []
            for face in bm.faces:
                # Вычисляем центр грани
                face_center = Vector()
                for vert in face.verts:
                    face_center += vert.co
                face_center /= len(face.verts)
                
                # Проверяем направление нормали
                if face.normal.dot(face_center - obj.location) < 0:
                    inverted_normals.append(face)
                    
            if inverted_normals:
                error_types.add("NORMALS")
            
            # Проверка 4: Не manifold геометрия
            non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
            non_manifold_verts = [v for v in bm.verts if not v.is_manifold]
            if non_manifold_edges or non_manifold_verts:
                error_types.add("MANIFOLD")

            # Формирование отчета с пояснениями и рекомендациями
            errors = []
            if boundary_edges:
                errors.append(f"❌ Открытые границы (Open boundaries): {len(boundary_edges)} ребер (<2 граней)")
                errors.append("   - Заполнить отверстия (Fill)")
                errors.append("   - Соединить края (Bridge Edge Loops)")
                
            if loose_verts:
                errors.append(f"❌ Неплотные соединения (Loose geometry): {len(loose_verts)} вершин (<2 ребер)")
                errors.append("   - Объединить по расстоянию (Merge by Distance)")
                errors.append("   - Удалить лишние вершины (Delete Vertices)")
                
            if inverted_normals:
                errors.append(f"❌ Перевернутые нормали (Inverted normals): {len(inverted_normals)} полигонов")
                errors.append("   - Перевернуть нормали (Flip Normals)")
                errors.append("   - Выровнять наружу (Recalculate Outside)")
                
            if non_manifold_edges or non_manifold_verts:
                errors.append(f"❌ Non-manifold: {len(non_manifold_edges)} ребер, {len(non_manifold_verts)} вершин")
                errors.append("   - Удалить внутренние поверхности (Delete Loose)")
                errors.append("   - Применить Boolean (Boolean Operation)")

            status = "✅ Замкнут (Watertight)" if not errors else "❌ НЕ замкнут (Not watertight)"
            results.append(f"{obj.name}: {status}")
            
            if errors:
                has_errors = True
                results.extend(errors)

                if scene.watertight_select_problems:
                    # Подготовка к выделению
                    bpy.context.view_layer.objects.active = obj
                    
                    # Сохраняем текущий режим
                    current_mode = obj.mode
                    
                    # Переходим в режим объектного уровня
                    if current_mode != 'OBJECT':
                        bpy.ops.object.mode_set(mode='OBJECT')
                    
                    # Переходим в режим редактирования
                    bpy.ops.object.mode_set(mode='EDIT')
                    
                    # Получаем bmesh из режима редактирования
                    bm_edit = bmesh.from_edit_mesh(mesh)
                    bm_edit.edges.ensure_lookup_table()
                    bm_edit.faces.ensure_lookup_table()
                    bm_edit.verts.ensure_lookup_table()
                    
                    # Сбрасываем выделение
                    bpy.ops.mesh.select_all(action='DESELECT')
                    
                    # Активируем все типы выделения
                    tool_settings = context.scene.tool_settings
                    tool_settings.mesh_select_mode = (True, True, True)
                    
                    # Выделяем проблемные элементы
                    for e in boundary_edges:
                        if e.index < len(bm_edit.edges):
                            bm_edit.edges[e.index].select = True
                    
                    for v in loose_verts:
                        if v.index < len(bm_edit.verts):
                            bm_edit.verts[v.index].select = True
                    
                    for f in inverted_normals:
                        if f.index < len(bm_edit.faces):
                            bm_edit.faces[f.index].select = True
                    
                    for e in non_manifold_edges:
                        if e.index < len(bm_edit.edges):
                            bm_edit.edges[e.index].select = True
                    
                    for v in non_manifold_verts:
                        if v.index < len(bm_edit.verts):
                            bm_edit.verts[v.index].select = True
                    
                    # Обновляем меш
                    bmesh.update_edit_mesh(mesh)
                    
                    # Возвращаем в исходный режим
                    if current_mode != 'EDIT':
                        bpy.ops.object.mode_set(mode=current_mode)

            bm.free()

        # Формирование финального отчета
        report_msg = "\n".join(results)
        if not results:
            self.report({'INFO'}, "Нет мешей для проверки")
            return {'CANCELLED'}
        
        # Сохраняем типы ошибок
        scene.watertight_error_types = error_types
        scene.watertight_report = report_msg
        
        if has_errors:
            self.report({'WARNING'}, "Обнаружены проблемы в геометрии")
        else:
            self.report({'INFO'}, "Все меши замкнуты")
            
        return {'FINISHED'}

class VIEW3D_PT_watertight_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Инструменты'
    bl_label = f"Watertight Checker v{PLUGIN_VERSION}"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Заголовок с версией
        row = layout.row()
        row.label(text=f"Watertight Checker v{PLUGIN_VERSION}", icon='MESH_CUBE')
        
        col = layout.column()
        col.operator(MESH_OT_check_watertight.bl_idname)
        col.prop(scene, "watertight_select_problems", text="Выделить проблемы (Select problems)")
        
        # Предупреждение о проверке нормалей
        warning_box = layout.box()
        warning_box.label(text="Проверка нормалей корректна только для выпуклых объектов")
        warning_box.label(text="Для вогнутых форм используйте стандартные инструменты анализа нормалей")
        
        if hasattr(scene, "watertight_report") and scene.watertight_report:
            box = layout.box()
            
            # Отчет о проблемах
            for line in scene.watertight_report.split('\n'):
                # Для заголовков объектов используем другой стиль
                if "✅" in line or "❌" in line:
                    row = box.row()
                    row.alert = "❌" in line
                    row.label(text=line, icon='OBJECT_DATA' if "✅" in line or "❌" in line else 'DOT')
                else:
                    row = box.row()
                    row.alert = "❌" in line
                    row.label(text=line)
            
            # Дополнительные решения
            if hasattr(scene, "watertight_error_types") and scene.watertight_error_types:
                solutions_box = box.box()
                solutions_box.label(text="Дополнительные решения:")
                
                col_solution = solutions_box.column(align=True)
                
                if "BOUNDARY" in scene.watertight_error_types:
                    row = col_solution.row()
                    row.operator("mesh.fill", text="Заполнить отверстия (Fill)")
                    row.operator("mesh.bridge_edge_loops", text="Соединить края (Bridge)")
                
                if "LOOSE" in scene.watertight_error_types:
                    row = col_solution.row()
                    row.operator("mesh.remove_doubles", text="Объединить по расстоянию (Merge by Distance)")
                    row.operator("mesh.delete", text="Удалить лишнее (Delete)").type = 'VERT'
                
                if "NORMALS" in scene.watertight_error_types:
                    row = col_solution.row()
                    row.operator("mesh.flip_normals", text="Перевернуть нормали (Flip Normals)")
                    row.operator("mesh.normals_make_consistent", text="Выровнять наружу (Recalculate Outside)").inside = False
                
                if "MANIFOLD" in scene.watertight_error_types:
                    row = col_solution.row()
                    row.operator("mesh.delete_loose", text="Удалить лишнее (Delete Loose)")
                    row.operator("mesh.intersect_boolean", text="Применить Boolean").operation = 'DIFFERENCE'

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
    bpy.types.Scene.watertight_error_types = bpy.props.EnumProperty(
        name="Error Types",
        options={'ENUM_FLAG'},
        items=[
            ('BOUNDARY', "Boundary", "Open boundaries"),
            ('LOOSE', "Loose", "Loose geometry"),
            ('NORMALS', "Normals", "Inverted normals"),
            ('MANIFOLD', "Manifold", "Non-manifold geometry"),
        ],
        default=set()
    )
    bpy.types.Scene.watertight_select_problems = BoolProperty(
        name="Select Problems",
        default=True,
        description="Автоматически выделять проблемные элементы в режиме редактирования"
    )

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.watertight_report
    del bpy.types.Scene.watertight_error_types
    del bpy.types.Scene.watertight_select_problems