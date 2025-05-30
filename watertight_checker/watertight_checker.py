import bpy
import bmesh
import traceback
import os
from bpy.types import Operator, Panel
from bpy.props import BoolProperty, StringProperty, IntVectorProperty, IntProperty, EnumProperty
from mathutils import Vector
from bpy_extras import view3d_utils
from bpy.app.translations import pgettext as _, pgettext_data as data_

# Версия плагина в формате "год.месяцдень.minor"
PLUGIN_VERSION = "2025.530.4"  # 30 мая 2025, 4-я ревизия

# Уникальные префиксы для свойств
PREFIX = "wtc_"

# Функция для логгирования
def log_message(message):
    print(f"[Watertight Checker] {message}")

# Функции для локализации
def TIP_(message):
    return pgettext_tip(message)

def DATA_(message):
    return pgettext_data(message)

# Создаем контекстные переводы
def register_translations():
    ru_translations = {
        # Операторы
        ("Operator", "Check Watertight Geometry"): "Проверить замкнутость геометрии (Watertight Geometry)",
        ("Operator", "Recheck Watertight Geometry"): "Перепроверить замкнутость геометрии (Recheck Watertight)",
        ("Operator", "Select Specific Problems"): "Выделить конкретные проблемы",
        ("Operator", "Focus on Problem Element"): "Сфокусироваться на проблемном элементе",
        
        # Панель
        ("*", "Watertight Checker"): "Проверка замкнутости",
        ("*", "Check"): "Проверить",
        ("*", "Recheck"): "Перепроверить",
        ("*", "Select problems:"): "Выделить проблемы:",
        ("*", "Open boundaries"): "Открытые границы (Open boundaries)",
        ("*", "Loose geometry"): "Неплотные соединения (Loose geometry)",
        ("*", "Inverted normals"): "Перевернутые нормали (Inverted normals)",
        ("*", "Non-manifold"): "Non-manifold геометрия",
        ("*", "Focus on elements:"): "Фокус на элементах:",
        ("*", "Position:"): "Позиция:",
        ("*", "Previous"): "Предыдущий",
        ("*", "Next"): "Следующий",
        ("*", "Additional solutions:"): "Дополнительные решения:",
        ("*", "Fill holes (Fill)"): "Заполнить отверстия (Fill)",
        ("*", "Connect edges (Bridge)"): "Соединить края (Bridge)",
        ("*", "Merge by Distance"): "Объединить по расстоянию (Merge by Distance)",
        ("*", "Delete extra"): "Удалить лишнее (Delete)",
        ("*", "Flip Normals"): "Перевернуть нормали (Flip Normals)",
        ("*", "Recalculate Outside"): "Выровнять наружу (Recalculate Outside)",
        ("*", "Delete Loose"): "Удалить лишнее (Delete Loose)",
        ("*", "Apply Boolean"): "Применить Boolean",
        
        # Сообщения
        ("*", "No selected objects to check"): "Нет выделенных объектов для проверки",
        ("*", "Geometry problems detected"): "Обнаружены проблемы в геометрии",
        ("*", "All meshes are watertight"): "Все меши замкнуты",
        ("*", "Select a mesh object"): "Выделите mesh-объект",
        ("*", "First select a problem"): "Сначала выделите проблему",
        ("*", "No problem elements found"): "Проблемные элементы не найдены",
        ("*", "Focus on element {index}/{total}"): "Фокус на элементе {index}/{total}",
        ("*", "Element not found"): "Элемент не найден",
        ("*", "Normal check is only reliable for convex objects"): 
            "Проверка нормалей корректна только для выпуклых объектов",
        ("*", "For concave shapes use standard normal analysis tools"): 
            "Для вогнутых форм используйте стандартные инструменты анализа нормалей",
        
        # Отчеты
        ("Report", "Open boundaries: {count} edges (<2 faces)"): 
            "Открытые границы (Open boundaries): {count} ребер (<2 граней)",
        ("Report", "Loose geometry: {count} vertices (<2 edges)"): 
            "Неплотные соединения (Loose geometry): {count} вершин (<2 ребер)",
        ("Report", "Inverted normals: {count} polygons"): 
            "Перевернутые нормали (Inverted normals): {count} полигонов",
        ("Report", "Non-manifold: {edges} edges, {verts} vertices"): 
            "Non-manifold: {edges} ребер, {verts} вершин",
        ("Report", "Watertight"): "✅ Замкнут (Watertight)",
        ("Report", "Not watertight"): "❌ НЕ замкнут (Not watertight)",
        ("Report", "Fill holes"): "   - Заполнить отверстия (Fill)",
        ("Report", "Connect edges"): "   - Соединить края (Bridge Edge Loops)",
        ("Report", "Merge by distance"): "   - Объединить по расстоянию (Merge by Distance)",
        ("Report", "Delete extra vertices"): "   - Удалить лишние вершины (Delete Vertices)",
        ("Report", "Flip normals"): "   - Перевернуть нормали (Flip Normals)",
        ("Report", "Recalculate outward"): "   - Выровнять наружу (Recalculate Outside)",
        ("Report", "Delete internal surfaces"): "   - Удалить внутренние поверхности (Delete Loose)",
        ("Report", "Apply boolean operation"): "   - Применить Boolean (Boolean Operation)",
    }
    
    en_translations = {
        # Английские версии (в основном идентичны оригиналу)
        ("Operator", "Check Watertight Geometry"): "Check Watertight Geometry",
        ("Operator", "Recheck Watertight Geometry"): "Recheck Watertight Geometry",
        ("Operator", "Select Specific Problems"): "Select Specific Problems",
        ("Operator", "Focus on Problem Element"): "Focus on Problem Element",
        
        # Панель
        ("*", "Watertight Checker"): "Watertight Checker",
        ("*", "Check"): "Check",
        ("*", "Recheck"): "Recheck",
        ("*", "Select problems:"): "Select problems:",
        ("*", "Open boundaries"): "Open boundaries",
        ("*", "Loose geometry"): "Loose geometry",
        ("*", "Inverted normals"): "Inverted normals",
        ("*", "Non-manifold"): "Non-manifold",
        ("*", "Focus on elements:"): "Focus on elements:",
        ("*", "Position:"): "Position:",
        ("*", "Previous"): "Previous",
        ("*", "Next"): "Next",
        ("*", "Additional solutions:"): "Additional solutions:",
        ("*", "Fill holes (Fill)"): "Fill holes (Fill)",
        ("*", "Connect edges (Bridge)"): "Connect edges (Bridge)",
        ("*", "Merge by Distance"): "Merge by Distance",
        ("*", "Delete extra"): "Delete extra",
        ("*", "Flip Normals"): "Flip Normals",
        ("*", "Recalculate Outside"): "Recalculate Outside",
        ("*", "Delete Loose"): "Delete Loose",
        ("*", "Apply Boolean"): "Apply Boolean",
        
        # Сообщения
        ("*", "No selected objects to check"): "No selected objects to check",
        ("*", "Geometry problems detected"): "Geometry problems detected",
        ("*", "All meshes are watertight"): "All meshes are watertight",
        ("*", "Select a mesh object"): "Select a mesh object",
        ("*", "First select a problem"): "First select a problem",
        ("*", "No problem elements found"): "No problem elements found",
        ("*", "Focus on element {index}/{total}"): "Focus on element {index}/{total}",
        ("*", "Element not found"): "Element not found",
        ("*", "Normal check is only reliable for convex objects"): 
            "Normal check is only reliable for convex objects",
        ("*", "For concave shapes use standard normal analysis tools"): 
            "For concave shapes use standard normal analysis tools",
    }
    
    translations_dict = {
        "ru_RU": ru_translations,
        "en_US": en_translations,
    }
    
    bpy.app.translations.register(__name__, translations_dict)

