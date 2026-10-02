from django.contrib import admin
from .models import Major, ClassRoom, Teacher, Student, Subject, TeacherAssignment


@admin.register(Major)
class MajorAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'created_at')
    search_fields = ('code', 'name')


@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'major', 'created_at')
    list_filter = ('level', 'major')
    search_fields = ('name',)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'nip', 'email', 'role_level', 'created_at')
    list_filter = ('role_level',)
    search_fields = ('full_name', 'nip', 'email')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('nis', 'full_name', 'class_room', 'major', 'status', 'email')
    list_filter = ('status', 'major', 'class_room')
    search_fields = ('nis', 'full_name', 'email')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code')


@admin.register(TeacherAssignment)
class TeacherAssignmentAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'subject', 'class_room', 'created_at')
    list_filter = ('class_room', 'subject')
    search_fields = ('teacher__full_name', 'subject__name', 'subject_name', 'class_room__name')
