# MyTasks/views.py
import datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from datetime import date, timedelta
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from .models import Project, Task
from django.contrib.auth.models import User
from django.db.models import Count, Q
from .forms import TaskForm

class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'MyTasks/project_list.html'
    context_object_name = 'projects'

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(
            total_tasks=Count('tasks', distinct=True),
            completed_tasks=Count('tasks', filter=Q(tasks__status='completed'), distinct=True)
        )

        for project in queryset:
            if project.total_tasks > 0:
                project.completion_percentage = int((project.completed_tasks / project.total_tasks) * 100)
            else:
                project.completion_percentage = 0

            # Calculate days left for project due date
            if project.due_date:
                today = date.today()
                delta = project.due_date - today
                project.days_left = delta.days
                project.is_due_soon = delta.days <= 7 # Consider due soon if 7 days or less
                if delta.days < 0:
                    project.overdue_days_abs = abs(delta.days)
            else:
                project.days_left = None
                project.is_due_soon = False
                project.overdue_days_abs = None
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.is_authenticated:
            # ค้นหางานที่ถูกมอบหมายให้ผู้ใช้ปัจจุบันและยังไม่เสร็จ (สถานะ to_do, in_progress, on_hold)
            user_assigned_pending_tasks_count = Task.objects.filter(
                assigned_to=user,
                status__in=['to_do', 'in_progress', 'on_hold']
            ).count()
            
            context['user_assigned_pending_tasks_count'] = user_assigned_pending_tasks_count
        else:
            context['user_assigned_pending_tasks_count'] = 0 # กำหนดเป็น 0 ถ้าผู้ใช้ไม่ได้เข้าสู่ระบบ
            
        return context


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'MyTasks/project_detail.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user # ดึงข้อมูลผู้ใช้ปัจจุบัน

        # ตรวจสอบว่าผู้ใช้เป็น Admin หรือไม่ (คุณอาจจะนิยาม Admin แตกต่างกันไปได้ เช่น is_staff, is_superuser)
        is_admin = user.is_staff or user.is_superuser

        # --- Logic for Project Completion and Due Date Countdown ---
        # เริ่มต้นด้วย queryset ของ Task ทั้งหมดที่เกี่ยวข้องกับ project นี้
        base_tasks_queryset = self.object.tasks.all()

        # ถ้าผู้ใช้ไม่ใช่ Admin ให้กรอง Task ที่ถูกมอบหมายให้ผู้ใช้คนนั้นเท่านั้น
        if not is_admin:
            base_tasks_queryset = base_tasks_queryset.filter(assigned_to=user)

        # ใช้ queryset ที่อาจถูกกรองแล้วสำหรับการคำนวณ Completion Percentage
        all_project_tasks_for_completion = base_tasks_queryset
        total_tasks_for_completion = all_project_tasks_for_completion.count()
        completed_tasks_for_completion = all_project_tasks_for_completion.filter(status='completed').count()

        self.object.completion_percentage = 0
        if total_tasks_for_completion > 0:
            self.object.completion_percentage = int((completed_tasks_for_completion / total_tasks_for_completion) * 100)

        self.object.days_left = None
        self.object.is_due_soon = False
        self.object.nearing_completion_text = ""
        self.object.overdue_days_abs = None

        if self.object.due_date:
            today = datetime.date.today()
            if self.object.due_date >= today:
                self.object.days_left = (self.object.due_date - today).days
                if self.object.days_left <= 7 and self.object.status not in ['completed', 'on_hold']:
                    self.object.is_due_soon = True
                    self.object.nearing_completion_text = "Nearing Deadline!"
            else: # Due date is in the past
                self.object.days_left = (today - self.object.due_date).days * -1
                self.object.overdue_days_abs = abs(self.object.days_left)
                if self.object.status not in ['completed', 'on_hold']:
                    self.object.is_due_soon = True
                    self.object.nearing_completion_text = "OVERDUE!"
        # --- End of Logic ---


        # ใช้ queryset ที่ถูกกรองแล้วสำหรับแสดง Task
        all_tasks = base_tasks_queryset.prefetch_related('subtasks', 'assigned_to')

        decorated_tasks = []
        for task in all_tasks:
            # Only process main tasks (tasks without a parent) here
            if not task.parent_task:
                task.subtasks_decorated = [] # Initialize list for decorated subtasks
                
                # ดึง Subtask ทั้งหมดของ Task นั้นๆ ก่อน
                raw_subtasks = task.subtasks.all()
                
                # ถ้าผู้ใช้ไม่ใช่ Admin ให้กรอง Subtask ที่ถูกมอบหมายให้ผู้ใช้คนนั้นเท่านั้น
                if not is_admin:
                    raw_subtasks = raw_subtasks.filter(assigned_to=user)

                for subtask in raw_subtasks: # วนลูปผ่าน Subtask ที่ถูกกรองแล้ว
                    self.decorate_task_with_progress(subtask)
                    task.subtasks_decorated.append(subtask)

                self.decorate_task_with_progress(task) # Decorate main task
                decorated_tasks.append(task)

        context['main_tasks'] = decorated_tasks

        # --- DEBUGGING PRINTS - THESE WILL SHOW IN YOUR TERMINAL ---
        print(f"\n--- Debugging Project Detail for Project PK: {self.object.pk} ---")
        print(f"Project Name: {self.object.project_name}")
        print(f"Is Admin: {is_admin}") # เพิ่ม debug สำหรับ is_admin
        print(f"Total tasks for completion (filtered): {total_tasks_for_completion}") # ระบุว่าอาจมีการกรองแล้ว
        print(f"Completed tasks for completion (filtered): {completed_tasks_for_completion}") # ระบุว่าอาจมีการกรองแล้ว
        print(f"Calculated completion percentage: {self.object.completion_percentage}")
        print("--- End Debugging ---\n")
        # --- END DEBUGGING PRINTS ---

        return context

    def decorate_task_with_progress(self, task):
        # Logic to calculate subtask completion percentage for main tasks
        if hasattr(task, 'subtasks_decorated') and task.subtasks_decorated:
            total_subtasks = len(task.subtasks_decorated)
            completed_subtasks = sum(1 for st in task.subtasks_decorated if st.status == 'completed')
            task.subtask_completion_percentage = int((completed_subtasks / total_subtasks) * 100) if total_subtasks > 0 else 0 # <-- แก้ไขบรรทัดนี้

            # เพิ่มโค้ดส่วนนี้
            task.incomplete_subtask_count = sum(1 for st in task.subtasks_decorated if st.status != 'completed')
            # --------------------
        else:
            task.subtask_completion_percentage = None # No subtasks
            task.incomplete_subtask_count = 0 # เพิ่มโค้ดส่วนนี้เพื่อกำหนดค่าเริ่มต้น


        # Calculate days left for task due date
        if task.due_date:
            today = date.today()
            delta = task.due_date - today
            task.days_left = delta.days
            task.is_due_soon = delta.days <= 3 # Task due soon if 3 days or less
            if delta.days < 0:
                task.overdue_days_abs = abs(delta.days)
            else:
                task.overdue_days_abs = None
        else:
            task.days_left = None
            task.is_due_soon = False
            task.overdue_days_abs = None


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'MyTasks/task_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project_instance'] = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        return kwargs

    def form_valid(self, form):
        project = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        form.instance.project = project
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('project-detail', kwargs={'pk': self.kwargs['project_pk']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = get_object_or_404(Project, pk=self.kwargs['project_pk'])
        context['project'] = project
        context['form_title'] = f"Add New Task for {project.project_name}"
        return context


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'MyTasks/task_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project_instance'] = self.object.project
        return kwargs

    def get_success_url(self):
        return reverse_lazy('project-detail', kwargs={'pk': self.object.project.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f"Edit Task: {self.object.task_name}"
        context['task'] = self.object
        return context


class AssigneeSummaryView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'MyTasks/assignee_summary.html'
    context_object_name = 'tasks_by_assignee'

    def get_queryset(self):
        tasks = Task.objects.select_related('assigned_to').order_by('assigned_to__username', 'due_date')

        tasks_by_assignee = {}
        for task in tasks:
            if task.assigned_to and task.assigned_to.first_name and task.assigned_to.last_name:
                assignee_full_name = f"{task.assigned_to.first_name} {task.assigned_to.last_name}"
            elif task.assigned_to:
                assignee_full_name = task.assigned_to.username
            else:
                assignee_full_name = "Unassigned"

            if assignee_full_name not in tasks_by_assignee:
                tasks_by_assignee[assignee_full_name] = {
                    'tasks': [],
                    'total_count': 0,
                    'completed_count': 0,
                    'level': 1
                }

            tasks_by_assignee[assignee_full_name]['tasks'].append(task)
            tasks_by_assignee[assignee_full_name]['total_count'] += 1
            if task.status == 'completed':
                tasks_by_assignee[assignee_full_name]['completed_count'] += 1

        for assignee_name, data in tasks_by_assignee.items():
            completed_tasks = data['completed_count']
            if completed_tasks < 5:
                tasks_by_assignee[assignee_name]['level'] = 1
            elif completed_tasks < 10:
                tasks_by_assignee[assignee_name]['level'] = 2
            elif completed_tasks < 15:
                tasks_by_assignee[assignee_name]['level'] = 3
            elif completed_tasks < 25:
                tasks_by_assignee[assignee_name]['level'] = 4
            else:
                tasks_by_assignee[assignee_name]['level'] = 5

        return tasks_by_assignee