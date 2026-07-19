from django.db import models  # Add this import
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.models import User as DjangoUser
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count  # Keep this too
from django.contrib.auth.decorators import login_required
import json
from datetime import datetime, timedelta
from django.utils import timezone

from .models import (
    UserProfile, 
    Report,
    ReportTemplate,
    TemplateField,
    Checklist,
    ChecklistTask,
    ChecklistLog,  
    ReportSubmission,
    ActivityLog,
    AdHocDeduction,
)
from .forms import UserProfileForm


# ==================== HELPER FUNCTIONS ====================

def log_activity(user, activity_type, details, request=None):
    """
    Helper function to log user activities.
    """
    try:
        from .models import ActivityLog
        ip_address = request.META.get('REMOTE_ADDR') if request else None
        user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
        ActivityLog.objects.create(
            user=user,
            activity_type=activity_type,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    except Exception:
        pass


def redirect_dashboard(user):
    """
    Redirect user to their appropriate dashboard based on role.
    """
    try:
        user_profile = UserProfile.objects.get(email=user.email)
        redirect_urls = {
            'admin': '/adminboard/admin/',
            'supervisor': '/adminboard/supervisor/',
            'member': '/adminboard/member/'
        }
        return redirect(redirect_urls.get(user_profile.role, '/adminboard/member/'))
    except UserProfile.DoesNotExist:
        return redirect('/adminboard/member/')
    

# ==================== LOGIN VIEWS ====================

def landing_page(request):
    """
    Landing page / Login page view.
    """
    if request.user.is_authenticated:
        return redirect_dashboard(request.user)
    return render(request, 'control_dashboard/index.html')


# ==================== LOGOUT VIEW ====================

def logout_view(request):
    """
    Logout view - this is already correctly linked to the logout button.
    """
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(email=request.user.email)
            log_activity(
                user=user_profile,
                activity_type='logout',
                details=f'User {request.user.email} logged out',
                request=request
            )
        except:
            pass
    
    auth_logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('control_dashboard:landing_page')


# ==================== API - AUTHENTICATION ====================

@csrf_exempt
@require_http_methods(["POST"])
def api_email_login(request):
    """
    API endpoint for email-based login.
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        
        if not email:
            return JsonResponse({
                'success': False,
                'error': 'Email is required'
            }, status=400)
        
        try:
            user_profile = UserProfile.objects.get(email__iexact=email)
        except UserProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'No account found with this email. Please contact your administrator.'
            }, status=404)
        
        if user_profile.status != 'active':
            return JsonResponse({
                'success': False,
                'error': 'Your account is inactive. Please contact support.'
            }, status=403)
        
        django_user, created = DjangoUser.objects.get_or_create(
            email__iexact=email,
            defaults={'username': email, 'email': email}
        )
        
        if created:
            django_user.save()
        
        auth_login(request, django_user)
        
        log_activity(
            user=user_profile,
            activity_type='login',
            details=f'User {email} logged in via email API',
            request=request
        )
        
        redirect_urls = {
            'admin': '/adminboard/admin/',
            'supervisor': '/adminboard/supervisor/',
            'member': '/adminboard/member/'
        }
        
        return JsonResponse({
            'success': True,
            'message': f'Welcome back, {user_profile.full_name}!',
            'redirect_url': redirect_urls.get(user_profile.role, '/adminboard/member/'),
            'user': {
                'id': user_profile.id,
                'email': user_profile.email,
                'full_name': user_profile.full_name,
                'role': user_profile.role,
                'position': user_profile.position
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_user_profile_api(request):
    """
    Get current user profile for API.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'authenticated': False}, status=401)
    
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        return JsonResponse({
            'authenticated': True,
            'user': {
                'id': user_profile.id,
                'email': user_profile.email,
                'full_name': user_profile.full_name,
                'role': user_profile.role,
                'position': user_profile.position,
                'status': user_profile.status
            }
        })
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'authenticated': True,
            'user': {
                'email': request.user.email,
                'full_name': request.user.get_full_name() or request.user.username,
                'role': 'member',
                'position': 'member'
            }
        })


# ==================== ADMIN VIEWS ====================

@login_required
def admin_page(request):
    """
    Admin dashboard view with user management.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    # Get all users
    users = UserProfile.objects.all().order_by('full_name')
    
    # Get choices for dropdowns
    positions = UserProfile.POSITION_CHOICES
    roles = UserProfile.ROLE_CHOICES
    statuses = UserProfile.STATUS_CHOICES
    
    context = {
        'user_profile': user_profile,
        'users': users,
        'positions': positions,
        'roles': roles,
        'statuses': statuses,
    }
    
    return render(request, 'control_dashboard/adminboard.html', context)


# ==================== API - ADMIN USER MANAGEMENT ====================

@csrf_exempt
@require_http_methods(["POST"])
def api_create_user(request):
    """
    API endpoint to create a new user.
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        full_name = data.get('full_name', '').strip()
        position = data.get('position', 'member')
        role = data.get('role', 'member')
        status = data.get('status', 'active')
        
        if not email:
            return JsonResponse({'success': False, 'error': 'Email is required'}, status=400)
        
        if not full_name:
            return JsonResponse({'success': False, 'error': 'Full name is required'}, status=400)
        
        if UserProfile.objects.filter(email__iexact=email).exists():
            return JsonResponse({'success': False, 'error': 'A user with this email already exists'}, status=400)
        
        user = UserProfile.objects.create(
            email=email.lower(),
            full_name=full_name,
            position=position,
            role=role,
            status=status
        )
        
        # Also create Django user for authentication
        django_user, created = DjangoUser.objects.get_or_create(
            username=email.lower(),
            defaults={'email': email.lower()}
        )
        
        if created:
            django_user.save()
        
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
    API endpoint to edit an existing user.
    """
    try:
        user = get_object_or_404(UserProfile, id=user_id)
        data = json.loads(request.body)
        
        changes = []
        old_email = user.email  # Store old email for Django user update
        
        if 'email' in data:
            new_email = data['email'].strip().lower()
            if new_email and new_email != user.email:
                if UserProfile.objects.filter(email=new_email).exclude(id=user_id).exists():
                    return JsonResponse({'success': False, 'error': 'Email already in use'}, status=400)
                changes.append(f'Email changed from {user.email} to {new_email}')
                user.email = new_email
        
        if 'full_name' in data and data['full_name'].strip() != user.full_name:
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
        
        # Update Django user if email changed
        if 'email' in data and data['email'].strip().lower() != old_email:
            try:
                # Try to find Django user by old email/username
                django_user = DjangoUser.objects.get(username=old_email)
                django_user.username = user.email
                django_user.email = user.email
                django_user.save()
            except DjangoUser.DoesNotExist:
                # If not found, create a new one
                django_user, created = DjangoUser.objects.get_or_create(
                    username=user.email,
                    defaults={'email': user.email}
                )
                if created:
                    django_user.save()
        
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
    API endpoint to toggle user status.
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
            activity_type='user_updated',
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
    API endpoint to delete a user.
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


# ==================== SUPERVISOR VIEWS ====================

@login_required
def supervisor_dashboard(request):
    """
    Supervisor dashboard view.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'supervisor' and user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    context = {
        'user_profile': user_profile,
        'today': timezone.now(),
    }
    
    return render(request, 'control_dashboard/supervisorboard.html', context)


# ==================== REPORT CENTER VIEWS ====================

