# control_dashboard/urls.py

from django.urls import path
from . import views

app_name = 'control_dashboard'

urlpatterns = [
    # ==================== AUTHENTICATION ====================
    path('', views.landing_page, name='landing_page'),
    path('login/', views.landing_page, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # ==================== ADMIN URLS ====================
    path('admin/', views.admin_page, name='admin_page'),
    path('reports/', views.report_center, name='report_center'),
    
    # ==================== ADMIN ACTIVITY LOGS ====================
    path('activity-logs/', views.activity_logs, name='activity_logs'),  # <-- ADD THIS
    
    # ==================== MEMBER URLS ====================
    path('member/', views.member_dashboard, name='member_dashboard'),
    path('member/drafts/', views.drafts_page, name='drafts_page'),
    path('member/reports/', views.reports_page, name='reports_page'),
    path('member/submit/', views.submit_page, name='submit_page'),
    path('member/checklist/', views.member_checklist, name='member_checklist'),
    path('member/activity-logs/', views.member_activity_logs, name='member_activity_logs'),
    
    # ==================== SUPERVISOR URLS ====================
    path('supervisor/', views.supervisor_dashboard, name='supervisor_dashboard'),
    path('supervisor/team-performance/', views.team_performance, name='team_performance'),
    path('supervisor/submitted-reports/', views.submitted_reports, name='submitted_reports'),
    path('supervisor/ad-hoc-scorecard/', views.ad_hoc_scorecard, name='ad_hoc_scorecard'),
    path('supervisor/logged-exceptions/', views.logged_exceptions, name='logged_exceptions'),
    path('supervisor/checklist/', views.supervisor_checklist, name='supervisor_checklist'),
    path('supervisor/activity-logs/', views.supervisor_activity_logs, name='supervisor_activity_logs'),
    
    # ==================== API - AUTHENTICATION ====================
    path('api/email-login/', views.api_email_login, name='api_email_login'),
    path('api/user/profile/', views.get_user_profile_api, name='get_user_profile_api'),
    
    # ==================== API - ADMIN USER MANAGEMENT ====================
    path('api/users/create/', views.api_create_user, name='api_create_user'),
    path('api/users/<int:user_id>/edit/', views.api_edit_user, name='api_edit_user'),
    path('api/users/<int:user_id>/status/', views.api_update_status, name='api_update_status'),
    path('api/users/<int:user_id>/delete/', views.api_delete_user, name='api_delete_user'),
    
    # ==================== API - ADMIN REPORTS ====================
    path('api/admin/reports/create/', views.api_create_report, name='api_create_report'),
    path('api/admin/reports/<int:report_id>/', views.api_get_report, name='api_get_report'),
    path('api/admin/reports/<int:report_id>/edit/', views.api_edit_report, name='api_edit_report'),
    path('api/admin/reports/<int:report_id>/delete/', views.api_delete_report, name='api_delete_report'),

    # ==================== API - MEMBER DRAFTS ====================
    path('api/drafts/<str:report_id>/', views.api_get_draft, name='api_get_draft'),
    path('api/drafts/<str:report_id>/edit/', views.api_edit_draft, name='api_edit_draft'),
    path('api/drafts/<str:report_id>/delete/', views.api_delete_draft, name='api_delete_draft'),
    
    # ==================== API - TEMPLATES ====================
    path('api/template-fields/', views.api_get_template_fields, name='api_get_template_fields'),
    path('api/templates/create/', views.api_create_template, name='api_create_template'),
    path('api/templates/<int:template_id>/', views.api_get_template, name='api_get_template'),
    path('api/templates/<int:template_id>/edit/', views.api_edit_template, name='api_edit_template'),
    path('api/templates/<int:template_id>/delete/', views.api_delete_template, name='api_delete_template'),
    
    # ==================== API - CHECKLISTS ====================
    path('api/checklists/create/', views.api_create_checklist, name='api_create_checklist'),
    path('api/checklists/<int:checklist_id>/', views.api_get_checklist, name='api_get_checklist'),
    path('api/checklists/<int:checklist_id>/edit/', views.api_edit_checklist, name='api_edit_checklist'),
    path('api/checklists/<int:checklist_id>/delete/', views.api_delete_checklist, name='api_delete_checklist'),
    
    # ==================== API - CHECKLIST LOGS ====================
    path('api/checklist-log/', views.api_log_checklist, name='api_log_checklist'),
    path('api/checklist-logs/', views.api_get_checklist_logs, name='api_get_checklist_logs'),
    path('api/checklist-stats/', views.api_get_checklist_stats, name='api_get_checklist_stats'),
    
    # ==================== API - SUBMIT REPORTS ====================
    path('api/save-draft/', views.api_save_draft, name='api_save_draft'),
    path('api/report-data/', views.api_get_report_data, name='api_get_report_data'),
    
    # ==================== TEMPLATE BUILDER VIEWS ====================
    path('templates/', views.template_builder, name='template_builder'),
    
    # ==================== CHECKLIST BUILDER VIEWS ====================
    path('checklists/', views.checklist_builder, name='checklist_builder'),
    
    # ==================== API - EXPORT LOGS ====================
    path('api/export-logs/', views.api_export_logs, name='export_logs'),
    
    # ==================== API - CHECKLIST DETAIL ====================
    path('api/checklist/detail/<int:user_id>/', views.api_checklist_detail, name='api_checklist_detail'),
    # ==================== API - ADMIN REPORTS ====================
    path('api/reports/create/', views.api_create_report, name='api_create_report'),
    path('api/reports/<int:report_id>/', views.api_get_report, name='api_get_report'),
    path('api/reports/<int:report_id>/edit/', views.api_edit_report, name='api_edit_report'),
    path('api/reports/<int:report_id>/delete/', views.api_delete_report, name='api_delete_report'),
]