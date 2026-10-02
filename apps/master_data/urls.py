from django.urls import path
from . import views

app_name = 'master_data'

urlpatterns = [
    # Core Master Data URLs (prefixed with /master/)
    path('', views.MajorListView.as_view(), name='index'),
    path('majors/', views.MajorListView.as_view(), name='majors'),
    path('classes/', views.ClassRoomListView.as_view(), name='classes'),
    path('teachers/', views.TeacherListView.as_view(), name='teachers'),
    path('teachers/export/', views.TeacherExportExcelView.as_view(), name='teachers_export'),
    path('students/', views.StudentListView.as_view(), name='students'),
    path('students/export/', views.StudentExportExcelView.as_view(), name='students_export'),
    path('students/import/', views.StudentImportView.as_view(), name='students_import'),
    path('students/import/template/', views.StudentImportTemplateView.as_view(), name='students_import_template'),
    path('assignments/', views.TeacherAssignmentListView.as_view(), name='assignments'),
    path('subjects/', views.SubjectListView.as_view(), name='subjects'),
    path('subjects/template/', views.SubjectTemplateExportView.as_view(), name='subjects_template'),
    path('subjects/import/', views.SubjectImportExcelView.as_view(), name='subjects_import'),
    path('subjects/<uuid:pk>/delete/', views.SubjectDeleteView.as_view(), name='subjects_delete'),
    path('sync/', views.SyncMasterDataView.as_view(), name='sync'),
    path('webhook/sync/', views.WebhookSyncView.as_view(), name='webhook_sync'),
]