@login_required
def report_center(request):
    """
    Report Center view for creating and managing reports.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    # Get all reports
    reports = Report.objects.all().order_by('-created_at')
    
    # Filter by user
    user_filter = request.GET.get('user', '')
    if user_filter and user_filter != 'all':
        reports = reports.filter(assigned_to__id=user_filter)
    
    # Get only MEMBER users for assignment (no admin or supervisor)
    users = UserProfile.objects.filter(role='member', status='active').order_by('full_name')
    
    context = {
        'user_profile': user_profile,
        'reports': reports,
        'users': users,
        'user_filter': user_filter,
    }
    
    return render(request, 'control_dashboard/reportcenter.html', context)


# ==================== API - REPORT MANAGEMENT ====================

@csrf_exempt
@require_http_methods(["POST"])
def api_create_report(request):
    """
    API endpoint to create a new report safely parsing empty string variants.
    """
    try:
        if not request.body:
            return JsonResponse({'success': False, 'error': 'Empty layout request payload'}, status=400)
            
        data = json.loads(request.body)
        
        report_type = data.get('report_type', '').strip()
        frequency = data.get('frequency', 'one-off')
        description = data.get('description', '').strip()
        
        # Normalize empty inputs explicitly to None so they drop into DB cleanly as NULL
        deadline_date = data.get('deadline_date')
        if not deadline_date or str(deadline_date).strip() == '':
            deadline_date = None
            
        deadline_time = data.get('deadline_time')
        if not deadline_time or str(deadline_time).strip() == '':
            deadline_time = None
            
        assigned_users = data.get('assigned_users', [])
        is_assigned_to_all = data.get('is_assigned_to_all', False)
        
        if not report_type:
            return JsonResponse({'success': False, 'error': 'Report type is required'}, status=400)
        
        # Owner profile resolution fallback strategy
        created_by = None
        if request.user and request.user.is_authenticated:
            created_by = UserProfile.objects.filter(email=request.user.email).first()
            
        if not created_by:
            created_by = UserProfile.objects.filter(role='admin').first() or UserProfile.objects.first()
            
        if not created_by:
            return JsonResponse({'success': False, 'error': 'No profile accounts exist to take ownership'}, status=400)
        
        # Instantiate report record parameters safely
        report = Report.objects.create(
            report_type=report_type,
            frequency=frequency,
            description=description,
            deadline_date=deadline_date,
            deadline_time=deadline_time,
            is_assigned_to_all=is_assigned_to_all,
            created_by=created_by,
            status='assigned'
        )
        
        # Assign members securely based on targeted role filter constraints
        if is_assigned_to_all:
            all_members = UserProfile.objects.filter(role='member', status='active')
            report.assigned_to.set(all_members)
        elif assigned_users:
            active_members = UserProfile.objects.filter(id__in=assigned_users, role='member', status='active')
            report.assigned_to.set(active_members)
            
        try:
            log_activity(
                user=created_by,
                activity_type='report_created',
                details=f'Created report: {report_type}',
                request=request
            )
        except NameError:
            pass 
            
        return JsonResponse({
            'success': True,
            'message': 'Report created successfully',
            'report_id': report.id
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Malformed JSON structural arguments payload'}, status=400)
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
                'is_assigned_to_all': report.is_assigned_to_all,
                'data': report.data or {},
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def api_edit_report(request, report_id):
    """
    API endpoint to modify an existing report dataset instance securely.
    """
    try:
        report = get_object_or_404(Report, id=report_id)
        if not request.body:
            return JsonResponse({'success': False, 'error': 'Payload structural parameters cannot be blank'}, status=400)
            
        data = json.loads(request.body)
        changes = []
        
        if 'report_type' in data and data['report_type'].strip() != report.report_type:
            changes.append(f'Type changed from {report.report_type} to {data["report_type"]}')
            report.report_type = data['report_type'].strip()
        
        if 'frequency' in data and data['frequency'] != report.frequency:
            old_freq = report.get_frequency_display()
            report.frequency = data['frequency']
            changes.append(f'Frequency changed from {old_freq} to {report.get_frequency_display()}')
            
        if 'status' in data and data['status'] != report.status:
            old_status = report.get_status_display()
            report.status = data['status']
            changes.append(f'Status changed from {old_status} to {report.get_status_display()}')
            
        if 'description' in data:
            report.description = data['description'].strip()
            
        if 'deadline_date' in data:
            val = data['deadline_date']
            report.deadline_date = val if val and str(val).strip() != '' else None
            
        if 'deadline_time' in data:
            val = data['deadline_time']
            report.deadline_time = val if val and str(val).strip() != '' else None
            
        is_assigned_to_all = data.get('is_assigned_to_all', report.is_assigned_to_all)
        assigned_users = data.get('assigned_users', [])
        
        if is_assigned_to_all != report.is_assigned_to_all:
            report.is_assigned_to_all = is_assigned_to_all
            changes.append('Assignment mode toggled')
            
        if is_assigned_to_all:
            report.assigned_to.set(UserProfile.objects.filter(role='member', status='active'))
        elif 'assigned_users' in data:
            report.assigned_to.set(UserProfile.objects.filter(id__in=assigned_users, role='member', status='active'))
            changes.append('Assigned user profiles refreshed')
            
        report.save()
        
        if changes:
            try:
                log_activity(
                    user=report.created_by,
                    activity_type='report_updated',
                    details=f'Report {report.report_type} updated: ' + '; '.join(changes),
                    request=request
                )
            except NameError:
                pass
                
        return JsonResponse({'success': True, 'message': 'Report modifications indexed successfully'})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON structure constraints'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_delete_report(request, report_id):
    """
    API endpoint to delete a report.
    """
    try:
        report = get_object_or_404(Report, id=report_id)
        report_type = report.report_type
        
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

# control_dashboard/views.py - Add these functions

# ==================== TEMPLATE BUILDER VIEWS ====================

@login_required
def template_builder(request):
    """
    Template Builder view for creating and managing report templates.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    from .models import ReportTemplate, TemplateField
    
    templates = ReportTemplate.objects.all().order_by('-created_at')
    
    # Get all report types from existing reports and templates
    report_types = list(Report.objects.values_list('report_type', flat=True).distinct())
    template_names = list(ReportTemplate.objects.values_list('name', flat=True).distinct())
    all_report_types = list(set(report_types + template_names))
    all_report_types.sort()
    
    field_types = ReportTemplate.FIELD_TYPES
    data_sources = ReportTemplate.DATA_SOURCES
    
    context = {
        'user_profile': user_profile,
        'templates': templates,
        'report_types': all_report_types,
        'field_types': field_types,
        'data_sources': data_sources,
    }
    
    return render(request, 'control_dashboard/reporttemplate.html', context)


# ==================== API - TEMPLATE MANAGEMENT ====================

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
        
        if ReportTemplate.objects.filter(name=report_type).exists():
            return JsonResponse({'success': False, 'error': 'A template for this report type already exists'}, status=400)
        
        created_by = UserProfile.objects.get(email=request.user.email)
        
        template = ReportTemplate.objects.create(
            name=report_type,
            description=description,
            created_by=created_by,
            is_active=True
        )
        
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
        
        if 'fields' in data:
            template.fields.all().delete()
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


# ==================== CHECKLIST VIEWS ====================