def unregister_translations():
    bpy.app.translations.unregister(__name__)

class MESH_OT_check_watertight(Operator):
    bl_idname = "mesh.check_watertight"
    bl_label = _("Check Watertight Geometry")
    bl_description = _("Проверяет замкнутость меша и наличие проблемных граней")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        # Очищаем предыдущий отчет
        scene[PREFIX + "report"] = ""
        scene[PREFIX + "error_types"] = ""  # Храним как строку вместо множества
        
        results = []
        has_errors = False
        error_types = set()
        
        # Проверяем есть ли выделенные объекты
        if not context.selected_objects:
            self.report({'INFO'}, _("No selected objects to check"))
            return {'CANCELLED'}
        
        # Сброс кэшированных данных на всех объектах перед началом новой проверки
        for obj in context.selected_objects:
            if hasattr(obj, PREFIX + "boundary_edges"):
                obj[PREFIX + "boundary_edges"] = []
            if hasattr(obj, PREFIX + "loose_verts"):
                obj[PREFIX + "loose_verts"] = []
            if hasattr(obj, PREFIX + "inverted_normals"):
                obj[PREFIX + "inverted_normals"] = []
            if hasattr(obj, PREFIX + "non_manifold_edges"):
                obj[PREFIX + "non_manifold_edges"] = []
            if hasattr(obj, PREFIX + "non_manifold_verts"):
                obj[PREFIX + "non_manifold_verts"] = []
        
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            mesh = obj.data
            
            # Очистка кэшированных данных для текущего объекта
            obj[PREFIX + "boundary_edges"] = []
            obj[PREFIX + "loose_verts"] = []
            obj[PREFIX + "inverted_normals"] = []
            obj[PREFIX + "non_manifold_edges"] = []
            obj[PREFIX + "non_manifold_verts"] = []
            
            # Принудительное обновление данных меша
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
                errors.append(_("Open boundaries: {count} edges (<2 faces)").format(count=len(boundary_edges)))
                errors.append(_("Fill holes"))
                errors.append(_("Connect edges"))
                
            if loose_verts:
                errors.append(_("Loose geometry: {count} vertices (<2 edges)").format(count=len(loose_verts)))
                errors.append(_("Merge by distance"))
                errors.append(_("Delete extra vertices"))
                
            if inverted_normals:
                errors.append(_("Inverted normals: {count} polygons").format(count=len(inverted_normals)))
                errors.append(_("Flip normals"))
                errors.append(_("Recalculate outward"))
                
            if non_manifold_edges or non_manifold_verts:
                errors.append(_("Non-manifold: {edges} edges, {verts} vertices").format(
                    edges=len(non_manifold_edges), 
                    verts=len(non_manifold_verts)))
                errors.append(_("Delete internal surfaces"))
                errors.append(_("Apply boolean operation"))

            status = _("Watertight") if not errors else _("Not watertight")
            status_symbol = "✅ " + status if not errors else "❌ " + status
            results.append(f"{obj.name}: {status_symbol}")
            
            if errors:
                has_errors = True
                results.extend(errors)
                
                # Сохраняем проблемы для последующего выделения
                obj[PREFIX + "boundary_edges"] = [e.index for e in boundary_edges]
                obj[PREFIX + "loose_verts"] = [v.index for v in loose_verts]
                obj[PREFIX + "inverted_normals"] = [f.index for f in inverted_normals]
                obj[PREFIX + "non_manifold_edges"] = [e.index for e in non_manifold_edges]
                obj[PREFIX + "non_manifold_verts"] = [v.index for v in non_manifold_verts]
            else:
                # Очищаем данные о проблемах, если их нет
                obj[PREFIX + "boundary_edges"] = []
                obj[PREFIX + "loose_verts"] = []
                obj[PREFIX + "inverted_normals"] = []
                obj[PREFIX + "non_manifold_edges"] = []
                obj[PREFIX + "non_manifold_verts"] = []

            bm.free()

        # Формирование финального отчета
        report_msg = "\n".join(results)
        # Сохраняем error_types как строку с разделителем
        scene[PREFIX + "error_types"] = ",".join(error_types)
        scene[PREFIX + "report"] = report_msg
        
        if has_errors:
            self.report({'WARNING'}, _("Geometry problems detected"))
        else:
            self.report({'INFO'}, _("All meshes are watertight"))
            
        return {'FINISHED'}

