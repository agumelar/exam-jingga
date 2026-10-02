"""URL configuration for Exam Jingga DATH Stack project."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('auth/login/', lambda r: __import__('apps.accounts.views', fromlist=['login_view']).login_view(r)),
    path('auth/logout/', lambda r: __import__('apps.accounts.views', fromlist=['logout_view']).logout_view(r)),
    path('auth/callback/', lambda r: __import__('apps.accounts.views', fromlist=['sso_callback_view']).sso_callback_view(r)),
    path('login/', lambda r: __import__('apps.accounts.views', fromlist=['login_view']).login_view(r), name='login_alias'),
    path('logout/', lambda r: __import__('apps.accounts.views', fromlist=['logout_view']).logout_view(r), name='logout_alias'),
    path('local-login/', lambda r: __import__('apps.accounts.views', fromlist=['local_login_view']).local_login_view(r), name='local_login_alias'),
    path('api/webhook/sync/', __import__('django.views.decorators.csrf', fromlist=['csrf_exempt']).csrf_exempt(__import__('apps.master_data.views', fromlist=['WebhookSyncView']).WebhookSyncView.as_view()), name='api_webhook_sync'),
    path('master/', include('apps.master_data.urls', namespace='master_data')),
    path('bank-soal/', include('apps.questions.urls', namespace='questions')),
    path('schedules/', include('apps.schedules.urls', namespace='schedules')),
    path('reports/', include('apps.reports.urls', namespace='reports')),
    path('', include('apps.exam_engine.urls', namespace='exam_engine')),
    # Direct route aliases matching sidebar navigation
    path('master-jurusan/', lambda r: __import__('apps.master_data.views', fromlist=['MajorListView']).MajorListView.as_view()(r)),
    path('master-kelas/', lambda r: __import__('apps.master_data.views', fromlist=['ClassRoomListView']).ClassRoomListView.as_view()(r)),
    path('master-guru/', lambda r: __import__('apps.master_data.views', fromlist=['TeacherListView']).TeacherListView.as_view()(r)),
    path('data-siswa/', lambda r: __import__('apps.master_data.views', fromlist=['StudentListView']).StudentListView.as_view()(r)),
    path('import-siswa/', __import__('apps.master_data.views', fromlist=['StudentImportView']).StudentImportView.as_view(), name='import_siswa'),
    path('import-siswa/template/', __import__('apps.master_data.views', fromlist=['StudentImportTemplateView']).StudentImportTemplateView.as_view(), name='import_siswa_template'),
    path('master-mapel/', __import__('apps.master_data.views', fromlist=['SubjectListView']).SubjectListView.as_view(), name='master_mapel'),
    path('master-mapel/template/', __import__('apps.master_data.views', fromlist=['SubjectTemplateExportView']).SubjectTemplateExportView.as_view(), name='master_mapel_template'),
    path('master-mapel/import/', __import__('apps.master_data.views', fromlist=['SubjectImportExcelView']).SubjectImportExcelView.as_view(), name='master_mapel_import'),
    path('master-mapel/<uuid:pk>/delete/', lambda r, pk: __import__('apps.master_data.views', fromlist=['SubjectDeleteView']).SubjectDeleteView.as_view()(r, pk=pk), name='master_mapel_delete'),
    path('penugasan-guru/', __import__('apps.master_data.views', fromlist=['TeacherAssignmentListView']).TeacherAssignmentListView.as_view(), name='penugasan_guru'),
    path('jadwal-ujian/', lambda r: __import__('apps.schedules.views', fromlist=['ScheduleListView']).ScheduleListView.as_view()(r)),
    path('select-questions/<uuid:exam_id>/', lambda r, exam_id: __import__('apps.schedules.views', fromlist=['SelectQuestionsView']).SelectQuestionsView.as_view()(r, exam_id=exam_id)),
    path('exam-participants/<uuid:schedule_id>/', lambda r, schedule_id: __import__('apps.reports.views', fromlist=['SessionMonitoringView']).SessionMonitoringView.as_view()(r, schedule_id=schedule_id), name='exam_participants_alias'),
    
    # Reports, Logistics, Monitoring & Settings aliases
    path('session-management/', lambda r: __import__('apps.reports.views', fromlist=['SessionMonitoringView']).SessionMonitoringView.as_view()(r), name='session_management_alias'),
    path('session-management/table/', lambda r: __import__('apps.reports.views', fromlist=['SessionMonitoringTableView']).SessionMonitoringTableView.as_view()(r), name='session_management_table_alias'),
    path('session-management/unlock/<uuid:session_id>/', lambda r, session_id: __import__('apps.reports.views', fromlist=['session_unlock_action']).session_unlock_action(r, session_id=session_id)),
    path('session-management/reset/<uuid:session_id>/', lambda r, session_id: __import__('apps.reports.views', fromlist=['session_reset_action']).session_reset_action(r, session_id=session_id)),
    path('session-management/force-submit/<uuid:session_id>/', lambda r, session_id: __import__('apps.reports.views', fromlist=['session_force_submit_action']).session_force_submit_action(r, session_id=session_id)),
    
    path('exam-results/', lambda r: __import__('apps.reports.views', fromlist=['ExamResultsListView']).ExamResultsListView.as_view()(r), name='exam_results_alias'),
    path('exam-results/<uuid:exam_id>/', lambda r, exam_id: __import__('apps.reports.views', fromlist=['ExamResultsView']).ExamResultsView.as_view()(r, exam_id=exam_id), name='exam_results_detail_alias'),
    path('exam-results/<uuid:exam_id>/export/', lambda r, exam_id: __import__('apps.reports.views', fromlist=['ExamResultsExportView']).ExamResultsExportView.as_view()(r, exam_id=exam_id)),
    path('exam-results/<uuid:exam_id>/analysis/', lambda r, exam_id: __import__('apps.reports.views', fromlist=['DistractorAnalysisView']).DistractorAnalysisView.as_view()(r, exam_id=exam_id)),

    path('exam-cards/', lambda r: __import__('apps.reports.views', fromlist=['ExamCardsView']).ExamCardsView.as_view()(r), name='exam_cards_alias'),
    path('attendance-list/', lambda r: __import__('apps.reports.views', fromlist=['AttendanceListView']).AttendanceListView.as_view()(r), name='attendance_list_alias'),
    path('logistics/', lambda r: __import__('apps.reports.views', fromlist=['LogisticsView']).LogisticsView.as_view()(r), name='logistics_alias'),
    path('settings/', lambda r: __import__('apps.reports.views', fromlist=['SettingsView']).SettingsView.as_view()(r), name='settings_alias'),

    # Sidebar menu exact aliases
    path('sesi-ruangan/', lambda r: __import__('apps.reports.views', fromlist=['SessionMonitoringView']).SessionMonitoringView.as_view()(r)),
    path('kartu-peserta/', lambda r: __import__('apps.reports.views', fromlist=['ExamCardsView']).ExamCardsView.as_view()(r)),
    path('daftar-hadir/', lambda r: __import__('apps.reports.views', fromlist=['AttendanceListView']).AttendanceListView.as_view()(r)),
    path('hasil-ujian/', lambda r: __import__('apps.reports.views', fromlist=['ExamResultsListView']).ExamResultsListView.as_view()(r)),
    path('pengaturan/', lambda r: __import__('apps.reports.views', fromlist=['SettingsView']).SettingsView.as_view()(r)),

    path('', include('apps.core.urls', namespace='core')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'apps.core.views.custom_404_view'
handler500 = 'apps.core.views.custom_500_view'