@login_required
def checklist_builder(request):
    """
    Checklist Builder view for creating and managing checklists.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    from .models import Checklist, ChecklistTask
    
    checklists = Checklist.objects.all().order_by('-created_at')
    
    # Get ALL active users for assignment (members, cc, hc)
    users = UserProfile.objects.filter(status='active').order_by('full_name')
    
    # DEBUG: Print to console
    print(f"=== CHECKLIST BUILDER DEBUG ===")
    print(f"Total users found: {users.count()}")
    for user in users:
        print(f"  User: {user.id} - {user.full_name} - {user.email} - Position: {user.position}")
    
    frequencies = Checklist.FREQUENCY_CHOICES
    assignments = Checklist.ASSIGNMENT_CHOICES
    
    context = {
        'user_profile': user_profile,
        'checklists': checklists,
        'users': users,
        'frequencies': frequencies,
        'assignments': assignments,
    }
    
    return render(request, 'control_dashboard/checklist.html', context)


# ==================== API - CHECKLIST MANAGEMENT ====================

@require_http_methods(["POST"])
def api_create_checklist(request):
    """
    API endpoint to create a new checklist from JSON payload.
    """
    try:
        # Check if request body contains data
        if not request.body:
            return JsonResponse({'success': False, 'error': 'Empty request body'}, status=400)
            
        data = json.loads(request.body)
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        frequency = data.get('frequency', 'weekly')
        assignment_target = data.get('assignment_target', 'all')
        assigned_users_ids = data.get('assigned_users', [])
        tasks_data = data.get('tasks', [])
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Activity name is required'}, status=400)
        
        if not tasks_data:
            return JsonResponse({'success': False, 'error': 'Please add at least one task'}, status=400)
        
        # Safe fallback user identification strategy
        created_by = None
        if request.user and request.user.is_authenticated:
            created_by = UserProfile.objects.filter(email=request.user.email).first()
        
        if not created_by:
            created_by = UserProfile.objects.first()
            
        if not created_by:
            return JsonResponse({'success': False, 'error': 'No active UserProfile records found to assign ownership'}, status=400)
        
        # Create checklist record inside database
        checklist = Checklist.objects.create(
            name=name,
            description=description,
            frequency=frequency,
            assignment_target=assignment_target,
            created_by=created_by,
            is_active=True
        )
        
        # Bulk user assignment mapping strategy
        if assignment_target == 'specific':
            active_users = UserProfile.objects.filter(id__in=assigned_users_ids, status='active')
            checklist.assigned_users.set(active_users)
        elif assignment_target == 'cc':
            checklist.assigned_users.set(UserProfile.objects.filter(position='cc', status='active'))
        elif assignment_target == 'hc':
            checklist.assigned_users.set(UserProfile.objects.filter(position='hc', status='active'))
        elif assignment_target == 'all':
            checklist.assigned_users.set(UserProfile.objects.filter(status='active'))
        
        # Order-aware item population execution loop
        for index, task_item in enumerate(tasks_data):
            task_desc = task_item.get('description', '').strip()
            if task_desc:
                ChecklistTask.objects.create(
                    checklist=checklist,
                    description=task_desc,
                    order=index
                )
                
        return JsonResponse({
            'success': True,
            'message': 'Checklist created successfully',
            'checklist_id': checklist.id
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Malformed or invalid JSON payload structure'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_get_checklist(request, checklist_id):
    """
    API endpoint to get checklist details.
    """
    try:
        from .models import Checklist
        
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


@require_http_methods(["PUT"])
def api_edit_checklist(request, checklist_id):
    """
    API endpoint to update an existing checklist layout.
    """
    try:
        checklist = get_object_or_404(Checklist, id=checklist_id)
        if not request.body:
            return JsonResponse({'success': False, 'error': 'Empty patch payload parameters'}, status=400)
            
        data = json.loads(request.body)
        
        # Update core structural assignments
        if 'name' in data:
            checklist.name = data['name'].strip()
        if 'frequency' in data:
            checklist.frequency = data['frequency']
        if 'assignment_target' in data:
            checklist.assignment_target = data['assignment_target']
        checklist.save()
        
        # Dynamic membership lookup calculations
        assignment_target = data.get('assignment_target', checklist.assignment_target)
        if assignment_target == 'specific':
            assigned_users_ids = data.get('assigned_users', [])
            checklist.assigned_users.set(UserProfile.objects.filter(id__in=assigned_users_ids, status='active'))
        elif assignment_target == 'cc':
            checklist.assigned_users.set(UserProfile.objects.filter(position='cc', status='active'))
        elif assignment_target == 'hc':
            checklist.assigned_users.set(UserProfile.objects.filter(position='hc', status='active'))
        elif assignment_target == 'all':
            checklist.assigned_users.set(UserProfile.objects.filter(status='active'))
            
        # Complete subtask clear-and-rewrite sweep execution 
        if 'tasks' in data:
            checklist.tasks.all().delete()
            for index, task_item in enumerate(data['tasks']):
                task_desc = task_item.get('description', '').strip()
                if task_desc:
                    ChecklistTask.objects.create(
                        checklist=checklist,
                        description=task_desc,
                        order=index
                    )
                    
        return JsonResponse({'success': True, 'message': 'Checklist records synchronized successfully'})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data payload parameters'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_delete_checklist(request, checklist_id):
    """
    API endpoint to delete a checklist.
    """
    try:
        from .models import Checklist
        
        checklist = get_object_or_404(Checklist, id=checklist_id)
        checklist_name = checklist.name
        
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





# ==================== MEMBER DASHBOARD VIEW ====================

@login_required
def member_dashboard(request):
    """
    Member dashboard view showing assigned checklists, reports, and submissions.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except UserProfile.DoesNotExist:
        # If no profile exists, create one from the Django user
        user_profile = UserProfile.objects.create(
            email=request.user.email,
            full_name=request.user.get_full_name() or request.user.username,
            role='member',
            position='member',
            status='active'
        )
    
    # Get today's date
    today = timezone.now().date()
    
    # ============================================
    # WEEKLY CALCULATION: Friday to Thursday
    # ============================================
    # Get the current day of the week (0=Monday, 6=Sunday)
    weekday = today.weekday()
    
    # Calculate week start (Friday) and week end (Thursday)
    # If today is Friday (4), start is today, end is next Thursday
    # If today is Saturday (5), start is yesterday (Friday)
    # If today is Sunday (6), start is 2 days ago (Friday)
    # If today is Monday (0), start is 3 days ago (Friday)
    # If today is Tuesday (1), start is 4 days ago (Friday)
    # If today is Wednesday (2), start is 5 days ago (Friday)
    # If today is Thursday (3), start is 6 days ago (Friday)
    
    if weekday >= 4:  # Friday (4), Saturday (5), Sunday (6)
        # Week starts on the most recent Friday
        days_since_friday = weekday - 4
        week_start = today - timedelta(days=days_since_friday)
    else:  # Monday (0), Tuesday (1), Wednesday (2), Thursday (3)
        # Week starts on the previous Friday
        days_since_friday = weekday + 3  # Monday=3, Tuesday=4, Wednesday=5, Thursday=6
        week_start = today - timedelta(days=days_since_friday)
    
    # Week end is Thursday (6 days after Friday)
    week_end = week_start + timedelta(days=6)
    
    # Get checklists assigned to this user
    from .models import Checklist
    from django.db.models import Q
    
    user_checklists = Checklist.objects.filter(
        is_active=True
    ).filter(
        Q(assigned_users=user_profile) |
        Q(assignment_target='all') |
        Q(assignment_target=user_profile.position)
    ).distinct()
    
    # Daily checklists
    daily_checklists = user_checklists.filter(frequency='daily')[:5]
    
    # ============================================
    # ASSIGNED THIS WEEK (Friday to Thursday)
    # ============================================
    assigned_this_week = user_checklists.filter(
        created_at__date__gte=week_start,
        created_at__date__lte=week_end
    ).count()
    
    # ============================================
    # EXCEPTIONS CAPTURED (Friday to Thursday)
    # ============================================
    # Count reports (exceptions) created by this user during the week
    exceptions_captured = Report.objects.filter(
        created_by=user_profile,
        created_at__date__gte=week_start,
        created_at__date__lte=week_end
    ).count()
    
    # Count pending submissions (reports with status 'submitted' or 'draft')
    pending_submissions = Report.objects.filter(
        Q(assigned_to=user_profile) |
        Q(created_by=user_profile) |
        Q(is_assigned_to_all=True)
    ).filter(
        Q(status='submitted') | Q(status='draft')
    ).distinct().count()
    
    # Get recent submissions (completed reports)
    recent_submissions = Report.objects.filter(
        Q(assigned_to=user_profile) |
        Q(created_by=user_profile) |
        Q(is_assigned_to_all=True)
    ).filter(
        status='submitted'
    ).order_by('-updated_at')[:5]
    
    # Prepare submission data with additional fields
    submission_data = []
    for report in recent_submissions:
        # Calculate if on time
        is_on_time = True
        if report.deadline_date:
            if report.deadline_date < timezone.now().date():
                is_on_time = False
            elif report.deadline_date == timezone.now().date() and report.deadline_time:
                current_time = timezone.now().time()
                if current_time > report.deadline_time:
                    is_on_time = False
        
        # Calculate final score (example logic - adjust as needed)
        final_score = None
        manual_deduction = 0
        if report.data:
            if isinstance(report.data, dict):
                if 'score' in report.data:
                    final_score = report.data.get('score')
                if 'manual_deduction' in report.data:
                    manual_deduction = report.data.get('manual_deduction')
        
        submission_data.append({
            'report_type': report.report_type,
            'deadline_date': report.deadline_date,
            'submitted_at': report.updated_at,
            'is_on_time': is_on_time,
            'manual_deduction': manual_deduction,
            'final_score': final_score,
        })
    
    context = {
        'user_profile': user_profile,
        'today': today,
        'week_start': week_start,
        'week_end': week_end,
        'assigned_this_week': assigned_this_week,
        'exceptions_captured': exceptions_captured,
        'pending_submissions': pending_submissions,
        'daily_checklists': daily_checklists,
        'recent_submissions': submission_data,
        'all_checklists': user_checklists,
    }
    
    return render(request, 'control_dashboard/memberboard.html', context)

# ==================== SUBMIT REPORT VIEWS ====================

@login_required
def drafts_page(request):
    """Submit Report page for member."""
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except UserProfile.DoesNotExist:
        return redirect('control_dashboard:member_dashboard')
    
    # Get all report types from templates
    from .models import ReportTemplate
    report_types = ReportTemplate.objects.filter(is_active=True).values_list('name', flat=True).distinct()
    
    context = {
        'user_profile': user_profile,
        'today': timezone.now(),
        'report_types': list(report_types),
    }
    return render(request, 'control_dashboard/draft.html', context)


