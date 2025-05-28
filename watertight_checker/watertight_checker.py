import bpy
import bmesh
import traceback
from bpy.types import Operator, Panel
from bpy.props import BoolProperty, StringProperty, IntVectorProperty
from mathutils import Vector

# Версия плагина в формате "год.месяцдень.minor"
PLUGIN_VERSION = "2025.528.22"  # 28 мая 2025, 22-я ревизия

# Уникальные префиксы для свойств
PREFIX = "wtc_"

# Функция для логгирования
def log_message(message):
    print(f"[Watertight Checker] {message}")

class MESH_OT_check_watertight(Operator):
    bl_idname = "mesh.check_watertight"
    bl_label = "Check Watertight Geometry"
    bl_description = "Проверяет замкнутость меша и наличие проблемных граней"
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
            self.report({'INFO'}, "Нет выделенных объектов для проверки")
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
            self.report({'WARNING'}, "Обнаружены проблемы в геометрии")
        else:
            self.report({'INFO'}, "Все меши замкнуты")
            
        return {'FINISHED'}

class MESH_OT_recheck_watertight(Operator):
    bl_idname = "mesh.recheck_watertight"
    bl_label = "Recheck Watertight Geometry"
    bl_description = "Обновляет меш и проверяет замкнутость"
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
    bl_label = "Select Specific Problems"
    bl_options = {'REGISTER', 'UNDO'}
    
    problem_type: bpy.props.StringProperty(
        name="Problem Type",
        description="Тип проблемы для выделения"
    )
    
    def execute(self, context):
        log_message(f"Выделение проблемы типа: {self.problem_type}")
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Выделите mesh-объект")
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
        
        # Выделяем в зависимости от типа проблемы
        if self.problem_type == 'BOUNDARY':
            indices = obj.get(PREFIX + "boundary_edges", [])
            log_message(f"Найдено {len(indices)} граничных ребер")
            for idx in indices:
                if idx < len(bm.edges):
                    bm.edges[idx].select = True
        elif self.problem_type == 'LOOSE':
            indices = obj.get(PREFIX + "loose_verts", [])
            log_message(f"Найдено {len(indices)} неплотных вершин")
            for idx in indices:
                if idx < len(bm.verts):
                    bm.verts[idx].select = True
        elif self.problem_type == 'NORMALS':
            indices = obj.get(PREFIX + "inverted_normals", [])
            log_message(f"Найдено {len(indices)} полигонов с перевернутыми нормалями")
            for idx in indices:
                if idx < len(bm.faces):
                    bm.faces[idx].select = True
        elif self.problem_type == 'MANIFOLD':
            indices_edges = obj.get(PREFIX + "non_manifold_edges", [])
            indices_verts = obj.get(PREFIX + "non_manifold_verts", [])
            log_message(f"Найдено {len(indices_edges)} не manifold ребер и {len(indices_verts)} не manifold вершин")
            for idx in indices_edges:
                if idx < len(bm.edges):
                    bm.edges[idx].select = True
            for idx in indices_verts:
                if idx < len(bm.verts):
                    bm.verts[idx].select = True
        
        # Обновляем меш
        bmesh.update_edit_mesh(mesh)
        
        # Оставляем пользователя в режиме редактирования
        log_message("Выделение завершено. Остаемся в режиме редактирования.")
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
        
        # Кнопки Check и Recheck в одном ряду
        row = col.row(align=True)
        row.operator(MESH_OT_check_watertight.bl_idname, text="Check")
        row.operator(MESH_OT_recheck_watertight.bl_idname, text="Recheck")
        
        # Кнопки выделения проблем
        # Преобразуем строку обратно в множество
        error_types_str = scene.get(PREFIX + "error_types", "")
        error_types = set(error_types_str.split(",")) if error_types_str else set()
        
        if error_types:
            box = layout.box()
            box.label(text="Выделить проблемы:")
            
            row = box.row()
            if "BOUNDARY" in error_types:
                op = row.operator("mesh.select_watertight_problems", text="Открытые границы")
                op.problem_type = 'BOUNDARY'
            
            if "LOOSE" in error_types:
                op = row.operator("mesh.select_watertight_problems", text="Неплотные соединения")
                op.problem_type = 'LOOSE'
            
            row = box.row()
            if "NORMALS" in error_types:
                op = row.operator("mesh.select_watertight_problems", text="Перевернутые нормали")
                op.problem_type = 'NORMALS'
            
            if "MANIFOLD" in error_types:
                op = row.operator("mesh.select_watertight_problems", text="Non-manifold")
                op.problem_type = 'MANIFOLD'
        
        # Предупреждение о проверке нормалей
        warning_box = layout.box()
        warning_box.label(text="Проверка нормалей корректна только для выпуклых объектов")
        warning_box.label(text="Для вогнутых форм используйте стандартные инструменты анализа нормалей")
        
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
                solutions_box.label(text="Дополнительные решения:")
                
                col_solution = solutions_box.column(align=True)
                
                if "BOUNDARY" in error_types:
                    row = col_solution.row()
                    row.operator("mesh.fill", text="Заполнить отверстия (Fill)")
                    row.operator("mesh.bridge_edge_loops", text="Соединить края (Bridge)")
                
                if "LOOSE" in error_types:
                    row = col_solution.row()
                    row.operator("mesh.remove_doubles", text="Объединить по расстоянию (Merge by Distance)")
                    row.operator("mesh.delete", text="Удалить лишнее (Delete)").type = 'VERT'
                
                if "NORMALS" in error_types:
                    row = col_solution.row()
                    row.operator("mesh.flip_normals", text="Перевернуть нормали (Flip Normals)")
                    row.operator("mesh.normals_make_consistent", text="Выровнять наружу (Recalculate Outside)").inside = False
                
                if "MANIFOLD" in error_types:
                    row = col_solution.row()
                    row.operator("mesh.delete_loose", text="Удалить лишнее (Delete Loose)")
                    row.operator("mesh.intersect_boolean", text="Применить Boolean").operation = 'DIFFERENCE'

# Определяем классы ПОСЛЕ их объявления
classes = (
    MESH_OT_check_watertight,
    MESH_OT_recheck_watertight,
    MESH_OT_select_watertight_problems,
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
    scene_props = ["wtc_report", "wtc_error_types"]
    
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
    
    log_message("Безопасное удаление завершено")

def unregister():
    log_message("Начало удаления плагина")
    safe_unregister()
    log_message("Плагин полностью удален")