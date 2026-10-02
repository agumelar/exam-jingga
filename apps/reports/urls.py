from django.urls import path
from apps.reports import views

app_name = 'reports'

urlpatterns = [
    # Live Monitoring
    path('monitoring/', views.SessionMonitoringView.as_view(), name='session_monitoring'),
    path('monitoring/table/', views.SessionMonitoringTableView.as_view(), name='session_monitoring_table'),
    path('monitoring/unlock/<uuid:session_id>/', views.session_unlock_action, name='session_unlock'),
    path('monitoring/reset/<uuid:session_id>/', views.session_reset_action, name='session_reset'),
    path('monitoring/force-submit/<uuid:session_id>/', views.session_force_submit_action, name='session_force_submit'),

    # Exam Results & Distractor Analysis
    path('results/', views.ExamResultsListView.as_view(), name='exam_results_list'),
    path('results/<uuid:exam_id>/', views.ExamResultsView.as_view(), name='exam_results_detail'),
    path('results/<uuid:exam_id>/export/', views.ExamResultsExportView.as_view(), name='exam_results_export'),
    path('results/<uuid:exam_id>/analysis/', views.DistractorAnalysisView.as_view(), name='distractor_analysis'),

    # Printable Cards & Attendance
    path('cards/', views.ExamCardsView.as_view(), name='exam_cards'),
    path('attendance/', views.AttendanceListView.as_view(), name='attendance_list'),

    # Logistics Allocation
    path('logistics/', views.LogisticsView.as_view(), name='logistics'),
    path('logistics/generate/', views.logistics_generate_action, name='logistics_generate'),
    path('logistics/export/', views.LogisticsExportView.as_view(), name='logistics_export'),

    # Institutional Settings
    path('settings/', views.SettingsView.as_view(), name='settings'),
]