@csrf_exempt
@require_http_methods(["GET"])
def api_get_template_fields(request):
    """
    API endpoint to get template fields for a report type.
    """
    try:
        report_type = request.GET.get('report_type', '')
        
        if not report_type:
            return JsonResponse({'success': False, 'error': 'Report type is required'}, status=400)
        
        from .models import ReportTemplate
        
        template = ReportTemplate.objects.filter(name=report_type, is_active=True).first()
        
        if not template:
            return JsonResponse({'success': False, 'error': 'Template not found'}, status=404)
        
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
                        'options': field.get_options_list(),
                        'order': field.order
                    }
                    for field in fields
                ]
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_save_draft(request):
    """
    API endpoint to save a report submission directly to database.
    """
    try:
        print("=== API SAVE DRAFT CALLED ===")
        print(f"Request body: {request.body}")
        
        data = json.loads(request.body)
        print(f"Parsed data: {data}")
        
        report_type = data.get('report_type', '').strip()
        template_name = data.get('template_name', '').strip()
        form_data = data.get('form_data', [])
        excel_data = data.get('excel_data', [])
        
        print(f"Report Type: {report_type}")
        print(f"Template Name: {template_name}")
        print(f"Form Data: {form_data}")
        print(f"Excel Data: {excel_data}")
        
        if not report_type:
            return JsonResponse({'success': False, 'error': 'Report type is required'}, status=400)
        
        if not form_data:
            return JsonResponse({'success': False, 'error': 'No form data provided'}, status=400)
        
        # Get user profile
        try:
            user_profile = UserProfile.objects.get(email=request.user.email)
            print(f"User Profile: {user_profile}")
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        # Create ReportSubmission
        submission = ReportSubmission.objects.create(
            report_type=report_type,
            template_name=template_name,
            submitted_by=user_profile,
            status='submitted',  # Use 'submitted'
            data={
                'form_data': form_data,
                'excel_data': excel_data,
            }
        )
        print(f"Submission created with ID: {submission.id}")
        
        # Create Report record with status 'submitted'
        report = Report.objects.create(
            report_type=report_type,
            frequency='one-off',
            description=template_name,
            status='submitted',  # Use 'submitted' instead of 'completed'
            created_by=user_profile,
            data={
                'submission_id': submission.id,
                'form_data': form_data,
                'excel_data': excel_data,
            }
        )
        print(f"Report created with ID: {report.id}")
        print(f"Report data: {report.data}")
        
        return JsonResponse({
            'success': True,
            'message': 'Report submitted successfully',
            'submission_id': submission.id,
            'report_id': report.id
        })
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def reports_page(request):
    """View all submitted reports for member."""
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except UserProfile.DoesNotExist:
        return redirect('control_dashboard:member_dashboard')
    
    # Get ALL reports submitted by this user
    reports = Report.objects.filter(
        created_by=user_profile
    ).filter(
        Q(status='submitted') | Q(status='completed')
    ).order_by('-created_at')
    
    # DEBUG: Print the actual data structure
    print(f"=== REPORTS PAGE DEBUG ===")
    print(f"User: {user_profile.full_name}")
    print(f"Total reports found: {reports.count()}")
    for report in reports:
        print(f"  Report ID: {report.id}")
        print(f"  Report Type: {report.report_type}")
        print(f"  Status: {report.status}")
        print(f"  Data type: {type(report.data)}")
        print(f"  Data: {report.data}")
        if isinstance(report.data, dict):
            print(f"  Data keys: {list(report.data.keys())}")
            for key, value in report.data.items():
                print(f"    {key}: {value}")
        print("-" * 40)
    
    # Get unique report types
    report_types = reports.values_list('report_type', flat=True).distinct()
    
    # Get all branches for dropdown
    from .models import Branch
    branches = Branch.objects.filter(is_active=True).order_by('name')
    
    context = {
        'user_profile': user_profile,
        'today': timezone.now(),
        'reports': reports,
        'report_types': list(report_types),
        'branches': branches,
    }
    return render(request, 'control_dashboard/reports.html', context)


@login_required
def submit_page(request):
    """Submit page for member."""
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except UserProfile.DoesNotExist:
        return redirect('control_dashboard:member_dashboard')
    
    context = {
        'user_profile': user_profile,
        'today': timezone.now(),
    }
    return render(request, 'control_dashboard/submit.html', context)