class MESH_OT_recheck_watertight(Operator):
    bl_idname = "mesh.recheck_watertight"
    bl_label = _("Recheck Watertight Geometry")
    bl_description = _("Обновляет меш и проверяет замкнутость")
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Запоминаем текущий режим активного объекта
        active_obj = context.active_object
        if active_obj:
            prev_mode = active_obj.mode
            was_in_edit_mode = prev_mode == 'EDIT'
            
            # Если были в режиме редактирования, переключаем в объектный режим
            if was_in_edit_mode:
                bpy.ops.object.mode_set(mode='OBJECT')
                # Небольшая задержка для применения изменений
                bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
            
            # Выполняем проверку
            bpy.ops.mesh.check_watertight()
            
            # Возвращаем в предыдущий режим
            if was_in_edit_mode:
                bpy.ops.object.mode_set(mode='EDIT')
        else:
            # Если нет активного объекта, просто выполняем проверку
            bpy.ops.mesh.check_watertight()
        
        return {'FINISHED'}

class MESH_OT_select_watertight_problems(Operator):
    """Выделить конкретный тип проблем"""
    bl_idname = "mesh.select_watertight_problems"
    bl_label = _("Select Specific Problems")
    bl_options = {'REGISTER', 'UNDO'}
    
    problem_type: StringProperty(
        name="Problem Type",
        description=_("Тип проблемы для выделения")
    )
    
    def execute(self, context):
        log_message(f"Выделение проблемы типа: {self.problem_type}")
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, _("Select a mesh object"))
            return {'CANCELLED'}
        
        mesh = obj.data
        current_mode = obj.mode
        
        # Переходим в режим редактирования
        if current_mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        
        # Сбрасываем выделение
        bpy.ops.mesh.select_all(action='DESELECT')
        
        # Получаем bmesh из режима редактирования
        bm = bmesh.from_edit_mesh(mesh)
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        
        # Список для сбора всех проблемных элементов
        all_elements = []
        
        # Выделяем в зависимости от типа проблемы
        if self.problem_type == 'BOUNDARY':
            indices = obj.get(PREFIX + "boundary_edges", [])
            log_message(f"Найдено {len(indices)} граничных ребер")
            for idx in indices:
                if idx < len(bm.edges):
                    edge = bm.edges[idx]
                    edge.select = True
                    all_elements.append(edge)
        elif self.problem_type == 'LOOSE':
            indices = obj.get(PREFIX + "loose_verts", [])
            log_message(f"Найдено {len(indices)} неплотных вершин")
            for idx in indices:
                if idx < len(bm.verts):
                    vert = bm.verts[idx]
                    vert.select = True
                    all_elements.append(vert)
        elif self.problem_type == 'NORMALS':
            indices = obj.get(PREFIX + "inverted_normals", [])
            log_message(f"Найдено {len(indices)} полигонов с перевернутыми нормалями")
            for idx in indices:
                if idx < len(bm.faces):
                    face = bm.faces[idx]
                    face.select = True
                    all_elements.append(face)
        elif self.problem_type == 'MANIFOLD':
            indices_edges = obj.get(PREFIX + "non_manifold_edges", [])
            indices_verts = obj.get(PREFIX + "non_manifold_verts", [])
            log_message(f"Найдено {len(indices_edges)} не manifold ребер и {len(indices_verts)} не manifold вершин")
            for idx in indices_edges:
                if idx < len(bm.edges):
                    edge = bm.edges[idx]
                    edge.select = True
                    all_elements.append(edge)
            for idx in indices_verts:
                if idx < len(bm.verts):
                    vert = bm.verts[idx]
                    vert.select = True
                    all_elements.append(vert)
        
        # Обновляем меш
        bmesh.update_edit_mesh(mesh)
        
        # Сохраняем тип проблемы для навигации
        context.scene[PREFIX + "current_problem_type"] = self.problem_type
        context.scene[PREFIX + "current_focus_index"] = -1  # Сброс индекса
        
        # Фокусируем камеру на всем проблемном участке
        if all_elements:
            center = Vector()
            for element in all_elements:
                if isinstance(element, bmesh.types.BMVert):
                    center += element.co
                elif isinstance(element, bmesh.types.BMEdge):
                    center += (element.verts[0].co + element.verts[1].co) / 2
                elif isinstance(element, bmesh.types.BMFace):
                    center += element.calc_center_median()
            
            center /= len(all_elements)
            self.focus_on_location(context, center)
        
        # Оставляем пользователя в режиме редактирования
        log_message("Выделение завершено. Остаемся в режиме редактирования.")
        return {'FINISHED'}

    @staticmethod
    def focus_on_location(context, location):
        """Фокусирует камеру на конкретной локации без изменения масштаба"""
        region = context.region
        rv3d = context.region_data
        
        # Центрируем вид на локации
        rv3d.view_location = location
        
        # Обновляем вид
        context.area.tag_redraw()

