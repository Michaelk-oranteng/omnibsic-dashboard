# control_dashboard/urls.py

from django.urls import path
from . import views

app_name = 'control_dashboard'

urlpatterns = [
    # ========================================================================
    # LANDING PAGE (Homepage)
    # ========================================================================
    path('', views.landing_page, name='landing_page'),
    
    
    # ========================================================================
    # AUTHENTICATION URLs
    # ========================================================================
    path('login/', views.login_view, name='login'),
    path('microsoft-login/', views.microsoft_login, name='microsoft_login'),
    path('logout/', views.logout_view, name='logout'),
    path('test-login/<str:role>/', views.test_login, name='test_login'),
    
    # ========================================================================
    # API - AUTHENTICATION
    # ========================================================================
    path('api/test-login/', views.api_test_login, name='api_test_login'),
    path('api/user/profile/', views.get_user_profile_api, name='get_user_profile_api'),
    
    # ========================================================================
    # ADMIN URLs
    # ========================================================================
    # Admin Dashboard
    path('admin/', views.admin_page, name='admin_page'),
    
    # Report Center
    path('reports-center/', views.report_center, name='report_center'),
    
    # Activity Logs
    path('activity-logs/', views.activity_logs, name='activity_logs'),
    path('activity-logs/export/', views.export_logs, name='export_logs'),
    
    # Template Builder
    path('templates/', views.template_builder, name='template_builder'),
    
    # Checklist Builder
    path('checklists/', views.checklist_builder, name='checklist_builder'),
    
    # ========================================================================
    # MEMBER URLs
    # ========================================================================
    path('member/', views.member_dashboard, name='member_dashboard'),
    path('member/checklist/', views.member_checklist, name='member_checklist'),
    path('member/activity-logs/', views.member_activity_logs, name='member_activity_logs'),
    
    # ========================================================================
    # SUPERVISOR URLs
    # ========================================================================
    path('supervisor/', views.supervisor_dashboard, name='supervisor_dashboard'),
    path('supervisor/exceptions/', views.supervisor_exceptions, name='supervisor_exceptions'),
    path('supervisor/team/', views.team_performance, name='team_performance'),
    path('supervisor/submitted/', views.submitted_reports, name='submitted_reports'),
    path('supervisor/ad-hoc/', views.ad_hoc_scorecard, name='ad_hoc_scorecard'),
    path('supervisor/logged-exceptions/', views.logged_exceptions, name='logged_exceptions'),
    path('supervisor/checklists/', views.supervisor_checklist, name='supervisor_checklist'),
    path('supervisor/activity-logs/', views.supervisor_activity_logs, name='supervisor_activity_logs'),
    
    # ========================================================================
    # DRAFTS & REPORTS URLs
    # ========================================================================
    path('drafts/', views.drafts_page, name='drafts_page'),
    path('reports/', views.reports_page, name='reports_page'),
    path('submit/', views.submit_page, name='submit_page'),
    
    # ========================================================================
    # API - USER MANAGEMENT
    # ========================================================================
    path('api/users/create/', views.api_create_user, name='api_create_user'),
    path('api/users/<int:user_id>/edit/', views.api_edit_user, name='api_edit_user'),
    path('api/users/<int:user_id>/status/', views.api_update_status, name='api_update_status'),
    path('api/users/<int:user_id>/delete/', views.api_delete_user, name='api_delete_user'),
    
    # ========================================================================
    # API - REPORT MANAGEMENT
    # ========================================================================
    path('api/reports/create/', views.api_create_report, name='api_create_report'),
    path('api/reports/<int:report_id>/', views.api_get_report, name='api_get_report'),
    path('api/reports/<int:report_id>/edit/', views.api_edit_report, name='api_edit_report'),
    path('api/reports/<int:report_id>/delete/', views.api_delete_report, name='api_delete_report'),
    path('api/reports/submit/', views.api_submit_report, name='api_submit_report'),
    path('api/reports/update-score/', views.api_update_report_score, name='api_update_report_score'),
    
    # ========================================================================
    # API - ACTIVITY MANAGEMENT
    # ========================================================================
    path('api/activities/<int:activity_id>/', views.api_get_activity, name='api_get_activity'),
    path('api/activities/<int:activity_id>/edit/', views.api_edit_activity, name='api_edit_activity'),
    
    # ========================================================================
    # API - TEMPLATE MANAGEMENT
    # ========================================================================
    path('api/templates/create/', views.api_create_template, name='api_create_template'),
    path('api/templates/<int:template_id>/', views.api_get_template, name='api_get_template'),
    path('api/templates/<int:template_id>/edit/', views.api_edit_template, name='api_edit_template'),
    path('api/templates/<int:template_id>/delete/', views.api_delete_template, name='api_delete_template'),
    path('api/templates/assign/', views.api_assign_template_to_report, name='api_assign_template_to_report'),
    path('api/templates/fields/', views.api_get_template_fields, name='api_get_template_fields'),
    
    # ========================================================================
    # API - CHECKLIST MANAGEMENT
    # ========================================================================
    path('api/checklists/create/', views.api_create_checklist, name='api_create_checklist'),
    path('api/checklists/<int:checklist_id>/', views.api_get_checklist, name='api_get_checklist'),
    path('api/checklists/<int:checklist_id>/edit/', views.api_edit_checklist, name='api_edit_checklist'),
    path('api/checklists/<int:checklist_id>/delete/', views.api_delete_checklist, name='api_delete_checklist'),
    path('api/checklists/log/', views.api_log_checklist, name='api_log_checklist'),
    path('api/checklists/detail/<int:user_id>/', views.api_user_checklist_detail, name='api_user_checklist_detail'),
    
    # ========================================================================
    # API - TASK MANAGEMENT
    # ========================================================================
    path('api/tasks/<int:task_id>/status/', views.api_update_task_status, name='api_update_task_status'),
    
    # ========================================================================
    # API - DRAFT MANAGEMENT
    # ========================================================================
    path('api/drafts/save/', views.api_save_draft, name='api_save_draft'),
    path('api/drafts/submit/', views.api_submit_draft, name='api_submit_draft'),
    path('api/drafts/<int:draft_id>/', views.api_get_draft, name='api_get_draft'),
    path('api/drafts/<int:draft_id>/delete/', views.api_delete_draft, name='api_delete_draft'),
    
    # ========================================================================
    # API - EMAIL
    # ========================================================================
    path('api/email/send/', views.api_send_email, name='api_send_email'),
    
    # ========================================================================
    # API - TEAM MANAGEMENT
    # ========================================================================
    path('api/team/member/<int:user_id>/', views.api_team_member_detail, name='api_team_member_detail'),
    
    # ========================================================================
    # API - AD-HOC DEDUCTIONS
    # ========================================================================
    path('api/ad-hoc/create/', views.api_create_ad_hoc_deduction, name='api_create_ad_hoc_deduction'),
    path('api/ad-hoc/<int:deduction_id>/update/', views.api_update_ad_hoc_deduction, name='api_update_ad_hoc_deduction'),
    path('api/ad-hoc/<int:deduction_id>/delete/', views.api_delete_ad_hoc_deduction, name='api_delete_ad_hoc_deduction'),
    
    # ========================================================================
    # API - EXCEPTION MANAGEMENT
    # ========================================================================
    path('api/exceptions/<int:exception_id>/', views.api_get_exception_detail, name='api_get_exception_detail'),
    path('api/exceptions/<int:exception_id>/update/', views.api_update_exception, name='api_update_exception'),
]