@login_required
def member_checklist(request):
    """
    Member checklist view showing all checklists assigned to the user.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except UserProfile.DoesNotExist:
        return redirect('control_dashboard:member_dashboard')
    
    # Get all checklists assigned to this user
    user_checklists = Checklist.objects.filter(
        is_active=True
    ).filter(
        Q(assigned_users=user_profile) |
        Q(assignment_target='all') |
        Q(assignment_target=user_profile.position)
    ).distinct().order_by('name')
    
    # Build checklist data with logs
    checklist_data = []
    for checklist in user_checklists:
        # Get tasks for this checklist
        tasks = checklist.tasks.all().order_by('order')
        
        # Get logs for this checklist and user
        logs = ChecklistLog.objects.filter(
            checklist=checklist,
            user=user_profile
        ).values_list('log_date', flat=True)
        
        # Convert logs to string dates
        log_dates = [log.strftime('%Y-%m-%d') for log in logs]
        
        checklist_data.append({
            'id': checklist.id,
            'name': checklist.name,
            'frequency': checklist.frequency,
            'frequency_display': checklist.get_frequency_display(),
            'tasks': [{'description': task.description} for task in tasks],
            'logs': log_dates,
        })
    
    context = {
        'user_profile': user_profile,
        'checklist_data': checklist_data,
    }
    
    return render(request, 'control_dashboard/checklist-mem.html', context)


# ==================== API - CHECKLIST LOG ====================

@csrf_exempt
@require_http_methods(["POST"])
def api_log_checklist(request):
    """
    API endpoint to log or unlog a checklist completion for a specific date.
    """
    try:
        data = json.loads(request.body)
        
        checklist_id = data.get('checklist_id')
        log_date = data.get('log_date')
        action = data.get('action', 'log')  # 'log' or 'unlog'
        
        if not checklist_id:
            return JsonResponse({'success': False, 'error': 'Checklist ID is required'}, status=400)
        
        if not log_date:
            return JsonResponse({'success': False, 'error': 'Log date is required'}, status=400)
        
        # Get the user profile
        try:
            user_profile = UserProfile.objects.get(email=request.user.email)
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        # Get the checklist
        try:
            checklist = Checklist.objects.get(id=checklist_id, is_active=True)
        except Checklist.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Checklist not found'}, status=404)
        
        # Parse the date
        try:
            date_obj = datetime.strptime(log_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
        
        if action == 'log':
            # Create the log entry
            log_entry, created = ChecklistLog.objects.get_or_create(
                checklist=checklist,
                user=user_profile,
                log_date=date_obj
            )
            
            if created:
                return JsonResponse({
                    'success': True,
                    'message': 'Checklist logged successfully',
                    'action': 'logged'
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': 'Checklist already logged for this date',
                    'action': 'already_logged'
                })
                
        elif action == 'unlog':
            # Delete the log entry
            deleted_count, _ = ChecklistLog.objects.filter(
                checklist=checklist,
                user=user_profile,
                log_date=date_obj
            ).delete()
            
            if deleted_count > 0:
                return JsonResponse({
                    'success': True,
                    'message': 'Checklist unlogged successfully',
                    'action': 'unlogged'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'No log found for this date'
                }, status=404)
        
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action. Use "log" or "unlog"'}, status=400)
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_get_checklist_logs(request):
    """
    API endpoint to get all logs for a user.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        
        logs = ChecklistLog.objects.filter(user=user_profile).select_related('checklist')
        
        log_data = []
        for log in logs:
            log_data.append({
                'checklist_id': log.checklist.id,
                'checklist_name': log.checklist.name,
                'log_date': log.log_date.strftime('%Y-%m-%d'),
                'logged_at': log.created_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'logs': log_data
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_get_checklist_stats(request):
    """
    API endpoint to get checklist completion statistics.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        
        # Get all checklists assigned to user
        user_checklists = Checklist.objects.filter(
            is_active=True
        ).filter(
            Q(assigned_users=user_profile) |
            Q(assignment_target='all') |
            Q(assignment_target=user_profile.position)
        ).distinct()
        
        total_checklists = user_checklists.count()
        
        # Get logs for this user
        logs = ChecklistLog.objects.filter(user=user_profile)
        total_logs = logs.count()
        
        # Get logs for this week
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        weekly_logs = logs.filter(log_date__gte=start_of_week, log_date__lte=end_of_week).count()
        
        # Get last 7 days of logs
        last_7_days = today - timedelta(days=7)
        recent_logs = logs.filter(log_date__gte=last_7_days).count()
        
        # Get completion rate for daily checklists this week
        daily_checklists = user_checklists.filter(frequency='daily')
        daily_total = daily_checklists.count()
        
        completion_rate = 0
        if daily_total > 0:
            # Count how many daily checklists were completed each day this week
            completed_days = 0
            for i in range(7):
                day = start_of_week + timedelta(days=i)
                completed_for_day = logs.filter(log_date=day).count()
                if completed_for_day >= daily_total:
                    completed_days += 1
            completion_rate = int((completed_days / 7) * 100)
        
        return JsonResponse({
            'success': True,
            'stats': {
                'total_checklists': total_checklists,
                'total_logs': total_logs,
                'weekly_logs': weekly_logs,
                'recent_logs': recent_logs,
                'completion_rate': completion_rate,
                'daily_checklists': daily_total,
            }
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==================== MEMBER OTHER PAGES ====================

@login_required
def drafts_page(request):
    """Submit Report page for member - shows reports assigned to the user."""
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except UserProfile.DoesNotExist:
        return redirect('control_dashboard:member_dashboard')
    
    # Get reports assigned to this user
    from .models import Report
    
    # Get reports assigned to this user (either directly or via position)
    assigned_reports = Report.objects.filter(
        Q(assigned_to=user_profile) |
        Q(is_assigned_to_all=True)
    ).filter(
        status__in=['assigned', 'in_progress']
    ).distinct().order_by('-created_at')
    
    # Get unique report types from assigned reports
    report_types = assigned_reports.values_list('report_type', flat=True).distinct()
    
    context = {
        'user_profile': user_profile,
        'today': timezone.now(),
        'report_types': list(report_types),
        'assigned_reports': assigned_reports,
    }
    return render(request, 'control_dashboard/draft.html', context)

@require_http_methods(["GET"])
def api_get_report_data(request):
    """
    API endpoint to get existing report data for a user.
    """
    try:
        report_type = request.GET.get('report_type', '')
        
        if not report_type:
            return JsonResponse({'success': False, 'error': 'Report type is required'}, status=400)
        
        user_profile = UserProfile.objects.get(email=request.user.email)
        
        # Get existing submissions for this report type
        submissions = ReportSubmission.objects.filter(
            report_type=report_type,
            submitted_by=user_profile
        ).order_by('-submission_date')
        
        if submissions.exists():
            latest = submissions.first()
            form_data = latest.data.get('form_data', [])
            return JsonResponse({
                'success': True,
                'data': form_data,
                'submission_id': latest.id
            })
        else:
            return JsonResponse({
                'success': True,
                'data': []
            })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def reports_page(request):
    user_profile = get_object_or_404(UserProfile, email=request.user.email)
    
    # Order by report_type FIRST so regroup combines them into single blocks
    reports = Report.objects.filter(
        created_by=user_profile
    ).order_by('report_type', '-updated_at')  # <--- Primary sort on report_type

    context = {
        'reports': reports,
        'report_types': ReportTemplate.objects.filter(is_active=True).values_list('name', flat=True),
    }
    return render(request, 'control_dashboard/reports.html', context)


@login_required
def submit_page(request):
    """
    Submit page for member - shows exceptions assigned to the user.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except UserProfile.DoesNotExist:
        return redirect('control_dashboard:member_dashboard')
    
    # Get all exceptions (reports) assigned to this user
    from django.db.models import Q
    
    # Get reports where user is assigned or created by user
    assigned_exceptions = Report.objects.filter(
        Q(assigned_to=user_profile) |
        Q(created_by=user_profile) |
        Q(is_assigned_to_all=True)
    ).filter(
        Q(status='submitted') | Q(status='draft') | Q(status='rejected')
    ).distinct().order_by('-updated_at')
    
    # Get unique report types from assigned exceptions
    assigned_report_types = assigned_exceptions.values_list('report_type', flat=True).distinct()
    
    # Get email recipients (users with email)
    email_recipients = UserProfile.objects.filter(
        status='active'
    ).exclude(
        email__isnull=True
    ).exclude(
        email=''
    ).values('email', 'full_name', 'position')
    
    # Convert to list for JSON serialization
    email_recipients_list = []
    for recipient in email_recipients:
        email_recipients_list.append({
            'email': recipient['email'],
            'name': recipient['full_name'],
            'department': recipient['position'] or 'General'
        })
    
    # Get categories from the data (units/branches)
    categories = set()
    for exception in assigned_exceptions:
        if exception.data:
            # Try multiple possible field names for unit/branch
            unit = (
                exception.data.get('unit') or 
                exception.data.get('branch') or 
                exception.data.get('BRANCH') or 
                exception.data.get('DEPARTMENT') or
                exception.data.get('BRANCH/UNIT') or
                exception.data.get('branch_unit')
            )
            if unit:
                categories.add(unit)
    
    categories_list = [{'id': cat, 'name': cat} for cat in categories if cat]
    
    # Prepare exceptions data for JSON
    exceptions_data = []
    for exception in assigned_exceptions:
        exception_data = exception.data or {}
        
        # Get unit from multiple possible field names
        unit = (
            exception_data.get('unit') or 
            exception_data.get('branch') or 
            exception_data.get('BRANCH') or 
            exception_data.get('DEPARTMENT') or
            exception_data.get('BRANCH/UNIT') or
            exception_data.get('branch_unit') or
            'N/A'
        )
        
        # Get category from unit
        category = unit if unit != 'N/A' else 'uncategorized'
        
        exceptions_data.append({
            'id': exception.id,
            'report_type': exception.report_type,
            'status': exception.status,
            'status_display': exception.get_status_display(),
            'data': exception_data,
            'created_at': exception.created_at.strftime('%b %d, %Y'),
            'unit': unit,
            'category': category,
            'assigned_to': user_profile.email,
            'created_by': exception.created_by.email if exception.created_by else ''
        })
    
    context = {
        'user_profile': user_profile,
        'today': timezone.now(),
        'assigned_exceptions': assigned_exceptions,
        'assigned_report_types': list(assigned_report_types),
        'categories_list': categories_list,
        'exceptions_json': json.dumps(exceptions_data, default=str),
        'exceptions': exceptions_data,
        'email_recipients': email_recipients_list,
        'user_data': {
            'name': user_profile.full_name,
            'email': user_profile.email,
            'department': user_profile.position or 'General'
        },
        'report_types': list(assigned_report_types),
    }
    
    return render(request, 'control_dashboard/submit.html', context)

@login_required
def member_activity_logs(request):
    """Activity logs page for member."""
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except UserProfile.DoesNotExist:
        return redirect('control_dashboard:member_dashboard')
    
    # Get all logs for this user
    logs = ChecklistLog.objects.filter(user=user_profile).select_related('checklist').order_by('-log_date', '-created_at')[:50]
    
    context = {
        'user_profile': user_profile,
        'today': timezone.now(),
        'logs': logs,
    }
    return render(request, 'control_dashboard/member_activity_logs.html', context)


@login_required
def member_activity_logs(request):
    """Activity logs page for member."""
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except UserProfile.DoesNotExist:
        return redirect('control_dashboard:member_dashboard')
    
    context = {
        'user_profile': user_profile,
        'today': timezone.now(),
    }
    return render(request, 'control_dashboard/member_activity_logs.html', context)

















@csrf_exempt
@require_http_methods(["GET"])
def api_get_draft(request, report_id):
    """
    API endpoint to fetch data payload details for a single report/draft modal layout.
    """
    try:
        lookup_id = int(report_id) if str(report_id).isdigit() else report_id
        report = get_object_or_404(Report, id=lookup_id)
        
        try:
            user_profile = UserProfile.objects.get(email=request.user.email)
            if report.created_by != user_profile and user_profile.role != 'admin':
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User profile context not found'}, status=404)
        
        response_data = {
            'success': True,
            'report': {
                'id': str(report.id),
                'report_type': report.report_type,
                'status': report.status,
                'data': report.data or {},
            }
        }
        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_edit_draft(request, report_id):
    """
    API endpoint to save edited modifications back into the Report 
    and associated ReportSubmission tables.
    """
    try:
        print("=== API EDIT DRAFT CALLED ===")
        lookup_id = int(report_id) if str(report_id).isdigit() else report_id
        report = get_object_or_404(Report, id=lookup_id)
        
        try:
            user_profile = UserProfile.objects.get(email=request.user.email)
            if report.created_by != user_profile and user_profile.role != 'admin':
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User profile context not found'}, status=404)
        
        # Parse payload data sent by Javascript form collection
        data = json.loads(request.body)
        form_data = data.get('form_data', {})
        
        # Look up linked entry inside report_submissions table via report.data tracking configuration
        submission_id = report.data.get('submission_id') if isinstance(report.data, dict) else None
        submission = None
        
        if submission_id:
            try:
                submission = ReportSubmission.objects.get(id=submission_id)
                if not isinstance(submission.data, dict):
                    submission.data = {}
                
                # Update inner nested structural content arrays cleanly
                if 'form_data' in submission.data and isinstance(submission.data['form_data'], list):
                    if submission.data['form_data']:
                        submission.data['form_data'][0].update(form_data)
                    else:
                        submission.data['form_data'] = [form_data]
                else:
                    submission.data['form_data'] = [form_data]
                
                submission.updated_at = timezone.now()
                submission.save()
            except ReportSubmission.DoesNotExist:
                submission = None

        # Fallback tracking logic if no record was previously mapped to this draft
        if not submission:
            submission = ReportSubmission.objects.create(
                report_type=report.report_type,
                template_name=getattr(report, 'description', report.report_type),
                submitted_by=user_profile,
                status='submitted',
                data={'form_data': [form_data]}
            )
        
        # Sync core primary layout data values back on the Report block for dashboard views
        if not isinstance(report.data, dict):
            report.data = {}
            
        report.data['submission_id'] = submission.id
        
        if 'form_data' in report.data and isinstance(report.data['form_data'], list):
            if report.data['form_data']:
                report.data['form_data'][0].update(form_data)
            else:
                report.data['form_data'] = [form_data]
        else:
            report.data['form_data'] = [form_data]

        # Force status tracking updates to transition context correctly
        if report.status == 'assigned':
            report.status = 'in_progress'

        report.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Report modifications saved successfully',
            'data': form_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON format received'}, status=400)
    except Exception as e:
        print(f"Exception during edit save tracking: {e}")
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
@csrf_exempt
@require_http_methods(["DELETE"])
def api_delete_draft(request, report_id):
    """
    API endpoint to permanently erase draft records across reports 
    and report_submissions tables.
    """
    try:
        # Detect numeric vs alphanumeric/UUID primary keys safely
        lookup_id = int(report_id) if str(report_id).isdigit() else report_id
        report = get_object_or_404(Report, id=lookup_id)
        
        # Verify user permission boundaries
        try:
            user_profile = UserProfile.objects.get(email=request.user.email)
            if report.created_by != user_profile and user_profile.role != 'admin':
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User context profile not found'}, status=404)
        
        # Look up and delete the linked data from the report_submissions table
        if isinstance(report.data, dict) and 'submission_id' in report.data:
            submission_id = report.data.get('submission_id')
            if submission_id:
                ReportSubmission.objects.filter(id=submission_id).delete()
        
        # Delete the core report tracking record
        report.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Draft and associated data payload permanently removed from database storage.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# views.py

@login_required
def member_activity_logs(request):
    """
    Activity logs page for member - shows only activities performed by the logged-in user.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except UserProfile.DoesNotExist:
        return redirect('control_dashboard:member_dashboard')
    
    # Get filter parameters
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    activity_filter = request.GET.get('activity', '')
    
    # Base queryset - only activities for this user
    queryset = ActivityLog.objects.filter(user=user_profile)
    
    # Apply date filters
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            queryset = queryset.filter(created_at__date__gte=start_date_obj)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            queryset = queryset.filter(created_at__date__lte=end_date_obj)
        except ValueError:
            pass
    
    # Apply activity type filter
    if activity_filter and activity_filter != 'all':
        queryset = queryset.filter(activity_type=activity_filter)
    
    # Get activity logs
    activity_logs = queryset.order_by('-created_at')[:100]  # Limit to 100 most recent
    
    # Get stats
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    
    today_logs = ActivityLog.objects.filter(
        user=user_profile,
        created_at__date=today
    )
    
    week_logs = ActivityLog.objects.filter(
        user=user_profile,
        created_at__date__gte=start_of_week,
        created_at__date__lte=today
    )
    
    month_logs = ActivityLog.objects.filter(
        user=user_profile,
        created_at__date__gte=start_of_month,
        created_at__date__lte=today
    )
    
    # Get last activity
    last_activity = ActivityLog.objects.filter(
        user=user_profile
    ).order_by('-created_at').first()
    
    last_activity_display = last_activity.created_at.strftime('%b %d, %Y %H:%M') if last_activity else None
    
    # Get activity types for filter dropdown
    activity_types = ActivityLog.ACTIVITY_TYPES
    
    context = {
        'user_profile': user_profile,
        'activity_logs': activity_logs,
        'activity_types': activity_types,
        'activity_filter': activity_filter,
        'start_date': start_date,
        'end_date': end_date,
        'today_logs': today_logs,
        'week_logs': week_logs,
        'month_logs': month_logs,
        'last_activity': last_activity_display,
        'today': today,
    }
    
    return render(request, 'control_dashboard/activity-mem.html', context)


@csrf_exempt
@require_http_methods(["GET"])
def api_export_logs(request):
    """
    API endpoint to export activity logs as CSV.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
    
    # Get filter parameters
    user_filter = request.GET.get('user', 'all')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    activity_filter = request.GET.get('activity', '')
    
    # Base queryset - get ALL activity logs (not just the current user)
    queryset = ActivityLog.objects.all().select_related('user')
    
    # Apply user filter
    if user_filter != 'all':
        try:
            queryset = queryset.filter(user_id=int(user_filter))
        except ValueError:
            pass
    
    # Apply date filters
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            queryset = queryset.filter(created_at__date__gte=start_date_obj)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            queryset = queryset.filter(created_at__date__lte=end_date_obj)
        except ValueError:
            pass
    
    # Apply activity type filter
    if activity_filter and activity_filter != 'all':
        queryset = queryset.filter(activity_type=activity_filter)
    
    logs = queryset.order_by('-created_at')
    
    # Create CSV response
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="activity_logs_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date & Time', 'User', 'Activity Type', 'Details', 'IP Address'])
    
    for log in logs:
        writer.writerow([
            log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            log.user.full_name or log.user.email,
            log.get_activity_type_display(),
            log.details or '',
            log.ip_address or ''
        ])
    
    return response

@login_required
def supervisor_dashboard(request):
    """
    Supervisor dashboard view showing team performance and metrics.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'supervisor' and user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    # Get today's date
    today = timezone.now().date()
    
    # ============================================
    # WEEKLY CALCULATION: Friday to Thursday
    # ============================================
    weekday = today.weekday()
    
    if weekday >= 4:
        days_since_friday = weekday - 4
        week_start = today - timedelta(days=days_since_friday)
    else:
        days_since_friday = weekday + 3
        week_start = today - timedelta(days=days_since_friday)
    
    week_end = week_start + timedelta(days=6)
    
    # ============================================
    # TEAM MEMBERS (Supervisor's team)
    # ============================================
    # Get all members under this supervisor
    # This assumes you have a supervisor field in UserProfile or you can get by department
    # For now, get all members
    from django.db.models import Q
    
    team_members = UserProfile.objects.filter(
        role='member',
        status='active'
    ).order_by('full_name')
    
    # ============================================
    # TEAM PERFORMANCE DATA
    # ============================================
    team_performance = []
    total_submitted = 0
    
    for member in team_members:
        # Count submitted reports for this member in the current week
        submitted_count = Report.objects.filter(
            created_by=member,
            created_at__date__gte=week_start,
            created_at__date__lte=week_end,
            status='submitted'
        ).count()
        
        total_submitted += submitted_count
        
        # Calculate percentage based on expected submissions
        # You can adjust this logic based on your business rules
        expected_submissions = 5  # Example: 5 reports per week
        percentage = min(100, int((submitted_count / expected_submissions) * 100)) if expected_submissions > 0 else 0
        
        # Determine status based on percentage
        if percentage >= 80:
            status = 'success'
        elif percentage >= 50:
            status = 'warning'
        else:
            status = 'danger'
        
        team_performance.append({
            'user': member,
            'submitted': submitted_count,
            'percentage': percentage,
            'status': status,
        })
    
    # Sort by percentage (highest first)
    team_performance.sort(key=lambda x: x['percentage'], reverse=True)
    
    # ============================================
    # METRICS
    # ============================================
    # Total exceptions (all reports with status 'submitted' or 'draft')
    total_exceptions = Report.objects.filter(
        Q(status='submitted') | Q(status='draft')
    ).count()
    
    # Today's exceptions
    today_exceptions = Report.objects.filter(
        Q(status='submitted') | Q(status='draft'),
        created_at__date=today
    ).count()
    
    # Submitted reports this week
    submitted_reports_count = Report.objects.filter(
        status='submitted',
        created_at__date__gte=week_start,
        created_at__date__lte=week_end
    ).count()
    
    # Team completion rate (average of all team members)
    if team_performance:
        completion_rate = sum(m['percentage'] for m in team_performance) // len(team_performance)
    else:
        completion_rate = 0
    
    context = {
        'user_profile': user_profile,
        'today': today,
        'week_start': week_start,
        'week_end': week_end,
        'team_performance': team_performance,
        'total_exceptions': total_exceptions,
        'today_exceptions': today_exceptions,
        'submitted_reports_count': submitted_reports_count,
        'completion_rate': completion_rate,
    }
    
    return render(request, 'control_dashboard/supervisorboard.html', context)

@login_required
def team_performance(request):
    """
    Team Performance page for supervisor.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'supervisor' and user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    # Get all team members (members under this supervisor)
    # You can filter by department or supervisor relationship
    team_members = UserProfile.objects.filter(
        role='member',
        status='active'
    ).order_by('full_name')
    
    # Calculate team performance data
    team_data = []
    total_tasks = 0
    total_completed = 0
    
    for member in team_members:
        # Count tasks (checklists) assigned to this member
        assigned_checklists = Checklist.objects.filter(
            assigned_users=member
        ).count()
        
        # Count completed tasks (checklist logs)
        completed_checklists = ChecklistLog.objects.filter(
            user=member
        ).count()
        
        total_tasks += assigned_checklists
        total_completed += completed_checklists
        
        # Calculate percentage
        percentage = 0
        if assigned_checklists > 0:
            percentage = int((completed_checklists / assigned_checklists) * 100)
        
        # Determine status
        if percentage >= 80:
            status = 'success'
            status_text = 'Excellent'
        elif percentage >= 50:
            status = 'warning'
            status_text = 'In Progress'
        else:
            status = 'danger'
            status_text = 'Needs Attention'
        
        team_data.append({
            'user': member,
            'total_tasks': assigned_checklists,
            'completed': completed_checklists,
            'percentage': percentage,
            'status': status,
            'status_text': status_text,
        })
    
    # Calculate overall completion
    overall_completion = 0
    if total_tasks > 0:
        overall_completion = int((total_completed / total_tasks) * 100)
    
    context = {
        'user_profile': user_profile,
        'team_data': team_data,
        'total_members': len(team_members),
        'total_tasks': total_tasks,
        'total_completed': total_completed,
        'overall_completion': overall_completion,
    }
    
    return render(request, 'control_dashboard/team.html', context)


@login_required
def submitted_reports(request):
    """
    Submitted Reports page for supervisor.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'supervisor' and user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    # Get filter parameters
    user_filter = request.GET.get('user', 'all')
    category_filter = request.GET.get('category', 'all')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Base queryset - get all submitted reports
    reports = Report.objects.filter(status='submitted')
    
    # Apply user filter
    if user_filter != 'all':
        try:
            reports = reports.filter(created_by_id=int(user_filter))
        except ValueError:
            pass
    
    # Apply category filter
    if category_filter != 'all':
        reports = reports.filter(report_type=category_filter)
    
    # Apply date filters
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            reports = reports.filter(created_at__date__gte=start_date_obj)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            reports = reports.filter(created_at__date__lte=end_date_obj)
        except ValueError:
            pass
    
    # Get all users for filter dropdown
    users = UserProfile.objects.filter(
        role='member',
        status='active'
    ).order_by('full_name')
    
    # Get all categories
    categories = Report.objects.values_list('report_type', flat=True).distinct()
    
    # Prepare report data
    report_data = []
    total_reports = 0
    approved_count = 0
    pending_count = 0
    rejected_count = 0
    
    for report in reports:
        total_reports += 1
        
        # Determine status display
        status_display = report.get_status_display()
        
        # Count by status
        if report.status == 'approved':
            approved_count += 1
        elif report.status == 'submitted':
            pending_count += 1
        elif report.status == 'rejected':
            rejected_count += 1
        
        # Calculate score
        manual_deduction = 0
        if report.data and isinstance(report.data, dict):
            manual_deduction = report.data.get('manual_deduction', 0)
        
        # Base score (100% minus deduction)
        final_score = max(0, 100 - manual_deduction)
        
        # Determine badge class
        if final_score >= 80:
            badge_class = 'success'
        elif final_score >= 50:
            badge_class = 'warning'
        else:
            badge_class = 'danger'
        
        report_data.append({
            'report': report,
            'created_by': report.created_by,
            'report_type': report.report_type,
            'status': report.status,
            'status_display': status_display,
            'submitted_at': report.created_at,
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
        'total_reports': total_reports,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'rejected_count': rejected_count,
    }
    
    return render(request, 'control_dashboard/submitted.html', context)


@login_required
def ad_hoc_scorecard(request):
    """
    Ad-Hoc Scorecard page for supervisor.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'supervisor' and user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    # Get filter parameter
    user_filter = request.GET.get('user', 'all')
    
    # Get all users for filter dropdown
    users = UserProfile.objects.filter(
        role='member',
        status='active'
    ).order_by('full_name')
    
    # Get deductions - handle case where table doesn't exist yet
    try:
        deductions = AdHocDeduction.objects.select_related('user', 'created_by').all().order_by('-created_at')
        
        # Apply user filter
        if user_filter != 'all':
            try:
                deductions = deductions.filter(user_id=int(user_filter))
            except ValueError:
                pass
        
        # Prepare deduction data for template
        deduction_data = []
        total_points = 0
        
        for deduction in deductions:
            total_points += deduction.points
            deduction_data.append({
                'id': deduction.id,
                'user_name': deduction.user.full_name,
                'user_email': deduction.user.email,
                'task_description': deduction.task_description,
                'points': deduction.points,
                'reason': deduction.reason,
                'created_at': deduction.created_at,
                'badge_class': deduction.get_badge_class(),
            })
    except Exception as e:
        # If table doesn't exist, return empty data
        print(f"Error loading deductions: {e}")
        deduction_data = []
        total_points = 0
    
    context = {
        'user_profile': user_profile,
        'users': users,
        'user_filter': user_filter,
        'deductions': deduction_data,
        'total_deductions': len(deduction_data),
        'total_points': total_points,
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
        task_description = data.get('task_description', '').strip()
        points = data.get('points', 0)
        reason = data.get('reason', '').strip()
        
        if not user_id:
            return JsonResponse({'success': False, 'error': 'User is required'}, status=400)
        
        if not task_description:
            return JsonResponse({'success': False, 'error': 'Task description is required'}, status=400)
        
        try:
            points = int(points)
            if points < 0 or points > 100:
                return JsonResponse({'success': False, 'error': 'Points must be between 0 and 100'}, status=400)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid points value'}, status=400)
        
        try:
            user = UserProfile.objects.get(id=user_id)
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        try:
            created_by = UserProfile.objects.get(email=request.user.email)
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Creator not found'}, status=404)
        
        # Create deduction
        deduction = AdHocDeduction.objects.create(
            user=user,
            task_description=task_description,
            points=points,
            reason=reason,
            created_by=created_by
        )
        
        # Log activity
        log_activity(
            user=created_by,
            activity_type='deduction_created',
            details=f'Created deduction of {points}% for {user.full_name} - {task_description}',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Deduction created successfully',
            'deduction_id': deduction.id
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
        deduction = get_object_or_404(AdHocDeduction, id=deduction_id)
        
        # Check permission
        try:
            user_profile = UserProfile.objects.get(email=request.user.email)
            if deduction.created_by != user_profile and user_profile.role != 'admin':
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        data = json.loads(request.body)
        
        if 'task_description' in data:
            deduction.task_description = data['task_description'].strip()
        
        if 'points' in data:
            try:
                points = int(data['points'])
                if points < 0 or points > 100:
                    return JsonResponse({'success': False, 'error': 'Points must be between 0 and 100'}, status=400)
                deduction.points = points
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Invalid points value'}, status=400)
        
        if 'reason' in data:
            deduction.reason = data['reason'].strip()
        
        deduction.save()
        
        log_activity(
            user=user_profile,
            activity_type='deduction_updated',
            details=f'Updated deduction for {deduction.user.full_name} - {deduction.task_description}',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Deduction updated successfully'
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
        deduction = get_object_or_404(AdHocDeduction, id=deduction_id)
        
        # Check permission
        try:
            user_profile = UserProfile.objects.get(email=request.user.email)
            if deduction.created_by != user_profile and user_profile.role != 'admin':
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        log_activity(
            user=user_profile,
            activity_type='deduction_deleted',
            details=f'Deleted deduction for {deduction.user.full_name} - {deduction.task_description}',
            request=request
        )
        
        deduction.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Deduction deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def logged_exceptions(request):
    """
    Logged Exceptions page for supervisor - shows all submitted reports from all users.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'supervisor' and user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    # Get filter parameters
    type_filter = request.GET.get('type', 'all')
    status_filter = request.GET.get('status', 'all')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    search_query = request.GET.get('search', '')
    
    # Base queryset - get ALL reports that have been submitted (not just members)
    # This includes reports from members, supervisors, and admins
    exceptions = Report.objects.exclude(
        status__in=['assigned', 'in_progress']
    ).order_by('-created_at')
    
    # Apply type filter
    if type_filter != 'all':
        exceptions = exceptions.filter(report_type=type_filter)
    
    # Apply status filter
    if status_filter != 'all':
        exceptions = exceptions.filter(status=status_filter)
    
    # Apply date filters
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            exceptions = exceptions.filter(created_at__date__gte=start_date_obj)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            exceptions = exceptions.filter(created_at__date__lte=end_date_obj)
        except ValueError:
            pass
    
    # Apply search filter
    if search_query:
        exceptions = exceptions.filter(
            Q(report_type__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(created_by__full_name__icontains=search_query) |
            Q(created_by__email__icontains=search_query)
        )
    
    # Get unique report types for filter dropdown - from ALL reports
    report_types = Report.objects.exclude(
        status__in=['assigned', 'in_progress']
    ).values_list('report_type', flat=True).distinct()
    
    context = {
        'user_profile': user_profile,
        'exceptions': exceptions,
        'report_types': report_types,
        'type_filter': type_filter,
        'status_filter': status_filter,
        'start_date': start_date,
        'end_date': end_date,
        'search_query': search_query,
    }
    
    return render(request, 'control_dashboard/logged.html', context)


@login_required
def supervisor_checklist(request):
    """
    Supervisor Checklist view - shows team members' checklist completion status.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'supervisor' and user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    # Get all team members (members under this supervisor)
    # For now, get all active members
    team_members = UserProfile.objects.filter(
        role='member',
        status='active'
    ).order_by('full_name')
    
    # Get all active checklists
    all_checklists = Checklist.objects.filter(is_active=True)
    
    # Calculate completion data for each user
    user_completion_data = []
    total_users = team_members.count()
    total_completed = 0
    total_completion_rate = 0
    
    for member in team_members:
        # Get checklists assigned to this member
        assigned_checklists = all_checklists.filter(
            models.Q(assigned_users=member) |
            models.Q(assignment_target='all') |
            models.Q(assignment_target=member.position)
        ).distinct()
        
        total_assigned = assigned_checklists.count()
        
        # Get completed checklists (logs) for this user
        completed_checklists = ChecklistLog.objects.filter(
            user=member,
            checklist__in=assigned_checklists
        ).values_list('checklist_id', flat=True).distinct().count()
        
        # Calculate completion rate
        if total_assigned > 0:
            completion_rate = int((completed_checklists / total_assigned) * 100)
        else:
            completion_rate = 0
        
        # Determine status
        if completion_rate >= 90:
            status = 'success'
            status_text = 'Excellent'
        elif completion_rate >= 70:
            status = 'warning'
            status_text = 'Good'
        elif completion_rate >= 40:
            status = 'warning'
            status_text = 'In Progress'
        else:
            status = 'danger'
            status_text = 'Needs Improvement'
        
        total_completed += completed_checklists
        if total_assigned > 0:
            total_completion_rate += completion_rate
        
        user_completion_data.append({
            'user': member,
            'total_checklists': total_assigned,
            'completed_checklists': completed_checklists,
            'completion_rate': completion_rate,
            'status': status,
            'status_text': status_text,
        })
    
    # Calculate average completion
    if total_users > 0 and sum(d['total_checklists'] for d in user_completion_data) > 0:
        avg_completion = int(total_completion_rate / total_users)
    else:
        avg_completion = 0
    
    # Sort by completion rate (highest first)
    user_completion_data.sort(key=lambda x: x['completion_rate'], reverse=True)
    
    context = {
        'user_profile': user_profile,
        'user_completion_data': user_completion_data,
        'total_users': total_users,
        'avg_completion': avg_completion,
        'total_checklists': all_checklists.count(),
        'total_completed': total_completed,
        'all_checklists': all_checklists,
    }
    
    return render(request, 'control_dashboard/checklist-sup.html', context)


@csrf_exempt
@require_http_methods(["GET"])
def api_checklist_detail(request, user_id):
    """
    API endpoint to get detailed checklist progress for a specific user.
    """
    try:
        print(f"=== API CHECKLIST DETAIL CALLED ===")
        print(f"User ID: {user_id}")
        print(f"User: {request.user.email if request.user.is_authenticated else 'Not authenticated'}")
        
        # Get the user
        try:
            user = UserProfile.objects.get(id=user_id)
            print(f"User found: {user.full_name}")
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        # Get all active checklists assigned to this user
        from django.db.models import Q
        
        assigned_checklists = Checklist.objects.filter(
            is_active=True
        ).filter(
            Q(assigned_users=user) |
            Q(assignment_target='all') |
            Q(assignment_target=user.position)
        ).distinct()
        
        print(f"Assigned checklists count: {assigned_checklists.count()}")
        
        # Get checklist logs for this user
        logs = ChecklistLog.objects.filter(
            user=user,
            checklist__in=assigned_checklists
        )
        print(f"Logs count: {logs.count()}")
        
        # Build checklist details
        checklist_details = []
        total_completed = 0
        today = timezone.now().date()
        print(f"Today's date: {today}")
        
        for checklist in assigned_checklists:
            tasks = checklist.tasks.all().order_by('order')
            total_tasks = tasks.count()
            print(f"Checklist: {checklist.name}, Tasks: {total_tasks}")
            
            # Check if this checklist is completed for today
            is_completed_today = logs.filter(
                checklist=checklist,
                log_date=today
            ).exists()
            print(f"  Completed today: {is_completed_today}")
            
            # Get completed tasks count
            completed_tasks = 0
            task_list = []
            for task in tasks:
                # For simplicity, we consider the checklist completed if logged today
                task_completed = is_completed_today
                task_list.append({
                    'description': task.description,
                    'is_completed': task_completed,
                })
                if task_completed:
                    completed_tasks += 1
            
            # Calculate task completion rate
            if total_tasks > 0:
                task_completion_rate = int((completed_tasks / total_tasks) * 100)
            else:
                task_completion_rate = 0
            
            checklist_details.append({
                'id': checklist.id,
                'name': checklist.name,
                'frequency': checklist.get_frequency_display(),
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'task_completion_rate': task_completion_rate,
                'is_completed': is_completed_today,
                'tasks': task_list,
            })
            
            if is_completed_today:
                total_completed += 1
        
        # Calculate overall completion rate
        total_checklists = len(checklist_details)
        if total_checklists > 0:
            completion_rate = int((total_completed / total_checklists) * 100)
        else:
            completion_rate = 0
        
        response_data = {
            'success': True,
            'user': {
                'id': user.id,
                'full_name': user.full_name,
                'email': user.email,
                'position': user.get_position_display() or 'Member',
                'total_checklists': total_checklists,
                'completed_checklists': total_completed,
                'completion_rate': completion_rate,
                'checklist_details': checklist_details,
            }
        }
        print(f"Response data: {response_data}")
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"Error in api_checklist_detail: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def supervisor_activity_logs(request):
    """
    Supervisor Activity Logs page - shows all user activities for monitoring.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'supervisor' and user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    # Get filter parameters
    user_filter = request.GET.get('user', 'all')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    activity_filter = request.GET.get('activity', '')
    
    # Base queryset - get ALL activity logs (not just the current user)
    queryset = ActivityLog.objects.all().select_related('user')
    
    # Apply user filter
    if user_filter != 'all':
        try:
            queryset = queryset.filter(user_id=int(user_filter))
        except ValueError:
            pass
    
    # Apply date filters
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            queryset = queryset.filter(created_at__date__gte=start_date_obj)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            queryset = queryset.filter(created_at__date__lte=end_date_obj)
        except ValueError:
            pass
    
    # Apply activity type filter
    if activity_filter and activity_filter != 'all':
        queryset = queryset.filter(activity_type=activity_filter)
    
    # Get activity logs (limited to 200 most recent)
    activity_logs = queryset.order_by('-created_at')[:200]
    
    # Get all users for filter dropdown
    users = UserProfile.objects.filter(status='active').order_by('full_name')
    
    # Get activity types for filter dropdown
    activity_types = ActivityLog.ACTIVITY_TYPES
    
    context = {
        'user_profile': user_profile,
        'activity_logs': activity_logs,
        'users': users,
        'activity_types': activity_types,
        'user_filter': user_filter,
        'activity_filter': activity_filter,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'control_dashboard/activity-sup.html', context)

@login_required
def activity_logs(request):
    """
    Admin Activity Logs page - shows all user activities for monitoring.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    # Get filter parameters
    user_filter = request.GET.get('user', 'all')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    activity_filter = request.GET.get('activity', '')
    
    # Base queryset - get ALL activity logs
    queryset = ActivityLog.objects.all().select_related('user')
    
    # Apply user filter
    if user_filter != 'all':
        try:
            queryset = queryset.filter(user_id=int(user_filter))
        except ValueError:
            pass
    
    # Apply date filters
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            queryset = queryset.filter(created_at__date__gte=start_date_obj)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            queryset = queryset.filter(created_at__date__lte=end_date_obj)
        except ValueError:
            pass
    
    # Apply activity type filter
    if activity_filter and activity_filter != 'all':
        queryset = queryset.filter(activity_type=activity_filter)
    
    # Calculate stats BEFORE slicing
    unique_users = queryset.values('user_id').distinct().count()
    today = timezone.now().date()
    today_logs = queryset.filter(created_at__date=today).count()
    
    # Get last activity BEFORE slicing
    last_activity_log = queryset.order_by('-created_at').first()
    last_activity = last_activity_log.created_at.strftime('%b %d, %Y %H:%M') if last_activity_log else None
    
    # Get activity logs (slice after stats)
    activity_logs = queryset.order_by('-created_at')[:200]
    
    # Get all users for filter dropdown
    users = UserProfile.objects.filter(status='active').order_by('full_name')
    
    # Get activity types for filter dropdown
    activity_types = ActivityLog.ACTIVITY_TYPES
    
    context = {
        'user_profile': user_profile,
        'activity_logs': activity_logs,
        'users': users,
        'activity_types': activity_types,
        'user_filter': user_filter,
        'activity_filter': activity_filter,
        'start_date': start_date,
        'end_date': end_date,
        'unique_users': unique_users,
        'today_logs': today_logs,
        'last_activity': last_activity,
    }
    
    return render(request, 'control_dashboard/activity.html', context)