class MESH_OT_focus_problem_element(Operator):
    """Фокусирует камеру на проблемном элементе"""
    bl_idname = "mesh.focus_problem_element"
    bl_label = _("Focus on Problem Element")
    bl_options = {'REGISTER', 'UNDO'}
    
    direction: EnumProperty(
        items=[
            ('PREV', _("Previous"), _("Фокус на предыдущем элементе")),
            ('NEXT', _("Next"), _("Фокус на следующем элементе"))
        ],
        default='NEXT'
    )
    
    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, _("Select a mesh object"))
            return {'CANCELLED'}
        
        scene = context.scene
        problem_type = scene.get(PREFIX + "current_problem_type", "")
        current_index = scene.get(PREFIX + "current_focus_index", -1)
        
        if not problem_type:
            self.report({'INFO'}, _("First select a problem"))
            return {'CANCELLED'}
        
        # Получаем список элементов для текущей проблемы
        elements = []
        if problem_type == 'BOUNDARY':
            elements = list(obj.get(PREFIX + "boundary_edges", []))
        elif problem_type == 'LOOSE':
            elements = list(obj.get(PREFIX + "loose_verts", []))
        elif problem_type == 'NORMALS':
            elements = list(obj.get(PREFIX + "inverted_normals", []))
        elif problem_type == 'MANIFOLD':
            # Преобразуем IDPropertyArray в списки
            edges = list(obj.get(PREFIX + "non_manifold_edges", []))
            verts = list(obj.get(PREFIX + "non_manifold_verts", []))
            elements = edges + verts
        
        if not elements:
            self.report({'INFO'}, _("No problem elements found"))
            return {'CANCELLED'}
        
        # Обновляем индекс в зависимости от направления
        if self.direction == 'NEXT':
            current_index = (current_index + 1) % len(elements)
        else:
            current_index = (current_index - 1) % len(elements)
        
        scene[PREFIX + "current_focus_index"] = current_index
        element_idx = elements[current_index]
        
        # Создаем BMesh для доступа к геометрии
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        
        # Получаем элемент по индексу
        element = None
        if problem_type == 'BOUNDARY' and element_idx < len(bm.edges):
            element = bm.edges[element_idx]
        elif problem_type == 'LOOSE' and element_idx < len(bm.verts):
            element = bm.verts[element_idx]
        elif problem_type == 'NORMALS' and element_idx < len(bm.faces):
            element = bm.faces[element_idx]
        elif problem_type == 'MANIFOLD':
            # Для non-manifold проверяем оба типа элементов
            if element_idx < len(bm.edges):
                element = bm.edges[element_idx]
            elif element_idx < len(bm.edges) + len(bm.verts):
                element = bm.verts[element_idx - len(bm.edges)]
        
        if element:
            # Вычисляем центр элемента
            if isinstance(element, bmesh.types.BMVert):
                center = element.co
            elif isinstance(element, bmesh.types.BMEdge):
                center = (element.verts[0].co + element.verts[1].co) / 2
            elif isinstance(element, bmesh.types.BMFace):
                center = element.calc_center_median()
            
            # Фокусируем камеру на элементе без изменения масштаба
            MESH_OT_select_watertight_problems.focus_on_location(context, center)
            self.report({'INFO'}, _("Focus on element {index}/{total}").format(
                index=current_index+1, 
                total=len(elements)))
        else:
            self.report({'WARNING'}, _("Element not found"))
        
        bm.free()
        return {'FINISHED'}

