# Generated by Django 5.2.4 on 2025-07-18 02:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('MyTasks', '0003_alter_task_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='task',
            options={'ordering': ['due_date']},
        ),
    ]
