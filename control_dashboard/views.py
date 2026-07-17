from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q, Count  # Add Count here
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json
import csv
from datetime import datetime, date, timedelta

from .models import UserProfile, ActivityLog, Report, ReportTemplate, TemplateField, TemplateAssignment, Checklist, ChecklistTask, Draft, DraftReview

# ==================== HELPER FUNCTION ====================

def log_activity(user, activity_type, details, request=None):
    """
    Helper function to log user activities.
    """
    try:
        ip_address = None
        user_agent = ''
        
        if request:
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        ActivityLog.objects.create(
            user=user,
            activity_type=activity_type,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    except Exception as e:
        # Silently fail if logging fails
        pass


# ==================== ADMIN PAGE ====================

def admin_page(request):
    """
    Main admin dashboard view with filtering and search.
    """
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    position_filter = request.GET.get('position', '')
    
    # Start with all users
    users = UserProfile.objects.all()
    
    # Apply filters
    if search_query:
        users = users.filter(
            Q(email__icontains=search_query) |
            Q(full_name__icontains=search_query)
        )
    
    if status_filter:
        users = users.filter(status=status_filter)
    
    if position_filter:
        users = users.filter(position=position_filter)
    
    # Statistics
    total_users = UserProfile.objects.count()
    active_users = UserProfile.objects.filter(status='active').count()
    inactive_users = UserProfile.objects.filter(status='inactive').count()
    hoc_users = UserProfile.objects.filter(position='hoc').count()
    cc_users = UserProfile.objects.filter(position='cc').count()
    
    context = {
        'users': users,
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'hoc_users': hoc_users,
        'cc_users': cc_users,
        'search_query': search_query,
        'status_filter': status_filter,
        'position_filter': position_filter,
        'statuses': UserProfile.STATUS_CHOICES,
        'positions': UserProfile.POSITION_CHOICES,
        'roles': UserProfile.ROLE_CHOICES,
    }
    
    return render(request, 'control_dashboard/adminboard.html', context)


# ==================== REPORT CENTER ====================

def report_center(request):
    """
    Report Center view with filtering.
    """
    status_filter = request.GET.get('status', '')
    user_filter = request.GET.get('user', '')
    
    reports = Report.objects.all()
    
    if status_filter and status_filter != 'all':
        reports = reports.filter(status=status_filter)
    
    if user_filter and user_filter != 'all':
        reports = reports.filter(assigned_to__id=user_filter)
    
    # Statistics
    total_reports = Report.objects.count()
    assigned_reports = Report.objects.filter(status='assigned').count()
    in_progress_reports = Report.objects.filter(status='in_progress').count()
    completed_reports = Report.objects.filter(status='completed').count()
    
    users = UserProfile.objects.all()
    
    context = {
        'reports': reports,
        'users': users,
        'total_reports': total_reports,
        'assigned_reports': assigned_reports,
        'in_progress_reports': in_progress_reports,
        'completed_reports': completed_reports,
        'status_filter': status_filter,
        'user_filter': user_filter,
        'report_statuses': Report.STATUS_CHOICES,
    }
    
    return render(request, 'control_dashboard/reportcenter.html', context)


# ==================== ACTIVITY LOGS ====================

def activity_logs(request):
    """
    Activity logs view with filtering.
    """
    # Get filter parameters
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    activity_filter = request.GET.get('activity', '')
    user_filter = request.GET.get('user', '')
    
    # Start with all logs
    logs = ActivityLog.objects.all()
    
    # Apply filters
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            logs = logs.filter(created_at__date__gte=start)
        except:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            logs = logs.filter(created_at__date__lte=end)
        except:
            pass
    
    if activity_filter and activity_filter != 'all':
        logs = logs.filter(activity_type=activity_filter)
    
    if user_filter and user_filter != 'all':
        logs = logs.filter(user_id=user_filter)
    
    # Get all users for filter dropdown
    users = UserProfile.objects.all()
    
    context = {
        'activity_logs': logs,
        'users': users,
        'activity_types': ActivityLog.ACTIVITY_CHOICES,
        'start_date': start_date,
        'end_date': end_date,
        'activity_filter': activity_filter,
        'user_filter': user_filter,
    }
    
    return render(request, 'control_dashboard/activity.html', context)


# ==================== TEMPLATE BUILDER ====================

def template_builder(request):
    """
    Template Builder view.
    """
    templates = ReportTemplate.objects.all().order_by('-created_at')
    users = UserProfile.objects.all()
    
    # Get all unique report types from existing reports
    report_types = Report.objects.values_list('report_type', flat=True).distinct()
    # Also get from templates that might have custom types
    template_report_types = ReportTemplate.objects.values_list('name', flat=True).distinct()
    # Combine and get unique values
    all_report_types = list(set(list(report_types) + list(template_report_types)))
    all_report_types.sort()
    
    context = {
        'templates': templates,
        'users': users,
        'field_types': ReportTemplate.FIELD_TYPES,
        'data_sources': ReportTemplate.DATA_SOURCES,
        'report_types': all_report_types,
    }
    
    return render(request, 'control_dashboard/reporttemplate.html', context)


# ==================== CHECKLIST BUILDER ====================

def checklist_builder(request):
    """
    Checklist Builder view.
    """
    checklists = Checklist.objects.all().order_by('-created_at')
    users = UserProfile.objects.all()
    
    context = {
        'checklists': checklists,
        'users': users,
        'frequencies': Checklist.FREQUENCY_CHOICES,
        'assignments': Checklist.ASSIGNMENT_CHOICES,
    }
    
    return render(request, 'control_dashboard/checklist.html', context)


# ==================== MEMBER DASHBOARD ====================

def member_dashboard(request):
    """
    Member Dashboard view.
    """
    # Get the current user's profile
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except (UserProfile.DoesNotExist, AttributeError):
        user_profile = UserProfile.objects.first()
    
    # Calculate the week range (Thursday to Wednesday)
    today = timezone.now().date()
    
    # Find the most recent Thursday (if today is Thursday, use today)
    days_since_thursday = (today.weekday() - 3) % 7
    week_start = today - timedelta(days=days_since_thursday)
    week_end = week_start + timedelta(days=6)  # Wednesday
    
    # 1. Get checklists assigned to this user (Daily frequency only)
    daily_checklists = Checklist.objects.filter(
        frequency='daily'
    ).filter(
        Q(assigned_users=user_profile) | 
        Q(assignment_target='all')
    ).distinct().order_by('-created_at')[:10]
    
    # 2. Get exceptions logged this week (Thursday to Wednesday)
    exceptions_this_week = ActivityLog.objects.filter(
        user=user_profile,
        activity_type='exception',
        created_at__date__gte=week_start,
        created_at__date__lte=week_end
    ).count()
    
    # 3. Get assigned tasks this week
    assigned_this_week = Checklist.objects.filter(
        Q(assigned_users=user_profile) | 
        Q(assignment_target='all')
    ).filter(
        created_at__date__gte=week_start,
        created_at__date__lte=week_end
    ).count()
    
    # 4. Get pending submissions (reports assigned but not submitted)
    pending_submissions = Report.objects.filter(
        assigned_to=user_profile,
        status__in=['assigned', 'in_progress']
    ).count()
    
    # 5. Get recent submissions
    recent_submissions = Report.objects.filter(
        created_by=user_profile
    ).order_by('-created_at')[:5]
    
    context = {
        'user_profile': user_profile,
        'daily_checklists': daily_checklists,
        'recent_submissions': recent_submissions,
        'assigned_this_week': assigned_this_week,
        'exceptions_this_week': exceptions_this_week,
        'pending_submissions': pending_submissions,
        'today': timezone.now(),
        'week_start': week_start,
        'week_end': week_end,
    }
    
    return render(request, 'control_dashboard/memberboard.html', context)


# ==================== MEMBER CHECKLIST ====================

def member_checklist(request):
    """
    Member Checklist view - shows checklists assigned to the user.
    """
    # Get the current user's profile
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except (UserProfile.DoesNotExist, AttributeError):
        user_profile = UserProfile.objects.first()
    
    # Get checklists assigned to this user OR assigned to 'all'
    checklists = Checklist.objects.filter(
        Q(assigned_users=user_profile) | 
        Q(assignment_target='all')
    ).distinct().order_by('-created_at')
    
    # Build checklist data with logs included
    checklist_data = []
    for checklist in checklists:
        # Get logs from activity logs for this checklist
        logs = ActivityLog.objects.filter(
            user=user_profile,
            activity_type='checklist_updated',
            details__icontains=checklist.name
        ).values_list('created_at__date', flat=True).distinct()
        
        log_dates = [log.strftime('%Y-%m-%d') for log in logs if log]
        
        checklist_data.append({
            'id': checklist.id,
            'name': checklist.name,
            'frequency': checklist.frequency,
            'frequency_display': checklist.get_frequency_display(),
            'tasks': checklist.tasks.all(),
            'logs': log_dates,
        })
    
    context = {
        'user_profile': user_profile,
        'checklist_data': checklist_data,
        'today': timezone.now(),
    }
    
    return render(request, 'control_dashboard/checklist-mem.html', context)


# ==================== EXPORT LOGS ====================

def export_logs(request):
    """
    Export activity logs as CSV.
    """
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    activity_filter = request.GET.get('activity', '')
    user_filter = request.GET.get('user', '')
    
    logs = ActivityLog.objects.all()
    
    # Apply filters
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            logs = logs.filter(created_at__date__gte=start)
        except:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            logs = logs.filter(created_at__date__lte=end)
        except:
            pass
    
    if activity_filter and activity_filter != 'all':
        logs = logs.filter(activity_type=activity_filter)
    
    if user_filter and user_filter != 'all':
        logs = logs.filter(user_id=user_filter)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="activity_logs_{timezone.now().date()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date & Time', 'User', 'Activity', 'Details', 'IP Address'])
    
    for log in logs:
        writer.writerow([
            log.created_at.strftime('%Y-%m-%d %H:%M'),
            log.user.full_name or log.user.email,
            log.get_activity_type_display(),
            log.details,
            log.ip_address or 'N/A'
        ])
    
    # Log the export activity
    try:
        user = UserProfile.objects.first()
        if user:
            log_activity(
                user=user,
                activity_type='export',
                details=f'Exported activity logs ({logs.count()} records)',
                request=request
            )
    except:
        pass
    
    return response


# ==================== API - USER ENDPOINTS ====================

@csrf_exempt
@require_http_methods(["POST"])
def api_create_user(request):
    """
    API endpoint to create a new user with activity logging.
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        
        if not email:
            return JsonResponse({'success': False, 'error': 'Email is required'}, status=400)
        
        if UserProfile.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'User with this email already exists'}, status=400)
        
        user = UserProfile.objects.create(
            email=email,
            full_name=data.get('full_name', '').strip(),
            position=data.get('position', 'hoc'),
            role=data.get('role', 'member'),
            status=data.get('status', 'active')
        )
        
        # Log the activity
        log_activity(
            user=user,
            activity_type='user_created',
            details=f'User {email} was created with role {user.get_role_display()}',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'User created successfully',
            'user_id': user.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def api_edit_user(request, user_id):
    """
    API endpoint to edit an existing user with activity logging.
    """
    try:
        user = get_object_or_404(UserProfile, id=user_id)
        data = json.loads(request.body)
        
        changes = []
        
        if 'email' in data:
            new_email = data['email'].strip()
            if new_email and new_email != user.email:
                if UserProfile.objects.filter(email=new_email).exclude(id=user_id).exists():
                    return JsonResponse({'success': False, 'error': 'Email already in use'}, status=400)
                changes.append(f'Email changed from {user.email} to {new_email}')
                user.email = new_email
        
        if 'full_name' in data and data['full_name'] != user.full_name:
            changes.append(f'Full name changed to {data["full_name"]}')
            user.full_name = data['full_name'].strip()
        
        if 'position' in data and data['position'] != user.position:
            old_pos = user.get_position_display()
            user.position = data['position']
            changes.append(f'Position changed from {old_pos} to {user.get_position_display()}')
        
        if 'role' in data and data['role'] != user.role:
            old_role = user.get_role_display()
            user.role = data['role']
            changes.append(f'Role changed from {old_role} to {user.get_role_display()}')
        
        if 'status' in data and data['status'] != user.status:
            old_status = user.get_status_display()
            user.status = data['status']
            changes.append(f'Status changed from {old_status} to {user.get_status_display()}')
        
        user.save()
        
        if changes:
            log_activity(
                user=user,
                activity_type='user_updated',
                details=f'User {user.email} updated: ' + '; '.join(changes),
                request=request
            )
        
        return JsonResponse({
            'success': True,
            'message': 'User updated successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_update_status(request, user_id):
    """
    API endpoint to toggle user status with activity logging.
    """
    try:
        user = get_object_or_404(UserProfile, id=user_id)
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if new_status not in ['active', 'inactive']:
            return JsonResponse({'success': False, 'error': 'Invalid status value'}, status=400)
        
        old_status = user.get_status_display()
        user.status = new_status
        user.save()
        
        log_activity(
            user=user,
            activity_type='user_status_changed',
            details=f'User {user.email} status changed from {old_status} to {user.get_status_display()}',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': f'User status updated to {new_status}'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_delete_user(request, user_id):
    """
    API endpoint to delete a user with activity logging.
    """
    try:
        user = get_object_or_404(UserProfile, id=user_id)
        email = user.email
        
        log_activity(
            user=user,
            activity_type='user_deleted',
            details=f'User {email} was deleted',
            request=request
        )
        
        user.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'User deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==================== API - REPORT ENDPOINTS ====================

@csrf_exempt
@require_http_methods(["POST"])
def api_create_report(request):
    """
    API endpoint to create a new report with activity logging.
    """
    try:
        data = json.loads(request.body)
        
        report_type = data.get('report_type', '').strip()
        frequency = data.get('frequency', 'one-off')
        description = data.get('description', '').strip()
        deadline_date = data.get('deadline_date', '')
        deadline_time = data.get('deadline_time', '')
        assigned_users = data.get('assigned_users', [])
        
        if not report_type:
            return JsonResponse({'success': False, 'error': 'Report type is required'}, status=400)
        
        if not assigned_users:
            return JsonResponse({'success': False, 'error': 'Please assign at least one user'}, status=400)
        
        # Get the current user (using the first user for now)
        created_by = UserProfile.objects.first()
        if not created_by:
            return JsonResponse({'success': False, 'error': 'No user found'}, status=400)
        
        # Create the report
        report = Report.objects.create(
            report_type=report_type,
            frequency=frequency,
            description=description,
            deadline_date=deadline_date if deadline_date else None,
            deadline_time=deadline_time if deadline_time else None,
            created_by=created_by,
            status='assigned'
        )
        
        # Assign users
        assigned_count = 0
        for user_id in assigned_users:
            try:
                user = UserProfile.objects.get(id=user_id)
                report.assigned_to.add(user)
                assigned_count += 1
            except UserProfile.DoesNotExist:
                pass
        
        # Log the activity
        log_activity(
            user=created_by,
            activity_type='report_created',
            details=f'Created report: {report_type} (Frequency: {frequency}) assigned to {assigned_count} users',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Report created successfully',
            'report_id': report.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_get_report(request, report_id):
    """
    API endpoint to get report details.
    """
    try:
        report = get_object_or_404(Report, id=report_id)
        
        return JsonResponse({
            'success': True,
            'report': {
                'id': report.id,
                'report_type': report.report_type,
                'frequency': report.frequency,
                'description': report.description,
                'status': report.status,
                'deadline_date': report.deadline_date.strftime('%Y-%m-%d') if report.deadline_date else '',
                'deadline_time': report.deadline_time.strftime('%H:%M') if report.deadline_time else '',
                'assigned_users': list(report.assigned_to.values_list('id', flat=True)),
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def api_edit_report(request, report_id):
    """
    API endpoint to edit a report with activity logging.
    """
    try:
        report = get_object_or_404(Report, id=report_id)
        data = json.loads(request.body)
        
        changes = []
        
        if 'report_type' in data and data['report_type'] != report.report_type:
            changes.append(f'Type changed from {report.report_type} to {data["report_type"]}')
            report.report_type = data['report_type']
        
        if 'frequency' in data and data['frequency'] != report.frequency:
            old_freq = report.get_frequency_display()
            report.frequency = data['frequency']
            changes.append(f'Frequency changed from {old_freq} to {report.get_frequency_display()}')
        
        if 'description' in data:
            report.description = data['description']
        
        if 'status' in data and data['status'] != report.status:
            old_status = report.get_status_display()
            report.status = data['status']
            changes.append(f'Status changed from {old_status} to {report.get_status_display()}')
        
        if 'deadline_date' in data:
            report.deadline_date = data['deadline_date'] if data['deadline_date'] else None
        
        if 'deadline_time' in data:
            report.deadline_time = data['deadline_time'] if data['deadline_time'] else None
        
        # Update assigned users
        if 'assigned_users' in data:
            report.assigned_to.clear()
            for user_id in data['assigned_users']:
                try:
                    user = UserProfile.objects.get(id=user_id)
                    report.assigned_to.add(user)
                except UserProfile.DoesNotExist:
                    pass
            changes.append('Assigned users updated')
        
        report.save()
        
        # Log the activity
        if changes:
            log_activity(
                user=report.created_by,
                activity_type='report_updated',
                details=f'Report {report.report_type} updated: ' + '; '.join(changes),
                request=request
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Report updated successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_delete_report(request, report_id):
    """
    API endpoint to delete a report with activity logging.
    """
    try:
        report = get_object_or_404(Report, id=report_id)
        report_type = report.report_type
        
        # Log before deletion
        log_activity(
            user=report.created_by,
            activity_type='report_deleted',
            details=f'Report "{report_type}" was deleted',
            request=request
        )
        
        report.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Report deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==================== API - ACTIVITY ENDPOINTS ====================

@csrf_exempt
@require_http_methods(["GET"])
def api_get_activity(request, activity_id):
    """
    API endpoint to get activity details for editing.
    """
    try:
        activity = get_object_or_404(ActivityLog, id=activity_id)
        
        return JsonResponse({
            'success': True,
            'activity': {
                'id': activity.id,
                'user': activity.user.id,
                'activity_type': activity.activity_type,
                'details': activity.details,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def api_edit_activity(request, activity_id):
    """
    API endpoint to edit an activity log with logging.
    """
    try:
        activity = get_object_or_404(ActivityLog, id=activity_id)
        data = json.loads(request.body)
        
        changes = []
        
        if 'user_id' in data:
            user = get_object_or_404(UserProfile, id=data['user_id'])
            old_user = activity.user.email
            activity.user = user
            changes.append(f'User changed from {old_user} to {user.email}')
        
        if 'activity_type' in data and data['activity_type'] != activity.activity_type:
            old_type = activity.get_activity_type_display()
            activity.activity_type = data['activity_type']
            changes.append(f'Activity type changed from {old_type} to {activity.get_activity_type_display()}')
        
        if 'details' in data and data['details'] != activity.details:
            changes.append('Details updated')
            activity.details = data['details']
        
        activity.save()
        
        # Log the activity
        if changes:
            log_activity(
                user=activity.user,
                activity_type='activity_edited',
                details=f'Activity log edited: ' + '; '.join(changes),
                request=request
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Activity updated successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==================== API - TEMPLATE ENDPOINTS ====================

@csrf_exempt
@require_http_methods(["POST"])
def api_create_template(request):
    """
    API endpoint to create a new template with fields.
    """
    try:
        data = json.loads(request.body)
        
        report_type = data.get('report_type', '').strip()
        description = data.get('description', '').strip()
        fields = data.get('fields', [])
        
        if not report_type:
            return JsonResponse({'success': False, 'error': 'Report type is required'}, status=400)
        
        # Get the current user
        created_by = UserProfile.objects.first()
        if not created_by:
            return JsonResponse({'success': False, 'error': 'No user found'}, status=400)
        
        # Check if template with same name exists
        if ReportTemplate.objects.filter(name=report_type).exists():
            return JsonResponse({'success': False, 'error': 'A template for this report type already exists'}, status=400)
        
        # Create the template
        template = ReportTemplate.objects.create(
            name=report_type,
            description=description,
            created_by=created_by,
            is_active=True
        )
        
        # Create fields
        field_count = 0
        for field_data in fields:
            TemplateField.objects.create(
                template=template,
                label=field_data.get('label', '').strip(),
                field_type=field_data.get('field_type', 'text'),
                data_source=field_data.get('data_source', 'manual'),
                is_required=field_data.get('is_required', False),
                options=field_data.get('options', ''),
                order=field_count
            )
            field_count += 1
        
        # Log the activity
        log_activity(
            user=created_by,
            activity_type='template_created',
            details=f'Created template for report type: {report_type} with {field_count} fields',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Template created successfully',
            'template_id': template.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_get_template(request, template_id):
    """
    API endpoint to get template details.
    """
    try:
        template = get_object_or_404(ReportTemplate, id=template_id)
        fields = template.fields.all().order_by('order')
        
        return JsonResponse({
            'success': True,
            'template': {
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'is_active': template.is_active,
                'created_at': template.created_at.isoformat(),
                'fields': [
                    {
                        'id': field.id,
                        'label': field.label,
                        'field_type': field.field_type,
                        'data_source': field.data_source,
                        'is_required': field.is_required,
                        'options': field.options,
                        'order': field.order
                    }
                    for field in fields
                ]
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def api_edit_template(request, template_id):
    """
    API endpoint to edit a template with activity logging.
    """
    try:
        template = get_object_or_404(ReportTemplate, id=template_id)
        data = json.loads(request.body)
        
        changes = []
        
        if 'report_type' in data and data['report_type'].strip() != template.name:
            if ReportTemplate.objects.filter(name=data['report_type'].strip()).exclude(id=template_id).exists():
                return JsonResponse({'success': False, 'error': 'A template for this report type already exists'}, status=400)
            changes.append(f'Report type changed from {template.name} to {data["report_type"]}')
            template.name = data['report_type'].strip()
        
        if 'description' in data and data['description'].strip() != template.description:
            changes.append('Description updated')
            template.description = data['description'].strip()
        
        if 'is_active' in data:
            new_status = data['is_active']
            old_status = 'active' if template.is_active else 'inactive'
            new_status_text = 'active' if new_status else 'inactive'
            if new_status != template.is_active:
                changes.append(f'Status changed from {old_status} to {new_status_text}')
            template.is_active = new_status
        
        # Update fields if provided
        if 'fields' in data:
            # Clear existing fields
            template.fields.all().delete()
            
            # Create new fields
            field_count = 0
            for field_data in data['fields']:
                TemplateField.objects.create(
                    template=template,
                    label=field_data.get('label', '').strip(),
                    field_type=field_data.get('field_type', 'text'),
                    data_source=field_data.get('data_source', 'manual'),
                    is_required=field_data.get('is_required', False),
                    options=field_data.get('options', ''),
                    order=field_count
                )
                field_count += 1
            changes.append(f'Fields updated ({field_count} fields)')
        
        template.save()
        
        # Log the activity
        if changes:
            log_activity(
                user=template.created_by,
                activity_type='template_updated',
                details=f'Template for {template.name} updated: ' + '; '.join(changes),
                request=request
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Template updated successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_delete_template(request, template_id):
    """
    API endpoint to delete a template with activity logging.
    """
    try:
        template = get_object_or_404(ReportTemplate, id=template_id)
        template_name = template.name
        
        # Log before deletion
        log_activity(
            user=template.created_by,
            activity_type='template_deleted',
            details=f'Template "{template_name}" was deleted',
            request=request
        )
        
        template.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Template deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_assign_template_to_report(request):
    """
    API endpoint to assign a template to a report.
    """
    try:
        data = json.loads(request.body)
        
        template_id = data.get('template_id')
        report_id = data.get('report_id')
        
        if not template_id or not report_id:
            return JsonResponse({'success': False, 'error': 'Template ID and Report ID are required'}, status=400)
        
        template = get_object_or_404(ReportTemplate, id=template_id)
        report = get_object_or_404(Report, id=report_id)
        
        # Check if already assigned
        if TemplateAssignment.objects.filter(template=template, report=report).exists():
            return JsonResponse({'success': False, 'error': 'This template is already assigned to this report'}, status=400)
        
        # Get the current user
        assigned_by = UserProfile.objects.first()
        if not assigned_by:
            return JsonResponse({'success': False, 'error': 'No user found'}, status=400)
        
        # Create assignment
        assignment = TemplateAssignment.objects.create(
            template=template,
            report=report,
            assigned_by=assigned_by,
            is_active=True
        )
        
        # Log the activity
        log_activity(
            user=assigned_by,
            activity_type='report_assigned',
            details=f'Assigned template "{template.name}" to report "{report.report_type}"',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Template assigned to report successfully',
            'assignment_id': assignment.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==================== API - CHECKLIST ENDPOINTS ====================

@csrf_exempt
@require_http_methods(["POST"])
def api_create_checklist(request):
    """
    API endpoint to create a new checklist with tasks.
    """
    try:
        data = json.loads(request.body)
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        frequency = data.get('frequency', 'weekly')
        assignment_target = data.get('assignment_target', 'all')
        assigned_users = data.get('assigned_users', [])
        tasks = data.get('tasks', [])
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Activity name is required'}, status=400)
        
        if not tasks:
            return JsonResponse({'success': False, 'error': 'Please add at least one task'}, status=400)
        
        # Get the current user
        created_by = UserProfile.objects.first()
        if not created_by:
            return JsonResponse({'success': False, 'error': 'No user found'}, status=400)
        
        # Create the checklist
        checklist = Checklist.objects.create(
            name=name,
            description=description,
            frequency=frequency,
            assignment_target=assignment_target,
            created_by=created_by,
            is_active=True
        )
        
        # Add assigned users if specific
        if assignment_target == 'specific' and assigned_users:
            for user_id in assigned_users:
                try:
                    user = UserProfile.objects.get(id=user_id)
                    checklist.assigned_users.add(user)
                except UserProfile.DoesNotExist:
                    pass
        
        # Create tasks
        task_count = 0
        for task_data in tasks:
            task_desc = task_data.get('description', '').strip()
            if task_desc:
                ChecklistTask.objects.create(
                    checklist=checklist,
                    description=task_desc,
                    order=task_count
                )
                task_count += 1
        
        # Log the activity
        log_activity(
            user=created_by,
            activity_type='checklist_created',
            details=f'Created checklist: {name} with {task_count} tasks',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Checklist created successfully',
            'checklist_id': checklist.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_get_checklist(request, checklist_id):
    """
    API endpoint to get checklist details.
    """
    try:
        checklist = get_object_or_404(Checklist, id=checklist_id)
        tasks = checklist.tasks.all().order_by('order')
        
        return JsonResponse({
            'success': True,
            'checklist': {
                'id': checklist.id,
                'name': checklist.name,
                'description': checklist.description,
                'frequency': checklist.frequency,
                'assignment_target': checklist.assignment_target,
                'is_active': checklist.is_active,
                'assigned_users': list(checklist.assigned_users.values_list('id', flat=True)),
                'tasks': [
                    {
                        'id': task.id,
                        'description': task.description,
                        'order': task.order,
                        'is_completed': task.is_completed
                    }
                    for task in tasks
                ]
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def api_edit_checklist(request, checklist_id):
    """
    API endpoint to edit a checklist with activity logging.
    """
    try:
        checklist = get_object_or_404(Checklist, id=checklist_id)
        data = json.loads(request.body)
        
        changes = []
        
        if 'name' in data and data['name'].strip() != checklist.name:
            changes.append(f'Name changed from {checklist.name} to {data["name"]}')
            checklist.name = data['name'].strip()
        
        if 'description' in data and data['description'].strip() != checklist.description:
            changes.append('Description updated')
            checklist.description = data['description'].strip()
        
        if 'frequency' in data and data['frequency'] != checklist.frequency:
            old_freq = checklist.get_frequency_display()
            checklist.frequency = data['frequency']
            changes.append(f'Frequency changed from {old_freq} to {checklist.get_frequency_display()}')
        
        if 'assignment_target' in data and data['assignment_target'] != checklist.assignment_target:
            old_assign = checklist.get_assignment_display()
            checklist.assignment_target = data['assignment_target']
            changes.append(f'Assignment changed from {old_assign} to {checklist.get_assignment_display()}')
        
        if 'is_active' in data:
            new_status = data['is_active']
            old_status = 'active' if checklist.is_active else 'inactive'
            new_status_text = 'active' if new_status else 'inactive'
            if new_status != checklist.is_active:
                changes.append(f'Status changed from {old_status} to {new_status_text}')
            checklist.is_active = new_status
        
        # Update assigned users
        if 'assigned_users' in data:
            checklist.assigned_users.clear()
            for user_id in data['assigned_users']:
                try:
                    user = UserProfile.objects.get(id=user_id)
                    checklist.assigned_users.add(user)
                except UserProfile.DoesNotExist:
                    pass
            changes.append('Assigned users updated')
        
        # Update tasks if provided
        if 'tasks' in data:
            # Clear existing tasks
            checklist.tasks.all().delete()
            
            # Create new tasks
            task_count = 0
            for task_data in data['tasks']:
                task_desc = task_data.get('description', '').strip()
                if task_desc:
                    ChecklistTask.objects.create(
                        checklist=checklist,
                        description=task_desc,
                        order=task_count
                    )
                    task_count += 1
            changes.append(f'Tasks updated ({task_count} tasks)')
        
        checklist.save()
        
        # Log the activity
        if changes:
            log_activity(
                user=checklist.created_by,
                activity_type='checklist_updated',
                details=f'Checklist {checklist.name} updated: ' + '; '.join(changes),
                request=request
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Checklist updated successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_delete_checklist(request, checklist_id):
    """
    API endpoint to delete a checklist with activity logging.
    """
    try:
        checklist = get_object_or_404(Checklist, id=checklist_id)
        checklist_name = checklist.name
        
        # Log before deletion
        log_activity(
            user=checklist.created_by,
            activity_type='checklist_deleted',
            details=f'Checklist "{checklist_name}" was deleted',
            request=request
        )
        
        checklist.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Checklist deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_update_task_status(request, task_id):
    """
    API endpoint to toggle task completion status with logging.
    """
    try:
        task = get_object_or_404(ChecklistTask, id=task_id)
        data = json.loads(request.body)
        is_completed = data.get('is_completed', False)
        
        old_status = 'Completed' if task.is_completed else 'Incomplete'
        new_status = 'Completed' if is_completed else 'Incomplete'
        
        task.is_completed = is_completed
        task.save()
        
        # Log the activity
        log_activity(
            user=task.checklist.created_by,
            activity_type='task_status_changed',
            details=f'Task "{task.description}" in checklist "{task.checklist.name}" status changed from {old_status} to {new_status}',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Task status updated successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_log_checklist(request):
    """
    API endpoint to log or unlog a checklist completion.
    """
    try:
        data = json.loads(request.body)
        checklist_id = data.get('checklist_id')
        log_date = data.get('log_date')
        action = data.get('action', 'log')  # 'log' or 'unlog'
        
        if not checklist_id or not log_date:
            return JsonResponse({'success': False, 'error': 'Checklist ID and log date are required'}, status=400)
        
        checklist = get_object_or_404(Checklist, id=checklist_id)
        
        # Get the current user
        try:
            user = UserProfile.objects.get(email=request.user.email)
        except (UserProfile.DoesNotExist, AttributeError):
            user = UserProfile.objects.first()
        
        if not user:
            return JsonResponse({'success': False, 'error': 'No user found'}, status=400)
        
        if action == 'unlog':
            # Find and delete the log entry
            # Use both conditions in the same filter
            activity_log = ActivityLog.objects.filter(
                user=user,
                activity_type='checklist_updated'
            ).filter(
                details__icontains=checklist.name
            ).filter(
                details__icontains=log_date
            ).first()
            
            if activity_log:
                activity_log.delete()
                return JsonResponse({
                    'success': True,
                    'message': f'Checklist "{checklist.name}" unlogged for {log_date}'
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': 'No log entry found to remove'
                })
        else:
            # Log the activity
            log_activity(
                user=user,
                activity_type='checklist_updated',
                details=f'Completed checklist "{checklist.name}" on {log_date}',
                request=request
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Checklist "{checklist.name}" logged for {log_date}'
            })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def drafts_page(request):
    """
    Drafts page view - shows templates and drafts.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except (UserProfile.DoesNotExist, AttributeError):
        user_profile = UserProfile.objects.first()
    
    # Get all report types from templates
    templates = ReportTemplate.objects.filter(is_active=True).order_by('name')
    report_types = templates.values_list('name', flat=True).distinct()
    
    # Get user's drafts
    drafts = Draft.objects.filter(created_by=user_profile).order_by('-created_at')
    
    # Get supervisors for assignment
    supervisors = UserProfile.objects.filter(Q(role='admin') | Q(role='supervisor'))
    
    context = {
        'user_profile': user_profile,
        'templates': templates,
        'report_types': list(report_types),
        'drafts': drafts,
        'supervisors': supervisors,
        'today': timezone.now(),
        'statuses': Draft.STATUS_CHOICES,
    }
    
    return render(request, 'control_dashboard/draft.html', context)


@csrf_exempt
@require_http_methods(["GET"])
def api_get_template_fields(request):
    """
    API endpoint to get template fields by report type.
    """
    try:
        report_type = request.GET.get('report_type')
        if not report_type:
            return JsonResponse({'success': False, 'error': 'Report type is required'}, status=400)
        
        template = get_object_or_404(ReportTemplate, name=report_type, is_active=True)
        fields = template.fields.all().order_by('order')
        
        return JsonResponse({
            'success': True,
            'template': {
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'fields': [
                    {
                        'id': field.id,
                        'label': field.label,
                        'field_type': field.field_type,
                        'data_source': field.data_source,
                        'is_required': field.is_required,
                        'options': field.get_options_list() if hasattr(field, 'get_options_list') else [],
                        'order': field.order
                    }
                    for field in fields
                ]
            }
        })
        
    except ReportTemplate.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Template not found for this report type'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_save_draft(request):
    """
    API endpoint to save a draft report.
    """
    try:
        data = json.loads(request.body)
        report_type = data.get('report_type', '').strip()
        form_data = data.get('form_data', {})
        submit = data.get('submit', False)
        
        if not report_type:
            return JsonResponse({'success': False, 'error': 'Report type is required'}, status=400)
        
        # Get the current user
        try:
            user = UserProfile.objects.get(email=request.user.email)
        except (UserProfile.DoesNotExist, AttributeError):
            user = UserProfile.objects.first()
        
        if not user:
            return JsonResponse({'success': False, 'error': 'No user found'}, status=400)
        
        # Get template
        template = ReportTemplate.objects.filter(name=report_type).first()
        
        # Determine status
        if submit:
            status = 'submitted'
        else:
            status = 'draft'
        
        # Create or update draft
        draft, created = Draft.objects.update_or_create(
            report_type=report_type,
            created_by=user,
            status='draft',
            defaults={
                'template': template,
                'data': form_data,
                'status': status,
            }
        )
        
        # If submitting, set submitted_at
        if submit:
            draft.submitted_at = timezone.now()
            draft.save()
        
        # Log the activity
        action_text = 'submitted' if submit else 'saved'
        log_activity(
            user=user,
            activity_type='edit' if not submit else 'report_created',
            details=f'{action_text.capitalize()} draft for report type: {report_type}',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Draft {action_text} successfully',
            'draft_id': draft.id,
            'status': draft.status
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_submit_draft(request):
    """
    API endpoint to submit a draft for review.
    """
    try:
        data = json.loads(request.body)
        draft_id = data.get('draft_id')
        
        if not draft_id:
            return JsonResponse({'success': False, 'error': 'Draft ID is required'}, status=400)
        
        draft = get_object_or_404(Draft, id=draft_id)
        
        # Get the current user
        try:
            user = UserProfile.objects.get(email=request.user.email)
        except (UserProfile.DoesNotExist, AttributeError):
            user = UserProfile.objects.first()
        
        if not user:
            return JsonResponse({'success': False, 'error': 'No user found'}, status=400)
        
        # Check if user owns this draft
        if draft.created_by != user:
            return JsonResponse({'success': False, 'error': 'You do not have permission to submit this draft'}, status=403)
        
        # Update draft status
        draft.status = 'submitted'
        draft.submitted_at = timezone.now()
        draft.save()
        
        # Log the activity
        log_activity(
            user=user,
            activity_type='report_created',
            details=f'Submitted report: {draft.report_type} for review',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Draft submitted successfully',
            'status': draft.status
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def api_get_draft(request, draft_id):
    """
    API endpoint to get draft details.
    """
    try:
        draft = get_object_or_404(Draft, id=draft_id)
        
        return JsonResponse({
            'success': True,
            'draft': {
                'id': draft.id,
                'report_type': draft.report_type,
                'data': draft.data,
                'status': draft.status,
                'status_display': draft.get_status_display(),
                'created_at': draft.created_at.isoformat(),
                'updated_at': draft.updated_at.isoformat(),
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
def api_delete_draft(request, draft_id):
    """
    API endpoint to delete a draft.
    """
    try:
        draft = get_object_or_404(Draft, id=draft_id)
        
        # Get the current user
        try:
            user = UserProfile.objects.get(email=request.user.email)
        except (UserProfile.DoesNotExist, AttributeError):
            user = UserProfile.objects.first()
        
        # Check if user owns this draft
        if draft.created_by != user:
            return JsonResponse({'success': False, 'error': 'You do not have permission to delete this draft'}, status=403)
        
        # Log the activity
        log_activity(
            user=user,
            activity_type='edit',
            details=f'Deleted draft: {draft.report_type}',
            request=request
        )
        
        draft.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Draft deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def reports_page(request):
    """
    Reports page view - shows all reports with filtering.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except (UserProfile.DoesNotExist, AttributeError):
        user_profile = UserProfile.objects.first()
    
    # Get all reports created by this user
    reports = Draft.objects.filter(created_by=user_profile).order_by('-created_at')
    
    # Get all report types for filter
    report_types = reports.values_list('report_type', flat=True).distinct()
    
    context = {
        'user_profile': user_profile,
        'reports': reports,
        'report_types': list(report_types),
        'today': timezone.now(),
    }
    
    return render(request, 'control_dashboard/reports.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def api_submit_report(request):
    """
    API endpoint to submit a report for review.
    """
    try:
        data = json.loads(request.body)
        report_id = data.get('report_id')
        
        if not report_id:
            return JsonResponse({'success': False, 'error': 'Report ID is required'}, status=400)
        
        report = get_object_or_404(Draft, id=report_id)
        
        try:
            user = UserProfile.objects.get(email=request.user.email)
        except (UserProfile.DoesNotExist, AttributeError):
            user = UserProfile.objects.first()
        
        if report.created_by != user:
            return JsonResponse({'success': False, 'error': 'You do not have permission to submit this report'}, status=403)
        
        report.status = 'submitted'
        report.submitted_at = timezone.now()
        report.save()
        
        log_activity(
            user=user,
            activity_type='report_created',
            details=f'Submitted report: {report.report_type} for review',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Report submitted successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def submit_page(request):
    """
    Submit page view - shows available exceptions for email submission.
    """
    # Get the first user profile (bypass authentication)
    user_profile = UserProfile.objects.first()
    
    # If no user exists, create a default one or show error
    if not user_profile:
        # Create a default user for testing
        user_profile = UserProfile.objects.create(
            email='test@bank.com',
            full_name='Test User',
            position='hoc',
            role='member',
            status='active'
        )
    
    # Get available exceptions (draft or rejected reports)
    exceptions = Draft.objects.filter(
        created_by=user_profile,
        status__in=['draft', 'rejected']
    ).order_by('-created_at')
    
    # Get all report types for filter
    report_types = Draft.objects.filter(
        created_by=user_profile
    ).values_list('report_type', flat=True).distinct()
    
    # Get unique categories from exceptions
    categories = []
    category_names = set()
    for exception in exceptions:
        category_name = exception.data.get('unit', '') or exception.data.get('branch', '') or 'Uncategorized'
        if category_name not in category_names:
            category_names.add(category_name)
            categories.append({
                'id': category_name.lower().replace(' ', '-'),
                'name': category_name
            })
    
    # Get email recipients
    email_recipients = [
        {'email': 'hoc@bank.com', 'name': 'Head of Control', 'department': 'Control'},
        {'email': 'cc@bank.com', 'name': 'Control Committee', 'department': 'Control'},
        {'email': 'operations@bank.com', 'name': 'Operations Team', 'department': 'Operations'},
        {'email': 'risk@bank.com', 'name': 'Risk Management', 'department': 'Risk'},
    ]
    
    # Convert exceptions to JSON for frontend
    exceptions_json = []
    for exception in exceptions:
        status_display = dict(Draft.STATUS_CHOICES).get(exception.status, exception.status)
        category = exception.data.get('unit', '') or exception.data.get('branch', '') or 'Uncategorized'
        category_id = category.lower().replace(' ', '-')
        
        exceptions_json.append({
            'id': exception.id,
            'report_type': exception.report_type,
            'status': exception.status,
            'status_display': status_display,
            'data': exception.data,
            'created_at': exception.created_at.strftime('%b %d, %Y'),
            'category': category_id,
            'unit': exception.data.get('unit', '') or exception.data.get('branch', '') or 'N/A',
        })
    
    # Add user data to template
    user_data = {
        'name': user_profile.full_name if user_profile else 'Test User',
        'email': user_profile.email if user_profile else 'test@bank.com',
        'department': user_profile.get_position_display() if user_profile else 'Member',
    }
    
    context = {
        'user_profile': user_profile,
        'exceptions_json': json.dumps(exceptions_json, default=str),
        'exceptions': exceptions,
        'report_types': list(report_types),
        'categories': categories,
        'email_recipients': email_recipients,
        'user_data': user_data,
    }
    
    return render(request, 'control_dashboard/submit.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def api_send_email(request):
    """
    API endpoint to send email with selected exceptions.
    """
    try:
        data = json.loads(request.body)
        
        to = data.get('to')
        cc = data.get('cc')
        subject = data.get('subject')
        body = data.get('body')
        exceptions = data.get('exceptions', [])
        from_email = data.get('from')
        from_name = data.get('from_name', '')
        
        # Validate required fields
        if not to:
            return JsonResponse({'success': False, 'error': 'Recipient is required'}, status=400)
        
        if not subject:
            return JsonResponse({'success': False, 'error': 'Subject is required'}, status=400)
        
        if not body:
            return JsonResponse({'success': False, 'error': 'Email body is required'}, status=400)
        
        if not exceptions:
            return JsonResponse({'success': False, 'error': 'No exceptions selected'}, status=400)
        
        # Get the first user (bypass authentication)
        user = UserProfile.objects.first()
        
        if not user:
            # Create a default user if none exists
            user = UserProfile.objects.create(
                email='test@bank.com',
                full_name='Test User',
                position='hoc',
                role='member',
                status='active'
            )
        
        # Log the email sending activity
        log_activity(
            user=user,
            activity_type='report_created',
            details=f'Sent email to {to} with {len(exceptions)} exceptions. Subject: {subject}',
            request=request
        )
        
        # Update the status of submitted exceptions
        for exception in exceptions:
            try:
                draft = Draft.objects.get(id=exception.get('id'))
                if draft.status in ['draft', 'rejected']:
                    draft.status = 'submitted'
                    draft.submitted_at = timezone.now()
                    draft.save()
            except Draft.DoesNotExist:
                pass
        
        # Return success response
        return JsonResponse({
            'success': True,
            'message': f'Email sent successfully to {to} with {len(exceptions)} exceptions',
            'clear_selection': True,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def member_activity_logs(request):
    """
    Member Activity Logs view - shows user's own activities only.
    """
    # Get the current user's profile
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except (UserProfile.DoesNotExist, AttributeError):
        user_profile = UserProfile.objects.first()
    
    # Get filter parameters
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    activity_filter = request.GET.get('activity', '')
    
    # Start with user's own logs
    logs = ActivityLog.objects.filter(user=user_profile)
    
    # Apply filters
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            logs = logs.filter(created_at__date__gte=start)
        except:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            logs = logs.filter(created_at__date__lte=end)
        except:
            pass
    
    if activity_filter and activity_filter != 'all':
        logs = logs.filter(activity_type=activity_filter)
    
    context = {
        'user_profile': user_profile,
        'activity_logs': logs,
        'activity_types': ActivityLog.ACTIVITY_CHOICES,
        'start_date': start_date,
        'end_date': end_date,
        'activity_filter': activity_filter,
    }
    
    return render(request, 'control_dashboard/activity-mem.html', context)

# ==================== SUPERVISOR DASHBOARD ====================

def supervisor_dashboard(request):
    """
    Supervisor Dashboard view with real-time metrics.
    """
    # Get the current user's profile
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except (UserProfile.DoesNotExist, AttributeError):
        user_profile = UserProfile.objects.first()
    
    # Calculate week range (Monday to Sunday)
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    # 1. LOGGED EXCEPTIONS - Total count of exceptions captured during the week
    weekly_exceptions = Draft.objects.filter(
        created_at__date__gte=week_start,
        created_at__date__lte=week_end,
        status__in=['draft', 'rejected', 'submitted', 'in_review', 'approved']
    )
    total_exceptions = weekly_exceptions.count()
    
    # Get today's exceptions
    today_exceptions = weekly_exceptions.filter(created_at__date=today).count()
    
    # 2. PENDING REVIEWS - Count of reviews outstanding or due for the week
    pending_reviews = Draft.objects.filter(
        status__in=['submitted', 'in_review']
    ).count()
    
    # 3. TEAM COMPLETION RATE - Percentage completion of all tasks and reports submitted
    team_drafts = Draft.objects.filter(
        created_by__role__in=['member', 'supervisor']
    )
    
    total_drafts = team_drafts.count()
    completed_drafts = team_drafts.filter(
        status__in=['approved', 'rejected']
    ).count()
    
    if total_drafts > 0:
        completion_rate = round((completed_drafts / total_drafts) * 100)
    else:
        completion_rate = 0
    
    # 4. OUTSTANDING EXCEPTIONS - Exceptions that are open or past resolution date
    overage_threshold = today - timedelta(days=7)
    outstanding_exceptions = Draft.objects.filter(
        status__in=['draft', 'submitted', 'in_review', 'rejected'],
        created_at__date__lte=overage_threshold
    ).order_by('created_at')[:10]
    
    # Get team performance data - FIXED: Use Count directly
    team_members = UserProfile.objects.filter(
        role__in=['member', 'supervisor']
    ).annotate(
        total_drafts=Count('drafts'),
        submitted_drafts=Count('drafts', filter=Q(drafts__status='submitted')),
        approved_drafts=Count('drafts', filter=Q(drafts__status='approved')),
        rejected_drafts=Count('drafts', filter=Q(drafts__status='rejected')),
        in_review_drafts=Count('drafts', filter=Q(drafts__status='in_review')),
    )
    
    # Calculate completion rates
    team_performance = []
    for member in team_members:
        total = member.total_drafts
        if total > 0:
            completed = member.approved_drafts + member.rejected_drafts
            percentage = round((completed / total) * 100)
        else:
            percentage = 0
        
        team_performance.append({
            'user': member,
            'total': total,
            'submitted': member.submitted_drafts,
            'approved': member.approved_drafts,
            'rejected': member.rejected_drafts,
            'in_review': member.in_review_drafts,
            'percentage': percentage,
            'status': 'success' if percentage >= 90 else 'warning' if percentage >= 70 else 'danger'
        })
    
    # Sort by percentage descending
    team_performance.sort(key=lambda x: x['percentage'], reverse=True)
    
    # Get recent exceptions (last 10)
    recent_exceptions = Draft.objects.filter(
        status__in=['draft', 'rejected', 'submitted', 'in_review']
    ).order_by('-created_at')[:10]
    
    context = {
        'user_profile': user_profile,
        'total_exceptions': total_exceptions,
        'pending_reviews': pending_reviews,
        'in_review': Draft.objects.filter(status='in_review').count(),
        'today_exceptions': today_exceptions,
        'recent_exceptions': recent_exceptions,
        'team_performance': team_performance,
        'completion_rate': completion_rate,
        'outstanding_exceptions': outstanding_exceptions,
        'week_start': week_start,
        'week_end': week_end,
        'today': today,
    }
    
    return render(request, 'control_dashboard/supervisorboard.html', context)


def supervisor_exceptions(request):
    """
    Supervisor view for logged exceptions with filtering and review capabilities.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except (UserProfile.DoesNotExist, AttributeError):
        user_profile = UserProfile.objects.first()
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    search_query = request.GET.get('search', '')
    
    # Start with all exceptions
    exceptions = Draft.objects.filter(
        status__in=['draft', 'rejected', 'submitted', 'in_review', 'approved']
    )
    
    # Apply filters
    if status_filter and status_filter != 'all':
        exceptions = exceptions.filter(status=status_filter)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            exceptions = exceptions.filter(created_at__date=filter_date)
        except:
            pass
    
    if search_query:
        exceptions = exceptions.filter(
            Q(report_type__icontains=search_query) |
            Q(data__header__icontains=search_query) |
            Q(data__details__icontains=search_query) |
            Q(created_by__full_name__icontains=search_query)
        )
    
    # Get status counts for filter badges
    status_counts = {
        'draft': Draft.objects.filter(status='draft').count(),
        'submitted': Draft.objects.filter(status='submitted').count(),
        'in_review': Draft.objects.filter(status='in_review').count(),
        'approved': Draft.objects.filter(status='approved').count(),
        'rejected': Draft.objects.filter(status='rejected').count(),
    }
    
    context = {
        'user_profile': user_profile,
        'exceptions': exceptions,
        'status_counts': status_counts,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'search_query': search_query,
        'statuses': Draft.STATUS_CHOICES,
    }
    
    return render(request, 'control_dashboard/supervisor_exceptions.html', context)

# ==================== TEAM PERFORMANCE ====================

def team_performance(request):
    """
    Team Performance view - shows all team members and their performance metrics.
    """
    # Get the current user's profile
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except (UserProfile.DoesNotExist, AttributeError):
        user_profile = UserProfile.objects.first()
    
    # Get filter parameters
    search_query = request.GET.get('search', '')
    
    # Get all team members (users with role 'member' or 'supervisor')
    team_members = UserProfile.objects.filter(
        role__in=['member', 'supervisor']
    )
    
    # Apply search filter
    if search_query:
        team_members = team_members.filter(
            Q(full_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Annotate with performance metrics
    team_members = team_members.annotate(
        total_drafts=Count('drafts'),
        submitted_drafts=Count('drafts', filter=Q(drafts__status='submitted')),
        approved_drafts=Count('drafts', filter=Q(drafts__status='approved')),
        rejected_drafts=Count('drafts', filter=Q(drafts__status='rejected')),
        in_review_drafts=Count('drafts', filter=Q(drafts__status='in_review')),
        # Count drafts that are completed (approved or rejected)
        completed_drafts=Count('drafts', filter=Q(drafts__status__in=['approved', 'rejected'])),
    )
    
    # Calculate performance scores
    team_data = []
    for member in team_members:
        total = member.total_drafts
        completed = member.completed_drafts
        
        # Calculate percentage
        if total > 0:
            percentage = round((completed / total) * 100)
        else:
            percentage = 0
        
        # Determine status color
        if percentage >= 90:
            status = 'success'
            status_text = 'Excellent'
        elif percentage >= 70:
            status = 'warning'
            status_text = 'Good'
        elif percentage >= 50:
            status = 'info'
            status_text = 'Average'
        else:
            status = 'danger'
            status_text = 'Needs Improvement'
        
        team_data.append({
            'user': member,
            'total_tasks': total,
            'submitted': member.submitted_drafts,
            'approved': member.approved_drafts,
            'rejected': member.rejected_drafts,
            'in_review': member.in_review_drafts,
            'completed': completed,
            'percentage': percentage,
            'status': status,
            'status_text': status_text,
        })
    
    # Sort by percentage descending
    team_data.sort(key=lambda x: x['percentage'], reverse=True)
    
    # Calculate team statistics
    total_tasks = sum(m['total_tasks'] for m in team_data)
    total_completed = sum(m['completed'] for m in team_data)
    if total_tasks > 0:
        overall_completion = round((total_completed / total_tasks) * 100)
    else:
        overall_completion = 0
    
    context = {
        'user_profile': user_profile,
        'team_data': team_data,
        'total_members': len(team_data),
        'total_tasks': total_tasks,
        'total_completed': total_completed,
        'overall_completion': overall_completion,
        'search_query': search_query,
    }
    
    return render(request, 'control_dashboard/team.html', context)


@csrf_exempt
@require_http_methods(["GET"])
def api_team_member_detail(request, user_id):
    """
    API endpoint to get detailed performance data for a team member.
    """
    try:
        member = get_object_or_404(UserProfile, id=user_id)
        
        # Get all drafts for this user
        drafts = Draft.objects.filter(created_by=member)
        
        # Get status breakdown
        status_breakdown = {
            'draft': drafts.filter(status='draft').count(),
            'submitted': drafts.filter(status='submitted').count(),
            'in_review': drafts.filter(status='in_review').count(),
            'approved': drafts.filter(status='approved').count(),
            'rejected': drafts.filter(status='rejected').count(),
            'revision_requested': drafts.filter(status='revision_requested').count(),
        }
        
        # Get recent submissions
        recent_submissions = drafts.order_by('-created_at')[:5]
        
        # Calculate completion rate
        total = drafts.count()
        completed = drafts.filter(status__in=['approved', 'rejected']).count()
        percentage = round((completed / total) * 100) if total > 0 else 0
        
        return JsonResponse({
            'success': True,
            'member': {
                'id': member.id,
                'full_name': member.full_name,
                'email': member.email,
                'position': member.get_position_display(),
                'role': member.get_role_display(),
                'total_tasks': total,
                'completed': completed,
                'percentage': percentage,
                'status_breakdown': status_breakdown,
                'recent_submissions': [
                    {
                        'id': draft.id,
                        'report_type': draft.report_type,
                        'status': draft.status,
                        'status_display': draft.get_status_display(),
                        'created_at': draft.created_at.strftime('%b %d, %Y'),
                        'data': draft.data,
                    }
                    for draft in recent_submissions
                ]
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ==================== SUBMITTED REPORTS ====================

def submitted_reports(request):
    """
    Submitted Reports view - shows all submitted reports with scoring.
    """
    # Get the current user's profile
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except (UserProfile.DoesNotExist, AttributeError):
        user_profile = UserProfile.objects.first()
    
    # Get filter parameters
    user_filter = request.GET.get('user', '')
    category_filter = request.GET.get('category', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Start with all submitted drafts
    reports = Draft.objects.filter(
        status__in=['submitted', 'in_review', 'approved', 'rejected', 'revision_requested']
    )
    
    # Apply filters
    if user_filter and user_filter != 'all':
        reports = reports.filter(created_by__id=user_filter)
    
    if category_filter and category_filter != 'all':
        reports = reports.filter(report_type__icontains=category_filter)
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            reports = reports.filter(created_at__date__gte=start)
        except:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            reports = reports.filter(created_at__date__lte=end)
        except:
            pass
    
    # Get all users for filter dropdown
    users = UserProfile.objects.filter(
        role__in=['member', 'supervisor']
    )
    
    # Get unique categories from reports
    categories = reports.values_list('report_type', flat=True).distinct()
    
    # Calculate scores for each report
    report_data = []
    for report in reports:
        # Calculate base score (percentage of tasks completed)
        # For now, we'll use a simple calculation based on status
        status_scores = {
            'submitted': 70,
            'in_review': 80,
            'approved': 100,
            'rejected': 50,
            'revision_requested': 60,
        }
        base_score = status_scores.get(report.status, 50)
        
        # Get manual deduction from report data or default to 0
        manual_deduction = report.data.get('manual_deduction', 0) if report.data else 0
        
        # Calculate final score
        final_score = max(0, base_score - manual_deduction)
        
        # Determine score badge class
        if final_score >= 90:
            badge_class = 'badge-success'
        elif final_score >= 70:
            badge_class = 'badge-warning'
        elif final_score >= 50:
            badge_class = 'badge-info'
        else:
            badge_class = 'badge-danger'
        
        report_data.append({
            'report': report,
            'created_by': report.created_by,
            'report_type': report.report_type,
            'created_at': report.created_at,
            'submitted_at': report.submitted_at or report.created_at,
            'status': report.status,
            'status_display': report.get_status_display(),
            'base_score': base_score,
            'manual_deduction': manual_deduction,
            'final_score': final_score,
            'badge_class': badge_class,
        })
    
    context = {
        'user_profile': user_profile,
        'report_data': report_data,
        'users': users,
        'categories': categories,
        'user_filter': user_filter,
        'category_filter': category_filter,
        'start_date': start_date,
        'end_date': end_date,
        'total_reports': len(report_data),
    }
    
    return render(request, 'control_dashboard/submitted.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def api_update_report_score(request):
    """
    API endpoint to update report score with manual deduction.
    """
    try:
        data = json.loads(request.body)
        report_id = data.get('report_id')
        manual_deduction = data.get('manual_deduction', 0)
        
        if not report_id:
            return JsonResponse({'success': False, 'error': 'Report ID is required'}, status=400)
        
        report = get_object_or_404(Draft, id=report_id)
        
        # Ensure manual_deduction is a valid number
        try:
            manual_deduction = int(manual_deduction)
            if manual_deduction < 0:
                manual_deduction = 0
            if manual_deduction > 100:
                manual_deduction = 100
        except ValueError:
            manual_deduction = 0
        
        # Update the report data
        if not report.data:
            report.data = {}
        report.data['manual_deduction'] = manual_deduction
        report.save()
        
        # Log the activity
        log_activity(
            user=report.created_by,
            activity_type='report_updated',
            details=f'Updated manual deduction for report {report.report_type} to {manual_deduction}%',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Score updated successfully',
            'manual_deduction': manual_deduction,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ==================== AD-HOC SCORECARD ====================

def ad_hoc_scorecard(request):
    """
    Ad-Hoc Scorecard view - manage manual deductions for users.
    """
    # Get the current user's profile
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except (UserProfile.DoesNotExist, AttributeError):
        user_profile = UserProfile.objects.first()
    
    # Get filter parameter
    user_filter = request.GET.get('user', '')
    
    # Get all ad-hoc deductions
    # We'll store deductions in a separate model or in the user's data
    # For now, we'll use the ActivityLog to track deductions
    deductions = ActivityLog.objects.filter(
        activity_type='ad_hoc_deduction'
    )
    
    if user_filter and user_filter != 'all':
        deductions = deductions.filter(user_id=user_filter)
    
    # Get all users for filter dropdown
    users = UserProfile.objects.filter(
        role__in=['member', 'supervisor']
    )
    
    # Build deduction data
    deduction_data = []
    for deduction in deductions:
        # Parse details from the log
        details = deduction.details
        # Expecting format: "Deduction: {points} - {reason} for {task_description}"
        parts = details.split(' - ')
        if len(parts) >= 2:
            points_part = parts[0].replace('Deduction: ', '')
            reason_part = parts[1] if len(parts) > 1 else ''
            task_desc = parts[2] if len(parts) > 2 else ''
        else:
            points_part = '0'
            reason_part = details
            task_desc = ''
        
        try:
            points = int(points_part)
        except:
            points = 0
        
        deduction_data.append({
            'id': deduction.id,
            'user': deduction.user,
            'points': points,
            'reason': reason_part,
            'task_description': task_desc,
            'created_at': deduction.created_at,
            'user_name': deduction.user.full_name or deduction.user.email,
        })
    
    context = {
        'user_profile': user_profile,
        'deductions': deduction_data,
        'users': users,
        'user_filter': user_filter,
        'total_deductions': len(deduction_data),
    }
    
    return render(request, 'control_dashboard/ad-hoc.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def api_create_ad_hoc_deduction(request):
    """
    API endpoint to create a new ad-hoc deduction.
    """
    try:
        data = json.loads(request.body)
        
        user_id = data.get('user_id')
        points = data.get('points', 0)
        reason = data.get('reason', '')
        task_description = data.get('task_description', '')
        
        if not user_id:
            return JsonResponse({'success': False, 'error': 'User is required'}, status=400)
        
        if not points:
            return JsonResponse({'success': False, 'error': 'Deduction points are required'}, status=400)
        
        try:
            points = int(points)
            if points < 0:
                points = 0
            if points > 100:
                points = 100
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid points value'}, status=400)
        
        user = get_object_or_404(UserProfile, id=user_id)
        
        # Log the deduction as an activity
        details = f"Deduction: {points} - {reason} - {task_description}"
        log_activity(
            user=user,
            activity_type='ad_hoc_deduction',
            details=details,
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Deduction added successfully',
            'deduction_id': user.id,
            'points': points,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_update_ad_hoc_deduction(request, deduction_id):
    """
    API endpoint to update an existing ad-hoc deduction.
    """
    try:
        data = json.loads(request.body)
        
        deduction = get_object_or_404(ActivityLog, id=deduction_id)
        
        if deduction.activity_type != 'ad_hoc_deduction':
            return JsonResponse({'success': False, 'error': 'Invalid deduction record'}, status=400)
        
        points = data.get('points')
        reason = data.get('reason', '')
        task_description = data.get('task_description', '')
        
        if points is not None:
            try:
                points = int(points)
                if points < 0:
                    points = 0
                if points > 100:
                    points = 100
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Invalid points value'}, status=400)
        
        # Update the details
        details = f"Deduction: {points} - {reason} - {task_description}"
        deduction.details = details
        deduction.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Deduction updated successfully',
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_delete_ad_hoc_deduction(request, deduction_id):
    """
    API endpoint to delete an ad-hoc deduction.
    """
    try:
        deduction = get_object_or_404(ActivityLog, id=deduction_id)
        
        if deduction.activity_type != 'ad_hoc_deduction':
            return JsonResponse({'success': False, 'error': 'Invalid deduction record'}, status=400)
        
        deduction.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Deduction deleted successfully',
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ==================== LOGGED EXCEPTIONS ====================

def logged_exceptions(request):
    """
    Logged Exceptions view - shows all exceptions with filtering and management.
    """
    # Get the current user's profile
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except (UserProfile.DoesNotExist, AttributeError):
        user_profile = UserProfile.objects.first()
    
    # Get filter parameters
    branch_filter = request.GET.get('branch', '')
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    search_query = request.GET.get('search', '')
    
    # Start with all exceptions (drafts and reports)
    exceptions = Draft.objects.all().order_by('-created_at')
    
    # Apply filters
    if branch_filter and branch_filter != 'all':
        exceptions = exceptions.filter(
            Q(data__branch__icontains=branch_filter) |
            Q(data__unit__icontains=branch_filter)
        )
    
    if category_filter and category_filter != 'all':
        exceptions = exceptions.filter(report_type__icontains=category_filter)
    
    if status_filter and status_filter != 'all':
        exceptions = exceptions.filter(status=status_filter)
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            exceptions = exceptions.filter(created_at__date__gte=start)
        except:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            exceptions = exceptions.filter(created_at__date__lte=end)
        except:
            pass
    
    if search_query:
        exceptions = exceptions.filter(
            Q(report_type__icontains=search_query) |
            Q(data__header__icontains=search_query) |
            Q(data__details__icontains=search_query) |
            Q(data__branch__icontains=search_query) |
            Q(created_by__full_name__icontains=search_query)
        )
    
    # Get unique branches/units from exceptions
    branches = set()
    for exception in exceptions:
        branch = exception.data.get('branch', '') or exception.data.get('unit', '')
        if branch:
            branches.add(branch)
    
    # Get unique categories
    categories = exceptions.values_list('report_type', flat=True).distinct()
    
    # Get status counts for filter badges
    status_counts = {
        'draft': Draft.objects.filter(status='draft').count(),
        'submitted': Draft.objects.filter(status='submitted').count(),
        'in_review': Draft.objects.filter(status='in_review').count(),
        'approved': Draft.objects.filter(status='approved').count(),
        'rejected': Draft.objects.filter(status='rejected').count(),
        'revision_requested': Draft.objects.filter(status='revision_requested').count(),
    }
    
    context = {
        'user_profile': user_profile,
        'exceptions': exceptions,
        'branches': sorted(list(branches)),
        'categories': categories,
        'status_counts': status_counts,
        'branch_filter': branch_filter,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'start_date': start_date,
        'end_date': end_date,
        'search_query': search_query,
        'total_exceptions': exceptions.count(),
    }
    
    return render(request, 'control_dashboard/logged.html', context)


@csrf_exempt
@require_http_methods(["GET"])
def api_get_exception_detail(request, exception_id):
    """
    API endpoint to get full exception details for viewing/editing.
    """
    try:
        exception = get_object_or_404(Draft, id=exception_id)
        
        # Get review history
        reviews = DraftReview.objects.filter(draft=exception).order_by('-created_at')
        
        return JsonResponse({
            'success': True,
            'exception': {
                'id': exception.id,
                'report_type': exception.report_type,
                'status': exception.status,
                'status_display': exception.get_status_display(),
                'data': exception.data,
                'created_by': {
                    'id': exception.created_by.id,
                    'name': exception.created_by.full_name or exception.created_by.email,
                    'email': exception.created_by.email,
                },
                'created_at': exception.created_at.strftime('%b %d, %Y %H:%M'),
                'updated_at': exception.updated_at.strftime('%b %d, %Y %H:%M'),
                'submitted_at': exception.submitted_at.strftime('%b %d, %Y %H:%M') if exception.submitted_at else None,
                'reviewed_at': exception.reviewed_at.strftime('%b %d, %Y %H:%M') if exception.reviewed_at else None,
                'review_comments': exception.review_comments,
                'reviewed_by': {
                    'id': exception.reviewed_by.id if exception.reviewed_by else None,
                    'name': exception.reviewed_by.full_name if exception.reviewed_by else None,
                } if exception.reviewed_by else None,
                'reviews': [
                    {
                        'action': review.get_action_display(),
                        'comments': review.comments,
                        'performed_by': review.performed_by.full_name or review.performed_by.email,
                        'created_at': review.created_at.strftime('%b %d, %Y %H:%M'),
                    }
                    for review in reviews
                ]
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_update_exception(request, exception_id):
    """
    API endpoint to update exception details.
    """
    try:
        data = json.loads(request.body)
        exception = get_object_or_404(Draft, id=exception_id)
        
        # Update fields
        if 'report_type' in data:
            exception.report_type = data['report_type']
        
        if 'data' in data:
            # Merge existing data with new data
            if not exception.data:
                exception.data = {}
            exception.data.update(data['data'])
        
        if 'status' in data:
            exception.status = data['status']
        
        if 'review_comments' in data:
            exception.review_comments = data['review_comments']
        
        exception.save()
        
        # Log the activity
        log_activity(
            user=exception.created_by,
            activity_type='report_updated',
            details=f'Updated exception: {exception.report_type}',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Exception updated successfully',
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==================== SUPERVISOR ACTIVITY CHECKLIST ====================

def supervisor_checklist(request):
    """
    Supervisor Activity Checklist view - shows all users and their checklist completion.
    """
    # Get the current user's profile
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except (UserProfile.DoesNotExist, AttributeError):
        user_profile = UserProfile.objects.first()
    
    # Get all users with role 'member' or 'supervisor'
    users = UserProfile.objects.filter(
        role__in=['member', 'supervisor']
    )
    
    # Get all checklists
    all_checklists = Checklist.objects.filter(is_active=True)
    
    # Build user completion data
    user_completion_data = []
    for user in users:
        # Get checklists assigned to this user
        assigned_checklists = all_checklists.filter(
            Q(assigned_users=user) | 
            Q(assignment_target='all')
        ).distinct()
        
        total_checklists = assigned_checklists.count()
        completed_checklists = 0
        checklist_details = []
        
        for checklist in assigned_checklists:
            # Check if user has completed this checklist
            is_completed = ActivityLog.objects.filter(
                user=user,
                activity_type='checklist_updated',
                details__icontains=checklist.name
            ).exists()
            
            if is_completed:
                completed_checklists += 1
            
            # Get tasks for this checklist
            tasks = checklist.tasks.all()
            completed_tasks = 0
            task_details = []
            
            for task in tasks:
                # Check if task is completed - FIXED: removed duplicate details__icontains
                task_completed = ActivityLog.objects.filter(
                    user=user,
                    activity_type='task_status_changed',
                    details__icontains=task.description
                ).filter(
                    details__icontains='Completed'
                ).exists()
                
                if task_completed:
                    completed_tasks += 1
                
                task_details.append({
                    'id': task.id,
                    'description': task.description,
                    'is_completed': task_completed
                })
            
            checklist_details.append({
                'id': checklist.id,
                'name': checklist.name,
                'frequency': checklist.get_frequency_display(),
                'is_completed': is_completed,
                'tasks': task_details,
                'total_tasks': len(task_details),
                'completed_tasks': completed_tasks,
                'task_completion_rate': round((completed_tasks / len(task_details)) * 100) if len(task_details) > 0 else 0
            })
        
        # Calculate overall completion rate
        if total_checklists > 0:
            completion_rate = round((completed_checklists / total_checklists) * 100)
        else:
            completion_rate = 0
        
        # Determine status
        if completion_rate >= 90:
            status = 'success'
        elif completion_rate >= 70:
            status = 'warning'
        else:
            status = 'danger'
        
        user_completion_data.append({
            'user': user,
            'total_checklists': total_checklists,
            'completed_checklists': completed_checklists,
            'completion_rate': completion_rate,
            'status': status,
            'checklist_details': checklist_details,
        })
    
    # Sort by completion rate descending
    user_completion_data.sort(key=lambda x: x['completion_rate'], reverse=True)
    
    # Calculate overall statistics
    total_users = len(user_completion_data)
    avg_completion = sum(u['completion_rate'] for u in user_completion_data) / total_users if total_users > 0 else 0
    
    context = {
        'user_profile': user_profile,
        'user_completion_data': user_completion_data,
        'total_users': total_users,
        'avg_completion': round(avg_completion),
        'all_checklists': all_checklists,
    }
    
    return render(request, 'control_dashboard/checklist-sup.html', context)


@csrf_exempt
@require_http_methods(["GET"])
def api_user_checklist_detail(request, user_id):
    """
    API endpoint to get detailed checklist completion for a specific user.
    """
    try:
        user = get_object_or_404(UserProfile, id=user_id)
        
        # Get all active checklists
        all_checklists = Checklist.objects.filter(is_active=True)
        
        # Get checklists assigned to this user
        assigned_checklists = all_checklists.filter(
            Q(assigned_users=user) | 
            Q(assignment_target='all')
        ).distinct()
        
        checklist_details = []
        completed_count = 0
        
        for checklist in assigned_checklists:
            # Check if completed
            is_completed = ActivityLog.objects.filter(
                user=user,
                activity_type='checklist_updated',
                details__icontains=checklist.name
            ).exists()
            
            if is_completed:
                completed_count += 1
            
            # Get tasks
            tasks = checklist.tasks.all()
            completed_tasks = 0
            task_list = []
            
            for task in tasks:
                # Check if task is completed - FIXED: removed duplicate details__icontains
                task_completed = ActivityLog.objects.filter(
                    user=user,
                    activity_type='task_status_changed',
                    details__icontains=task.description
                ).filter(
                    details__icontains='Completed'
                ).exists()
                
                if task_completed:
                    completed_tasks += 1
                
                task_list.append({
                    'id': task.id,
                    'description': task.description,
                    'is_completed': task_completed
                })
            
            checklist_details.append({
                'id': checklist.id,
                'name': checklist.name,
                'frequency': checklist.get_frequency_display(),
                'is_completed': is_completed,
                'tasks': task_list,
                'total_tasks': len(task_list),
                'completed_tasks': completed_tasks,
                'task_completion_rate': round((completed_tasks / len(task_list)) * 100) if len(task_list) > 0 else 0
            })
        
        total_checklists = len(assigned_checklists)
        completion_rate = round((completed_count / total_checklists) * 100) if total_checklists > 0 else 0
        
        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'full_name': user.full_name or user.email,
                'email': user.email,
                'position': user.get_position_display(),
                'total_checklists': total_checklists,
                'completed_checklists': completed_count,
                'completion_rate': completion_rate,
                'checklist_details': checklist_details,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ==================== SUPERVISOR ACTIVITY LOGS ====================

def supervisor_activity_logs(request):
    """
    Supervisor Activity Logs view - shows all activities with user completion rates.
    """
    # Get the current user's profile
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except (UserProfile.DoesNotExist, AttributeError):
        user_profile = UserProfile.objects.first()
    
    # Get filter parameters
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    activity_filter = request.GET.get('activity', '')
    user_filter = request.GET.get('user', '')
    
    # Start with all logs
    logs = ActivityLog.objects.all()
    
    # Apply filters
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            logs = logs.filter(created_at__date__gte=start)
        except:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            logs = logs.filter(created_at__date__lte=end)
        except:
            pass
    
    if activity_filter and activity_filter != 'all':
        logs = logs.filter(activity_type=activity_filter)
    
    if user_filter and user_filter != 'all':
        logs = logs.filter(user_id=user_filter)
    
    # Get all users for filter dropdown
    users = UserProfile.objects.filter(
        role__in=['member', 'supervisor']
    )
    
    # Calculate completion rates for each user
    user_completion_rates = []
    for user in users:
        # Get all checklists assigned to this user
        assigned_checklists = Checklist.objects.filter(
            Q(assigned_users=user) | 
            Q(assignment_target='all')
        ).distinct()
        
        total_checklists = assigned_checklists.count()
        completed_checklists = 0
        
        # Check which checklists have been completed by this user
        for checklist in assigned_checklists:
            # Check if there's a log entry for this checklist
            has_log = ActivityLog.objects.filter(
                user=user,
                activity_type='checklist_updated',
                details__icontains=checklist.name
            ).exists()
            
            if has_log:
                completed_checklists += 1
        
        # Calculate completion percentage
        if total_checklists > 0:
            completion_rate = round((completed_checklists / total_checklists) * 100)
        else:
            completion_rate = 0
        
        # Get recent activities for this user
        recent_activities = ActivityLog.objects.filter(
            user=user
        ).order_by('-created_at')[:5]
        
        user_completion_rates.append({
            'user': user,
            'total_checklists': total_checklists,
            'completed_checklists': completed_checklists,
            'completion_rate': completion_rate,
            'recent_activities': recent_activities,
            'status': 'success' if completion_rate >= 90 else 'warning' if completion_rate >= 70 else 'danger'
        })
    
    # Sort by completion rate descending
    user_completion_rates.sort(key=lambda x: x['completion_rate'], reverse=True)
    
    context = {
        'user_profile': user_profile,
        'activity_logs': logs,
        'users': users,
        'user_completion_rates': user_completion_rates,
        'activity_types': ActivityLog.ACTIVITY_CHOICES,
        'start_date': start_date,
        'end_date': end_date,
        'activity_filter': activity_filter,
        'user_filter': user_filter,
        'total_logs': logs.count(),
    }
    
    return render(request, 'control_dashboard/activity-sup.html', context)

# ==================== SUPERVISOR ACTIVITY LOGS ====================

def supervisor_activity_logs(request):
    """
    Supervisor Activity Logs view - shows all activities with filtering.
    """
    # Get the current user's profile
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except (UserProfile.DoesNotExist, AttributeError):
        user_profile = UserProfile.objects.first()
    
    # Get filter parameters
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    activity_filter = request.GET.get('activity', '')
    user_filter = request.GET.get('user', '')
    
    # Start with all logs
    logs = ActivityLog.objects.all()
    
    # Apply filters
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            logs = logs.filter(created_at__date__gte=start)
        except:
            pass    
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            logs = logs.filter(created_at__date__lte=end)
        except:
            pass
    
    if activity_filter and activity_filter != 'all':
        logs = logs.filter(activity_type=activity_filter)
    
    if user_filter and user_filter != 'all':
        logs = logs.filter(user_id=user_filter)
    
    # Get all users for filter dropdown
    users = UserProfile.objects.all()
    
    # Get activity type counts for statistics
    activity_counts = {}
    for log in logs:
        activity_counts[log.activity_type] = activity_counts.get(log.activity_type, 0) + 1
    
    context = {
        'user_profile': user_profile,
        'activity_logs': logs,
        'users': users,
        'activity_types': ActivityLog.ACTIVITY_CHOICES,
        'start_date': start_date,
        'end_date': end_date,
        'activity_filter': activity_filter,
        'user_filter': user_filter,
        'total_logs': logs.count(),
        'activity_counts': activity_counts,
    }
    
    return render(request, 'control_dashboard/activity-sup.html', context)

# ==================== AUTHENTICATION VIEWS ====================
# Add these functions after your imports

def login_view(request):
    """
    Login page view with Microsoft login option.
    """
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(email=request.user.email)
            if user_profile.role == 'admin':
                return redirect('admin_page')
            elif user_profile.role == 'supervisor':
                return redirect('supervisor_dashboard')
            else:
                return redirect('member_dashboard')
        except UserProfile.DoesNotExist:
            pass
    
    return render(request, 'control_dashboard/login.html')

def microsoft_login(request):
    """
    Redirect to Microsoft login.
    """
    return redirect(reverse('social:begin', args=['azuread-oauth2']))

def logout_view(request):
    """
    Logout view.
    """
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(email=request.user.email)
            log_activity(
                user=user_profile,
                activity_type='logout',
                details=f'User logged out',
                request=request
            )
        except:
            pass
    
    auth_logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')

def test_login(request, role):
    """
    Development-only test login.
    """
    if not settings.DEBUG:
        return redirect('login')
    
    # Map role to email
    role_emails = {
        'admin': 'admin@test.com',
        'member': 'member@test.com',
        'supervisor': 'supervisor@test.com'
    }
    
    email = role_emails.get(role)
    if not email:
        messages.error(request, 'Invalid test role')
        return redirect('login')
    
    # Get or create Django user
    django_user, created = DjangoUser.objects.get_or_create(
        username=email,
        defaults={'email': email}
    )
    
    if created:
        django_user.set_password('Test@123')
        django_user.save()
    
    # Get or create UserProfile
    try:
        user_profile = UserProfile.objects.get(email=email)
    except UserProfile.DoesNotExist:
        # Map role to position and role
        role_map = {
            'admin': {'position': 'hoc', 'role': 'admin'},
            'member': {'position': 'hoc', 'role': 'member'},
            'supervisor': {'position': 'cc', 'role': 'supervisor'}
        }
        role_data = role_map.get(role, {'position': 'hoc', 'role': 'member'})
        
        user_profile = UserProfile.objects.create(
            email=email,
            full_name=f'{role.capitalize()} User',
            position=role_data['position'],
            role=role_data['role'],
            status='active'
        )
    
    # Login the user
    auth_login(request, django_user)
    
    # Log the activity
    log_activity(
        user=user_profile,
        activity_type='login',
        details=f'Test login as {role}',
        request=request
    )
    
    # Redirect based on role
    if role == 'admin':
        return redirect('admin_page')
    elif role == 'supervisor':
        return redirect('supervisor_dashboard')
    else:
        return redirect('member_dashboard')

def get_or_create_user_profile(django_user):
    """
    Helper function to get or create UserProfile from Django user.
    """
    try:
        user_profile = UserProfile.objects.get(email=django_user.email)
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(
            email=django_user.email,
            full_name=django_user.get_full_name() or django_user.username,
            position='hoc',
            role='member',
            status='active'
        )
    return user_profile