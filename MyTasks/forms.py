# MyTasks/forms.py
from django import forms
from .models import Task, Project # Make sure Project is also imported if needed in forms.py
from django.contrib.auth.models import User # <--- ADD THIS LINE to import the User model

class SubtaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['task_name', 'description', 'assigned_to', 'due_date'] # ไม่ต้องใส่ 'project' หรือ 'parent_task' เพราะจะกำหนดใน view

    # เพื่อให้ input ของวันที่ใช้งานง่ายขึ้น (optional)
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False # Subtask อาจจะไม่ต้องมี Due Date ก็ได้
    )

    # เพื่อให้ input ของ description ไม่จำเป็นต้องใส่
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False)

    # เพิ่ม __init__ เพื่อจำกัด choices ของ assigned_to ให้เลือกเฉพาะ User ที่มีอยู่
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ตัวอย่าง: คุณอาจจะอยากกรอง User ที่เลือกได้ หรือเพิ่ม placeholder
        self.fields['assigned_to'].empty_label = "Select Assignee"

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['task_name', 'description', 'assigned_to', 'due_date', 'status', 'project', 'parent_task']
        # คุณสามารถกำหนด widgets หรือ labels เพิ่มเติมได้ที่นี่
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

    # เพิ่ม __init__ เพื่อจำกัด choices ของ assigned_to และ parent_task
    def __init__(self, *args, **kwargs):
        # ดึง project_instance ออกจาก kwargs ก่อนเรียก super().__init__
        project_instance = kwargs.pop('project_instance', None)
        super().__init__(*args, **kwargs)

        # กรอง assigned_to ให้เลือกเฉพาะ User ที่มีอยู่
        self.fields['assigned_to'].queryset = User.objects.all() # หรือกรองตามกลุ่ม/โปรเจกต์ที่ต้องการ
        self.fields['assigned_to'].empty_label = "Select Assignee"

        # กรอง parent_task ให้เลือกเฉพาะ Task หลัก (parent_task__isnull=True) ใน project เดียวกัน
        if project_instance:
            # Task ที่กำลังแก้ไขจะไม่สามารถเป็น parent_task ของตัวเองได้
            if self.instance and self.instance.pk: # ถ้าเป็นฟอร์มแก้ไข (มี instance)
                self.fields['parent_task'].queryset = Task.objects.filter(
                    project=project_instance,
                    parent_task__isnull=True
                ).exclude(pk=self.instance.pk) # ไม่รวมตัว Task เอง
            else: # ถ้าเป็นฟอร์มสร้าง (ไม่มี instance)
                self.fields['parent_task'].queryset = Task.objects.filter(
                    project=project_instance,
                    parent_task__isnull=True
                )
            self.fields['project'].initial = project_instance # ตั้งค่า project เริ่มต้น
            self.fields['project'].widget = forms.HiddenInput() # ซ่อนช่อง project ไม่ให้แก้ไข
        else:
            # ถ้าไม่มี project_instance (เช่น ไม่ได้มาจากหน้าเพิ่ม Task ใน Project)
            # ให้แสดงทุก Task ที่เป็น parent_task ได้ หรือคุณอาจจะต้องการปรับปรุงตรงนี้
            self.fields['parent_task'].queryset = Task.objects.filter(parent_task__isnull=True)

        self.fields['parent_task'].required = False # ทำให้ parent_task ไม่จำเป็นต้องใส่
        self.fields['parent_task'].empty_label = "No Parent Task"

        # ทำให้ description ไม่จำเป็นต้องใส่ใน TaskForm ด้วย (ถ้าต้องการ)
        self.fields['description'].required = False
        self.fields['description'].widget = forms.Textarea(attrs={'rows': 2}) # ปรับขนาด Textarea