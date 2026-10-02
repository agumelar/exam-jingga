"""URL configuration for Core CBT Exam Engine (Task 7)."""
from django.urls import path
from apps.exam_engine import views

app_name = 'exam_engine'

urlpatterns = [
    # Student Dashboard routes
    path('student-dashboard/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('student/dashboard/', views.StudentDashboardView.as_view(), name='student_dashboard_alt'),
    
    # Token Confirmation & Session Initialization
    path('exam/confirm-token/', views.ConfirmTokenView.as_view(), name='confirm_token'),
    
    # Live CBT Exam Interface & Interaction
    path('exam/session/<uuid:session_id>/', views.ExamInterfaceView.as_view(), name='exam_interface'),
    path('exam/session/<uuid:session_id>/question/<int:order_num>/', views.QuestionSwapView.as_view(), name='question_swap'),
    path('exam/session/<uuid:session_id>/save-answer/', views.SaveAnswerView.as_view(), name='save_answer'),
    
    # Anti-cheat Violation & Status Polling
    path('exam/session/<uuid:session_id>/violation/', views.ViolationHandlerView.as_view(), name='violation_handler'),
    path('exam/session/<uuid:session_id>/check-status/', views.StatusCheckView.as_view(), name='check_status'),
    
    # Final Submission & Auto-grading
    path('exam/session/<uuid:session_id>/finish/', views.FinishExamView.as_view(), name='finish_exam'),
]
