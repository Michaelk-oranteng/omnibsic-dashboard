# control_dashboard/urls.py

from django.urls import path
from . import views

app_name = 'control_dashboard'

urlpatterns = [
    # ==================== AUTHENTICATION URLs ====================
    # Login/Logout
    path('login/', views.login_view, name='login'),
    path('microsoft-login/', views.microsoft_login, name='microsoft_login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Test login (development only)
    path('test-login/<str:role>/', views.test_login, name='test_login'),
    
    # ==================== ADMIN URLs ====================
    # Admin page (root of the app)
    path('', views.admin_page, name='admin_page'),
    
    # Report Center
    path('reports_center/', views.report_center, name='report_center'),
    
    # Activity Logs
    path('activity/', views.activity_logs, name='activity_logs'),
    path('activity/export/', views.export_logs, name='export_logs'),
    
    # Template Builder
    path('templates/', views.template_builder, name='template_builder'),
    
    # Checklist Builder (Admin)
    path('checklist/', views.checklist_builder, name='checklist_builder'),
    
    # ==================== MEMBER URLs ====================
    # Member Dashboard
    path('member/', views.member_dashboard, name='member_dashboard'),
    
    # Member Checklist
    path('member/checklist/', views.member_checklist, name='member_checklist'),
    
    # Member Activity Logs
    path('member/activity/', views.member_activity_logs, name='member_activity_logs'),
    
    # ==================== SUPERVISOR URLs ====================
    # Supervisor Dashboard
    path('supervisor/', views.supervisor_dashboard, name='supervisor_dashboard'),
    
    # Supervisor Exceptions
    path('supervisor/exceptions/', views.supervisor_exceptions, name='supervisor_exceptions'),
    
    # Team Performance
    path('supervisor/team/', views.team_performance, name='team_performance'),
    
    # Submitted Reports
    path('supervisor/submitted/', views.submitted_reports, name='submitted_reports'),
    
    # Ad-Hoc Scorecard
    path('supervisor/ad-hoc/', views.ad_hoc_scorecard, name='ad_hoc_scorecard'),
    
    # Logged Exceptions
    path('supervisor/logged/', views.logged_exceptions, name='logged_exceptions'),
    
    # Supervisor Checklist
    path('supervisor/checklist/', views.supervisor_checklist, name='supervisor_checklist'),
    
    # Supervisor Activity Logs
    path('supervisor/activity/', views.supervisor_activity_logs, name='supervisor_activity_logs'),
    
    # ==================== DRAFTS & REPORTS URLs ====================
    # Drafts
    path('drafts/', views.drafts_page, name='drafts_page'),
    
    # Reports
    path('reports/', views.reports_page, name='reports_page'),
    
    # Submit
    path('submit/', views.submit_page, name='submit_page'),
    
    # ==================== API ENDPOINTS ====================
    
    # API - Users
    path('api/users/create/', views.api_create_user, name='api_create_user'),
    path('api/users/<int:user_id>/edit/', views.api_edit_user, name='api_edit_user'),
    path('api/users/<int:user_id>/status/', views.api_update_status, name='api_update_status'),
    
    # API - Reports
    path('api/reports/create/', views.api_create_report, name='api_create_report'),
    path('api/reports/<int:report_id>/', views.api_get_report, name='api_get_report'),
    path('api/reports/<int:report_id>/edit/', views.api_edit_report, name='api_edit_report'),
    path('api/reports/<int:report_id>/delete/', views.api_delete_report, name='api_delete_report'),
    
    # API - Activities
    path('api/activities/<int:activity_id>/', views.api_get_activity, name='api_get_activity'),
    path('api/activities/<int:activity_id>/edit/', views.api_edit_activity, name='api_edit_activity'),
    
    # API - Templates
    path('api/templates/create/', views.api_create_template, name='api_create_template'),
    path('api/templates/<int:template_id>/', views.api_get_template, name='api_get_template'),
    path('api/templates/<int:template_id>/edit/', views.api_edit_template, name='api_edit_template'),
    path('api/templates/<int:template_id>/delete/', views.api_delete_template, name='api_delete_template'),
    path('api/templates/assign/', views.api_assign_template_to_report, name='api_assign_template_to_report'),
    path('api/template/fields/', views.api_get_template_fields, name='api_get_template_fields'),
    
    # API - Checklists
    path('api/checklists/create/', views.api_create_checklist, name='api_create_checklist'),
    path('api/checklists/<int:checklist_id>/', views.api_get_checklist, name='api_get_checklist'),
    path('api/checklists/<int:checklist_id>/edit/', views.api_edit_checklist, name='api_edit_checklist'),
    path('api/checklists/<int:checklist_id>/delete/', views.api_delete_checklist, name='api_delete_checklist'),
    path('api/tasks/<int:task_id>/status/', views.api_update_task_status, name='api_update_task_status'),
    path('api/checklist/log/', views.api_log_checklist, name='api_log_checklist'),
    path('api/checklist/detail/<int:user_id>/', views.api_user_checklist_detail, name='api_user_checklist_detail'),
    
    # API - Drafts
    path('api/draft/save/', views.api_save_draft, name='api_save_draft'),
    path('api/draft/submit/', views.api_submit_draft, name='api_submit_draft'),
    path('api/draft/<int:draft_id>/', views.api_get_draft, name='api_get_draft'),
    path('api/draft/<int:draft_id>/delete/', views.api_delete_draft, name='api_delete_draft'),
    
    # API - Reports Submission
    path('api/report/submit/', views.api_submit_report, name='api_submit_report'),
    path('api/report/update-score/', views.api_update_report_score, name='api_update_report_score'),
    
    # API - Email
    path('api/send-email/', views.api_send_email, name='api_send_email'),
    
    # API - Team
    path('api/team/member/<int:user_id>/', views.api_team_member_detail, name='api_team_member_detail'),
    
    # API - Ad-Hoc Deductions
    path('api/ad-hoc/create/', views.api_create_ad_hoc_deduction, name='api_create_ad_hoc_deduction'),
    path('api/ad-hoc/<int:deduction_id>/update/', views.api_update_ad_hoc_deduction, name='api_update_ad_hoc_deduction'),
    path('api/ad-hoc/<int:deduction_id>/delete/', views.api_delete_ad_hoc_deduction, name='api_delete_ad_hoc_deduction'),
    
    # API - Exceptions
    path('api/exception/<int:exception_id>/', views.api_get_exception_detail, name='api_get_exception_detail'),
    path('api/exception/<int:exception_id>/update/', views.api_update_exception, name='api_update_exception'),
]