class VIEW3D_PT_watertight_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Инструменты'
    bl_label = _("Watertight Checker") + f" v{PLUGIN_VERSION}"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Заголовок с версией
        row = layout.row()
        row.label(text=_(self.bl_label), icon='MESH_CUBE')
        
        col = layout.column()
        
        # Кнопки Check и Recheck в одном ряду
        row = col.row(align=True)
        row.operator(MESH_OT_check_watertight.bl_idname, text=_("Check"))
        row.operator(MESH_OT_recheck_watertight.bl_idname, text=_("Recheck"))
        
        # Кнопки выделения проблем
        # Преобразуем строку обратно в множество
        error_types_str = scene.get(PREFIX + "error_types", "")
        error_types = set(error_types_str.split(",")) if error_types_str else set()
        
        if error_types:
            box = layout.box()
            box.label(text=_("Select problems:"))
            
            row = box.row()
            if "BOUNDARY" in error_types:
                op = row.operator("mesh.select_watertight_problems", text=_("Open boundaries"))
                op.problem_type = 'BOUNDARY'
            
            if "LOOSE" in error_types:
                op = row.operator("mesh.select_watertight_problems", text=_("Loose geometry"))
                op.problem_type = 'LOOSE'
            
            row = box.row()
            if "NORMALS" in error_types:
                op = row.operator("mesh.select_watertight_problems", text=_("Inverted normals"))
                op.problem_type = 'NORMALS'
            
            if "MANIFOLD" in error_types:
                op = row.operator("mesh.select_watertight_problems", text=_("Non-manifold"))
                op.problem_type = 'MANIFOLD'
            
            # Кнопки навигации по проблемным элементам
            problem_type = scene.get(PREFIX + "current_problem_type", "")
            if problem_type and problem_type in error_types:
                nav_box = box.box()
                nav_box.label(text=_("Focus on elements:"))
                
                row = nav_box.row(align=True)
                op_prev = row.operator("mesh.focus_problem_element", text="", icon='TRIA_LEFT')
                op_prev.direction = 'PREV'
                
                # Отображение текущей позиции
                row.label(text=_("Position:") + f" {scene.get(PREFIX + 'current_focus_index', -1) + 1}/{self.get_element_count(context, problem_type)}")
                
                op_next = row.operator("mesh.focus_problem_element", text="", icon='TRIA_RIGHT')
                op_next.direction = 'NEXT'
        
        # Предупреждение о проверке нормалей
        warning_box = layout.box()
        warning_box.label(text=_("Normal check is only reliable for convex objects"))
        warning_box.label(text=_("For concave shapes use standard normal analysis tools"))
        
        report = scene.get(PREFIX + "report", "")
        if report:
            box = layout.box()
            
            # Отчет о проблемах
            for line in report.split('\n'):
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
            if error_types:
                solutions_box = box.box()
                solutions_box.label(text=_("Additional solutions:"))
                
                col_solution = solutions_box.column(align=True)
                
                if "BOUNDARY" in error_types:
                    row = col_solution.row()
                    row.operator("mesh.fill", text=_("Fill holes (Fill)"))
                    row.operator("mesh.bridge_edge_loops", text=_("Connect edges (Bridge)"))
                
                if "LOOSE" in error_types:
                    row = col_solution.row()
                    row.operator("mesh.remove_doubles", text=_("Merge by Distance"))
                    row.operator("mesh.delete", text=_("Delete extra")).type = 'VERT'
                
                if "NORMALS" in error_types:
                    row = col_solution.row()
                    row.operator("mesh.flip_normals", text=_("Flip Normals"))
                    row.operator("mesh.normals_make_consistent", text=_("Recalculate Outside")).inside = False
                
                if "MANIFOLD" in error_types:
                    row = col_solution.row()
                    row.operator("mesh.delete_loose", text=_("Delete Loose"))
                    row.operator("mesh.intersect_boolean", text=_("Apply Boolean")).operation = 'DIFFERENCE'

    def get_element_count(self, context, problem_type):
        """Возвращает количество элементов для текущей проблемы"""
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return 0
        
        if problem_type == 'BOUNDARY':
            return len(obj.get(PREFIX + "boundary_edges", []))
        elif problem_type == 'LOOSE':
            return len(obj.get(PREFIX + "loose_verts", []))
        elif problem_type == 'NORMALS':
            return len(obj.get(PREFIX + "inverted_normals", []))
        elif problem_type == 'MANIFOLD':
            edges = len(obj.get(PREFIX + "non_manifold_edges", []))
            verts = len(obj.get(PREFIX + "non_manifold_verts", []))
            return edges + verts
        
        return 0

