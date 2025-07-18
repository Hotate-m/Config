# MyTasks/admin.py
from django.contrib import admin
from .models import Project, Task # ตรวจสอบให้แน่ใจว่า import Models ถูกต้อง

# --- Inline for Tasks within Project Admin ---
# การทำสิ่งนี้จะช่วยให้คุณสามารถเพิ่ม/แก้ไข Tasks ได้โดยตรงในหน้าแก้ไข Project
class TaskInline(admin.TabularInline): # หรือ admin.StackedInline
    model = Task
    extra = 1 # จำนวนช่องว่างสำหรับเพิ่ม Task ใหม่เริ่มต้น
    fields = ('task_name', 'description', 'assigned_to', 'due_date', 'status', 'parent_task')


# --- Project Admin Configuration ---
class ProjectAdmin(admin.ModelAdmin):
    # Fields ที่ต้องการให้แสดงในหน้า List ของ Project
    list_display = (
        'project_name',
        'start_date',
        'due_date',
        'status',
        'get_total_tasks_display', # แสดงจำนวน Tasks ทั้งหมด
        'get_completed_tasks_display', # แสดงจำนวน Tasks ที่เสร็จแล้ว
        'get_completion_percentage_display', # แสดง % ความคืบหน้า (จะคำนวณจาก Tasks)
    )

    # Fields ที่ต้องการให้สามารถค้นหาได้
    search_fields = (
        'project_name',
        'description',
        'status',
    )

    # Fields ที่ต้องการให้สามารถ Filter ได้จาก Sidebar ด้านขวา
    list_filter = (
        'status',
        'start_date',
        'due_date',
    )

    # กำหนดลำดับการแสดงผลเริ่มต้น
    ordering = ('-start_date',) # เรียงจากวันที่เริ่มต้นล่าสุดก่อน

    # เพิ่ม Task Inline เข้ามาในหน้าแก้ไข Project
    inlines = [TaskInline]

    # --- Custom methods for Project Admin ---
    def get_total_tasks_display(self, obj):
        return obj.tasks.count()
    get_total_tasks_display.short_description = 'Total Tasks'
    get_total_tasks_display.admin_order_field = 'tasks__count' # ช่วยให้เรียงลำดับได้ (ต้องมี annotation ใน get_queryset)

    def get_completed_tasks_display(self, obj):
        return obj.tasks.filter(status='completed').count()
    get_completed_tasks_display.short_description = 'Completed Tasks'
    get_completed_tasks_display.admin_order_field = 'completed_tasks_count' # ต้องมี annotation ใน get_queryset

    def get_completion_percentage_display(self, obj):
        total_tasks = obj.tasks.count()
        if total_tasks == 0:
            return "0%"
        completed_tasks = obj.tasks.filter(status='completed').count()
        percentage = round((completed_tasks / total_tasks) * 100)
        return f"{percentage}%"
    get_completion_percentage_display.short_description = 'Completion'
    get_completion_percentage_display.admin_order_field = 'completion_percentage' # ต้องมี annotation ใน get_queryset

    # Override get_queryset เพื่อให้สามารถเรียงลำดับตาม custom methods ได้
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        from django.db.models import Count, Case, When, IntegerField, F
        # Annotate total tasks
        queryset = queryset.annotate(
            _total_tasks_count=Count('tasks', distinct=True)
        )
        # Annotate completed tasks
        queryset = queryset.annotate(
            _completed_tasks_count=Count(Case(
                When(tasks__status='completed', then=1),
                output_field=IntegerField()
            ), distinct=True)
        )
        # Annotate completion percentage (handle division by zero)
        queryset = queryset.annotate(
            completion_percentage=Case(
                When(_total_tasks_count=0, then=0), # If no tasks, 0%
                default=(F('_completed_tasks_count') * 100 / F('_total_tasks_count')),
                output_field=IntegerField()
            )
        )
        return queryset

# --- Task Admin Configuration ---
class TaskAdmin(admin.ModelAdmin):
    # Fields ที่ต้องการให้แสดงในหน้า List ของ Task
    list_display = (
        'task_name',
        'project',          # แสดงชื่อ Project ที่ Task นี้อยู่
        'assigned_to',      # แสดงชื่อ User ที่ถูก assign
        'due_date',
        'status',
        'parent_task',      # แสดง Task แม่ (ถ้ามี)
    )

    # Fields ที่ต้องการให้สามารถค้นหาได้
    search_fields = (
        'task_name',
        'description',
        'status',
        'project__project_name', # ค้นหาตามชื่อ Project ที่เกี่ยวข้อง
        'assigned_to__username', # ค้นหาตาม username ของผู้ที่ถูก assign
        'parent_task__task_name', # ค้นหาตามชื่อ Task แม่
    )

    # Fields ที่ต้องการให้สามารถ Filter ได้จาก Sidebar ด้านขวา
    list_filter = (
        'status',
        'due_date',
        'project',          # Filter ตาม Project
        'assigned_to',      # Filter ตามผู้ที่ถูก assign
        'parent_task',      # Filter ตาม Task แม่
    )

    # กำหนดลำดับการแสดงผลเริ่มต้น
    ordering = ('due_date',) # เรียงตาม due_date โดย default

    # สำหรับ ForeignKey fields (assigned_to, parent_task)
    # raw_id_fields จะแสดงเป็นช่อง ID แทน dropdown list (เหมาะสำหรับข้อมูลเยอะๆ)
    # แต่ถ้าไม่เยอะ dropdown ก็สะดวกกว่า
    # raw_id_fields = ('assigned_to', 'parent_task',)

    # สำหรับ ForeignKey fields (assigned_to, parent_task) ที่อยากให้เป็น dropdown แต่ค้นหาได้
    autocomplete_fields = ['assigned_to', 'project', 'parent_task'] # Django 2.0+

    # fieldsets = ( # สามารถจัดกลุ่ม fields ในหน้า Add/Change ได้
    #     (None, {
    #         'fields': ('task_name', 'description', 'project', 'assigned_to',)
    #     }),
    #     ('Dates & Status', {
    #         'fields': ('due_date', 'status',)
    #     }),
    #     ('Hierarchy', {
    #         'fields': ('parent_task',)
    #     }),
    # )


# --- Register Models with their Admin classes ---
admin.site.register(Project, ProjectAdmin)
admin.site.register(Task, TaskAdmin)