# MyTasks/urls.py
from django.urls import path
from .views import ProjectListView, ProjectDetailView, AssigneeSummaryView, TaskCreateView, TaskUpdateView

urlpatterns = [
    path('projects/', ProjectListView.as_view(), name='project-list'),
    path('project/<int:pk>/', ProjectDetailView.as_view(), name='project-detail'),
    path('summary/', AssigneeSummaryView.as_view(), name='assignee-summary'),
    path('project/<int:project_pk>/add-task/', TaskCreateView.as_view(), name='task-create'),
    path('task/<int:pk>/edit/', TaskUpdateView.as_view(), name='task-edit'),
]