# Определяем классы ПОСЛЕ их объявления
classes = (
    MESH_OT_check_watertight,
    MESH_OT_recheck_watertight,
    MESH_OT_select_watertight_problems,
    MESH_OT_focus_problem_element,
    VIEW3D_PT_watertight_panel,
)

def register():
    log_message("Начало регистрации плагина")
    
    # Удаляем старые свойства, если они существуют
    safe_unregister()
    
    # Регистрируем классы
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
            log_message(f"Класс зарегистрирован: {cls.__name__}")
        except Exception as e:
            log_message(f"Ошибка регистрации класса {cls.__name__}: {str(e)}")
            log_message(traceback.format_exc())
    
    # Свойства сцены
    try:
        if not hasattr(bpy.types.Scene, PREFIX + "report"):
            bpy.types.Scene.wtc_report = StringProperty(
                name="Watertight Report",
                default=""
            )
            log_message("Свойство сцены wtc_report создано")
    except Exception as e:
        log_message(f"Ошибка создания wtc_report: {str(e)}")
        log_message(traceback.format_exc())
    
    try:
        if not hasattr(bpy.types.Scene, PREFIX + "error_types"):
            # Изменено на StringProperty для хранения множества
            bpy.types.Scene.wtc_error_types = StringProperty(
                name="Error Types",
                default=""
            )
            log_message("Свойство сцены wtc_error_types создано")
    except Exception as e:
        log_message(f"Ошибка создания wtc_error_types: {str(e)}")
        log_message(traceback.format_exc())
    
    try:
        if not hasattr(bpy.types.Scene, PREFIX + "current_problem_type"):
            bpy.types.Scene.wtc_current_problem_type = StringProperty(
                name="Current Problem Type",
                default=""
            )
            log_message("Свойство сцены wtc_current_problem_type создано")
    except Exception as e:
        log_message(f"Ошибка создания wtc_current_problem_type: {str(e)}")
        log_message(traceback.format_exc())
    
    try:
        if not hasattr(bpy.types.Scene, PREFIX + "current_focus_index"):
            bpy.types.Scene.wtc_current_focus_index = IntProperty(
                name="Current Focus Index",
                default=-1,
                min=-1
            )
            log_message("Свойство сцены wtc_current_focus_index создано")
    except Exception as e:
        log_message(f"Ошибка создания wtc_current_focus_index: {str(e)}")
        log_message(traceback.format_exc())
    
    # Свойства объектов
    obj_properties = [
        ("boundary_edges", "Индексы граничных ребер"),
        ("loose_verts", "Индексы вершин с недостаточным количеством соединений"),
        ("inverted_normals", "Индексы полигонов с перевернутыми нормалями"),
        ("non_manifold_edges", "Индексы не manifold ребер"),
        ("non_manifold_verts", "Индексы не manifold вершин")
    ]
    
    for prop_name, description in obj_properties:
        full_name = PREFIX + prop_name
        try:
            if hasattr(bpy.types.Object, full_name):
                log_message(f"Свойство {full_name} уже существует перед регистрацией")
            else:
                # Создаем свойство динамически
                prop = IntVectorProperty(
                    name=prop_name.capitalize().replace("_", " "),
                    default=(),
                    description=description
                )
                setattr(bpy.types.Object, full_name, prop)
                log_message(f"Свойство объекта {full_name} создано")
                
                # Проверяем, действительно ли создалось
                if hasattr(bpy.types.Object, full_name):
                    log_message(f"Подтверждение: свойство {full_name} существует после создания")
                else:
                    log_message(f"ОШИБКА: свойство {full_name} не создалось!")
        except Exception as e:
            log_message(f"Ошибка создания свойства {full_name}: {str(e)}")
            log_message(traceback.format_exc())
    
    # Регистрируем переводы
    register_translations()
    
    log_message("Регистрация плагина завершена")

def safe_unregister():
    """Безопасное удаление свойств и классов"""
    log_message("Начало безопасного удаления")
    
    # Список свойств для удаления
    obj_props = [
        "wtc_boundary_edges", 
        "wtc_loose_verts", 
        "wtc_inverted_normals", 
        "wtc_non_manifold_edges", 
        "wtc_non_manifold_verts"
    ]
    scene_props = ["wtc_report", "wtc_error_types", "wtc_current_problem_type", "wtc_current_focus_index"]
    
    # Удаляем свойства объектов
    for prop in obj_props:
        try:
            if hasattr(bpy.types.Object, prop):
                log_message(f"Удаление свойства объекта: {prop}")
                delattr(bpy.types.Object, prop)
            else:
                log_message(f"Свойство объекта {prop} не существует, пропускаем удаление")
        except Exception as e:
            log_message(f"Ошибка удаления свойства объекта {prop}: {str(e)}")
            log_message(traceback.format_exc())
    
    # Удаляем свойства сцены
    for prop in scene_props:
        try:
            if hasattr(bpy.types.Scene, prop):
                log_message(f"Удаление свойства сцены: {prop}")
                delattr(bpy.types.Scene, prop)
            else:
                log_message(f"Свойство сцены {prop} не существует, пропускаем удаление")
        except Exception as e:
            log_message(f"Ошибка удаления свойства сцены {prop}: {str(e)}")
            log_message(traceback.format_exc())
    
    # Удаляем классы
    for cls in classes:
        try:
            log_message(f"Попытка удаления класса: {cls.__name__}")
            bpy.utils.unregister_class(cls)
            log_message(f"Класс {cls.__name__} успешно удален")
        except Exception as e:
            log_message(f"Ошибка удаления класса {cls.__name__}: {str(e)}")
            log_message(traceback.format_exc())
    
    # Удаляем переводы
    unregister_translations()
    
    log_message("Безопасное удаление завершено")

def unregister():
    log_message("Начало удаления плагина")
    safe_unregister()
    log_message("Плагин полностью удален")