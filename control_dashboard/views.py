# control_dashboard/views.py

from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.models import User as DjangoUser
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required
import json
from datetime import datetime, timedelta
from django.utils import timezone
import re

from .models import (
    UserProfile, 
    Report,
    Checklist,
    ChecklistTask,
    ChecklistLog,  
    ReportSubmission,
    ActivityLog,
    AdHocDeduction,
    Branch,
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


def get_or_create_django_user(email, username=None, full_name=None):
    """
    Get or create a Django User from email.
    """
    try:
        django_user = DjangoUser.objects.get(email=email)
        return django_user
    except DjangoUser.DoesNotExist:
        if not username:
            username = email.split('@')[0]
            username = re.sub(r'[^a-zA-Z0-9._]', '', username).lower()
            
            original_username = username
            counter = 1
            while DjangoUser.objects.filter(username=username).exists():
                username = f"{original_username}{counter}"
                counter += 1
        
        django_user = DjangoUser.objects.create_user(
            username=username,
            email=email,
            password='defaultpassword123'
        )
        
        if full_name:
            name_parts = full_name.split(' ', 1)
            django_user.first_name = name_parts[0]
            django_user.last_name = name_parts[1] if len(name_parts) > 1 else ''
            django_user.save()
        
        return django_user


# ==================== LOGIN VIEWS ====================

def landing_page(request):
    if request.user.is_authenticated:
        return redirect_dashboard(request.user)
    return render(request, 'control_dashboard/index.html')


def logout_view(request):
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
    try:
        data = json.loads(request.body)
        login_input = data.get('email', '').strip()
        raw_input = data.get('raw_input', '').strip()
        
        if not login_input:
            return JsonResponse({
                'success': False,
                'error': 'Username or email is required'
            }, status=400)
        
        print(f"\n=== LOGIN ATTEMPT ===")
        print(f"Login Input: '{login_input}'")
        
        user_profile = None
        found_by = None
        
        try:
            user_profile = UserProfile.objects.get(email__iexact=login_input)
            found_by = "email"
            print(f"✅ Found by email: {user_profile.email}")
        except UserProfile.DoesNotExist:
            print(f"❌ Not found by email: '{login_input}'")
        
        if not user_profile:
            username_to_check = login_input.split('@')[0] if '@' in login_input else login_input
            try:
                user_profile = UserProfile.objects.get(username__iexact=username_to_check)
                found_by = "username"
                print(f"✅ Found by username: '{user_profile.username}'")
            except UserProfile.DoesNotExist:
                print(f"❌ Not found by username: '{username_to_check}'")
        
        if not user_profile and '@' not in login_input:
            domains = ['@omnisbic.com.gh', '@omnisbic.com']
            for domain in domains:
                try:
                    user_profile = UserProfile.objects.get(email__iexact=login_input + domain)
                    found_by = f"email with domain {domain}"
                    print(f"✅ Found by {found_by}: {user_profile.email}")
                    break
                except UserProfile.DoesNotExist:
                    print(f"❌ Not found: {login_input + domain}")
                    continue
        
        if not user_profile:
            print("❌ NO USER FOUND!")
            return JsonResponse({
                'success': False,
                'error': f'No account found for "{raw_input or login_input}". Please check your username or contact your administrator.'
            }, status=404)
        
        print(f"\n=== USER FOUND IN UserProfile ===")
        print(f"Found by: {found_by}")
        print(f"ID: {user_profile.id}")
        print(f"Username: '{user_profile.username}'")
        print(f"Email: '{user_profile.email}'")
        print(f"Full Name: '{user_profile.full_name}'")
        print(f"Role: '{user_profile.role}'")
        print(f"Status: '{user_profile.status}'")
        
        if user_profile.status != 'active':
            return JsonResponse({
                'success': False,
                'error': 'Your account is inactive. Please contact support.'
            }, status=403)
        
        django_user = None
        
        try:
            django_user = DjangoUser.objects.get(email=user_profile.email)
            print(f"✅ Found existing Django user by email: {django_user.username}")
        except DjangoUser.DoesNotExist:
            print(f"❌ No Django user found by email: {user_profile.email}")
        
        if not django_user and user_profile.username:
            try:
                django_user = DjangoUser.objects.get(username=user_profile.username)
                print(f"✅ Found existing Django user by username: {django_user.username}")
            except DjangoUser.DoesNotExist:
                print(f"❌ No Django user found by username: {user_profile.username}")
        
        if not django_user:
            print("🔄 Creating new Django user...")
            
            django_username = user_profile.username or user_profile.email.split('@')[0]
            
            original_username = django_username
            counter = 1
            while DjangoUser.objects.filter(username=django_username).exists():
                django_username = f"{original_username}{counter}"
                counter += 1
            
            django_user = DjangoUser.objects.create_user(
                username=django_username,
                email=user_profile.email,
                password='defaultpassword123'
            )
            
            if user_profile.full_name:
                name_parts = user_profile.full_name.split(' ', 1)
                django_user.first_name = name_parts[0]
                django_user.last_name = name_parts[1] if len(name_parts) > 1 else ''
                django_user.save()
            
            print(f"✅ Created Django user: {django_user.username}")
        
        if django_user.email != user_profile.email:
            django_user.email = user_profile.email
            django_user.save()
            print(f"✅ Updated Django user email to: {django_user.email}")
        
        if user_profile.username and django_user.username != user_profile.username:
            if not DjangoUser.objects.filter(username=user_profile.username).exclude(id=django_user.id).exists():
                django_user.username = user_profile.username
                django_user.save()
                print(f"✅ Updated Django user username to: {django_user.username}")
        
        auth_login(request, django_user)
        
        log_activity(
            user=user_profile,
            activity_type='login',
            details=f'User {user_profile.email} logged in via {raw_input or login_input}',
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
                'username': user_profile.username,
                'full_name': user_profile.full_name,
                'role': user_profile.role,
                'position': user_profile.position
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Login error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_user_profile_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'authenticated': False}, status=401)
    
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        return JsonResponse({
            'authenticated': True,
            'user': {
                'id': user_profile.id,
                'email': user_profile.email,
                'username': user_profile.username,
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
                'username': request.user.username,
                'full_name': request.user.get_full_name() or request.user.username,
                'role': 'member',
                'position': 'member'
            }
        })


# ==================== ADMIN VIEWS ====================

@login_required
def admin_page(request):
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    users = UserProfile.objects.all().order_by('full_name')
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
        
        django_user = get_or_create_django_user(
            email=email.lower(),
            username=user.username,
            full_name=full_name
        )
        
        log_activity(
            user=user,
            activity_type='user_created',
            details=f'User {email} was created with role {user.get_role_display()} (username: {user.username})',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': f'User created successfully. Username: {user.username}',
            'user_id': user.id,
            'username': user.username
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def api_edit_user(request, user_id):
    try:
        user = get_object_or_404(UserProfile, id=user_id)
        data = json.loads(request.body)
        
        changes = []
        old_email = user.email
        old_username = user.username
        
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
        
        if 'username' in data and data['username'].strip():
            new_username = data['username'].strip()
            if new_username != user.username:
                if UserProfile.objects.filter(username=new_username).exclude(id=user_id).exists():
                    return JsonResponse({'success': False, 'error': 'Username already in use'}, status=400)
                changes.append(f'Username changed from {user.username} to {new_username}')
                user.username = new_username
        
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
        
        try:
            django_user = DjangoUser.objects.get(username=old_username)
            if user.username and user.username != old_username:
                django_user.username = user.username
            if user.email and user.email != old_email:
                django_user.email = user.email
            if user.full_name:
                name_parts = user.full_name.split(' ', 1)
                django_user.first_name = name_parts[0]
                django_user.last_name = name_parts[1] if len(name_parts) > 1 else ''
            django_user.save()
        except DjangoUser.DoesNotExist:
            get_or_create_django_user(
                email=user.email,
                username=user.username,
                full_name=user.full_name
            )
        
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
    try:
        user = get_object_or_404(UserProfile, id=user_id)
        email = user.email
        username = user.username
        
        try:
            django_user = DjangoUser.objects.get(username=username)
            django_user.delete()
        except DjangoUser.DoesNotExist:
            pass
        
        log_activity(
            user=user,
            activity_type='user_deleted',
            details=f'User {email} (username: {username}) was deleted',
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


# ==================== REPORT CREATION & CENTER VIEWS ====================

@login_required
def report_creation(request):
    """
    Report Creation view for creating new reports.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    users = UserProfile.objects.filter(role='member', status='active').order_by('full_name')
    
    context = {
        'user_profile': user_profile,
        'users': users,
    }
    
    return render(request, 'control_dashboard/reportcreation.html', context)


@login_required
def report_center(request):
    """
    Report Center view for managing existing reports.
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    reports = Report.objects.all().order_by('-created_at')
    
    user_filter = request.GET.get('user', '')
    if user_filter and user_filter != 'all':
        reports = reports.filter(assigned_to__id=user_filter)
    
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
    try:
        if not request.body:
            return JsonResponse({'success': False, 'error': 'Empty request payload'}, status=400)
            
        data = json.loads(request.body)
        print(f"Create report data: {data}")
        
        report_type = data.get('report_type', '').strip()
        frequency = data.get('frequency', 'one-off')
        description = data.get('description', '').strip()
        deadline_date = data.get('deadline_date')
        deadline_time = data.get('deadline_time')
        assigned_users = data.get('assigned_users', [])
        is_assigned_to_all = data.get('is_assigned_to_all', False)
        
        if not report_type:
            return JsonResponse({'success': False, 'error': 'Report type is required'}, status=400)
        
        try:
            created_by = UserProfile.objects.get(email=request.user.email)
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        if not deadline_date or str(deadline_date).strip() == '':
            deadline_date = None
        if not deadline_time or str(deadline_time).strip() == '':
            deadline_time = None
        
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
        
        if is_assigned_to_all:
            all_members = UserProfile.objects.filter(role='member', status='active')
            report.assigned_to.set(all_members)
        elif assigned_users:
            active_members = UserProfile.objects.filter(id__in=assigned_users, status='active')
            report.assigned_to.set(active_members)
        
        log_activity(
            user=created_by,
            activity_type='report_created',
            details=f'Created report: {report_type}',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Report created successfully',
            'report_id': report.id
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Error creating report: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_get_report(request, report_id):
    try:
        report = get_object_or_404(Report, id=report_id)
        
        try:
            user_profile = UserProfile.objects.get(email=request.user.email)
            if report.created_by != user_profile and user_profile.role != 'admin':
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
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
        print(f"Error getting report: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def api_edit_report(request, report_id):
    try:
        report = get_object_or_404(Report, id=report_id)
        
        try:
            user_profile = UserProfile.objects.get(email=request.user.email)
            if report.created_by != user_profile and user_profile.role != 'admin':
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        if not request.body:
            return JsonResponse({'success': False, 'error': 'Empty request payload'}, status=400)
            
        data = json.loads(request.body)
        print(f"Edit report data: {data}")
        
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
            report.assigned_to.set(UserProfile.objects.filter(id__in=assigned_users, status='active'))
            changes.append('Assigned user profiles refreshed')
            
        report.save()
        
        if changes:
            log_activity(
                user=user_profile,
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
        print(f"Error editing report: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_delete_report(request, report_id):
    try:
        report = get_object_or_404(Report, id=report_id)
        
        try:
            user_profile = UserProfile.objects.get(email=request.user.email)
            if report.created_by != user_profile and user_profile.role != 'admin':
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
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
        print(f"Error deleting report: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==================== CHECKLIST VIEWS ====================

@login_required
def checklist_builder(request):
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    from .models import Checklist, ChecklistTask
    
    checklists = Checklist.objects.all().order_by('-created_at')
    users = UserProfile.objects.filter(status='active').order_by('full_name')
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


@login_required
def checklist_list(request):
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    from .models import Checklist
    
    checklists = Checklist.objects.all().prefetch_related('tasks', 'assigned_users').order_by('-created_at')
    users = UserProfile.objects.filter(status='active').order_by('full_name')
    
    context = {
        'user_profile': user_profile,
        'checklists': checklists,
        'users': users,
        'today': timezone.now(),
    }
    
    return render(request, 'control_dashboard/checklist_list.html', context)


# ==================== API - CHECKLIST MANAGEMENT ====================

@require_http_methods(["POST"])
def api_create_checklist(request):
    try:
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
        
        created_by = None
        if request.user and request.user.is_authenticated:
            created_by = UserProfile.objects.filter(email=request.user.email).first()
        
        if not created_by:
            created_by = UserProfile.objects.first()
            
        if not created_by:
            return JsonResponse({'success': False, 'error': 'No active UserProfile records found to assign ownership'}, status=400)
        
        checklist = Checklist.objects.create(
            name=name,
            description=description,
            frequency=frequency,
            assignment_target=assignment_target,
            created_by=created_by,
            is_active=True
        )
        
        if assignment_target == 'specific':
            active_users = UserProfile.objects.filter(id__in=assigned_users_ids, status='active')
            checklist.assigned_users.set(active_users)
        elif assignment_target == 'cc':
            checklist.assigned_users.set(UserProfile.objects.filter(position='cc', status='active'))
        elif assignment_target == 'hc':
            checklist.assigned_users.set(UserProfile.objects.filter(position='hc', status='active'))
        elif assignment_target == 'all':
            checklist.assigned_users.set(UserProfile.objects.filter(status='active'))
        
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
    try:
        checklist = get_object_or_404(Checklist, id=checklist_id)
        if not request.body:
            return JsonResponse({'success': False, 'error': 'Empty patch payload parameters'}, status=400)
            
        data = json.loads(request.body)
        
        if 'name' in data:
            checklist.name = data['name'].strip()
        if 'frequency' in data:
            checklist.frequency = data['frequency']
        if 'assignment_target' in data:
            checklist.assignment_target = data['assignment_target']
        checklist.save()
        
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
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(
            email=request.user.email,
            full_name=request.user.get_full_name() or request.user.username,
            role='member',
            position='member',
            status='active'
        )
    
    from datetime import date, timedelta
    today = timezone.now().date()
    weekday = today.weekday()
    
    if weekday >= 4:
        days_since_friday = weekday - 4
        week_start = today - timedelta(days=days_since_friday)
    else:
        days_since_friday = weekday + 3
        week_start = today - timedelta(days=days_since_friday)
    
    week_end = week_start + timedelta(days=6)
    
    from .models import Checklist, ChecklistLog
    
    # Get all user checklists
    user_checklists = Checklist.objects.filter(
        is_active=True
    ).filter(
        Q(assigned_users=user_profile) |
        Q(assignment_target='all') |
        Q(assignment_target=user_profile.position)
    ).distinct()
    
    # Get checklists for display (show all, sorted by frequency priority)
    display_checklists = user_checklists.order_by('frequency')[:10]
    
    # Calculate month-to-date and year-to-date progress
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    
    # Get all logs for the user
    all_logs = ChecklistLog.objects.filter(user=user_profile)
    
    # Month progress calculation
    month_expected = 0
    month_actual = 0
    year_expected = 0
    year_actual = 0
    total_checklists_completed = 0
    
    # Calculate progress for each checklist
    display_checklists_with_progress = []
    frequency_counts = {}
    
    for checklist in user_checklists:
        # Get frequency count for summary
        freq = checklist.frequency
        frequency_counts[freq] = frequency_counts.get(freq, 0) + 1
        
        # Month progress for this checklist - using the new methods
        checklist_month_expected = checklist.get_monthly_expected(user_profile)
        checklist_month_actual = checklist.get_monthly_actual(user_profile)
        
        # Year progress for this checklist
        checklist_year_expected = checklist.get_year_to_date_expected(user_profile)
        checklist_year_actual = checklist.get_year_to_date_actual(user_profile)
        
        month_expected += checklist_month_expected
        month_actual += checklist_month_actual
        year_expected += checklist_year_expected
        year_actual += checklist_year_actual
        
        # Calculate next due date
        next_due = checklist.get_next_due_date(user_profile)
        
        month_progress = int((checklist_month_actual / checklist_month_expected * 100)) if checklist_month_expected > 0 else 0
        year_progress = int((checklist_year_actual / checklist_year_expected * 100)) if checklist_year_expected > 0 else 0
        
        # Determine status
        if month_progress >= 100:
            status = 'completed'
            total_checklists_completed += 1
        elif month_progress >= 70:
            status = 'on_track'
        elif month_progress >= 40:
            status = 'in_progress'
        else:
            status = 'at_risk'
        
        # Add progress data to checklist object for template
        checklist.month_progress = month_progress
        checklist.year_progress = year_progress
        checklist.month_expected = checklist_month_expected
        checklist.month_actual = checklist_month_actual
        checklist.year_expected = checklist_year_expected
        checklist.year_actual = checklist_year_actual
        checklist.status = status
        checklist.next_due_date = next_due.strftime('%b %d, %Y') if next_due else None
        
        # Only add to display list if it's in the display list
        if checklist in display_checklists:
            display_checklists_with_progress.append(checklist)
    
    # Build frequency summary
    freq_labels = {
        'daily': 'Daily',
        'weekly': 'Weekly',
        'monthly': 'Monthly',
        'quarterly': 'Quarterly',
        'bi-annual': 'Bi-Annual',
        'one-off': 'One-Off'
    }
    freq_parts = []
    for freq, count in frequency_counts.items():
        if count > 0:
            freq_parts.append(f"{count} {freq_labels.get(freq, freq)}")
    frequency_summary = ', '.join(freq_parts) if freq_parts else 'No checklists'
    
    # Overall progress (capped at 100%)
    overall_month_progress = int((month_actual / month_expected * 100)) if month_expected > 0 else 0
    overall_year_progress = int((year_actual / year_expected * 100)) if year_expected > 0 else 0
    month_total = month_expected
    year_total = year_expected
    
    # Weekly completion rate
    weekly_logs = all_logs.filter(log_date__gte=week_start, log_date__lte=today)
    weekly_checklists = user_checklists.count()
    
    # Count weekdays in the week so far
    weekdays_count = 0
    current = week_start
    while current <= today:
        if current.weekday() < 5:
            weekdays_count += 1
        current += timedelta(days=1)
    
    weekly_expected = weekly_checklists * weekdays_count if weekly_checklists > 0 else 0
    weekly_completion_rate = int((weekly_logs.count() / weekly_expected * 100)) if weekly_expected > 0 else 0
    
    # Assignments count
    assigned_this_week = user_checklists.filter(
        created_at__date__gte=week_start,
        created_at__date__lte=week_end
    ).count()
    
    # Exceptions captured this week
    exceptions_this_week = Report.objects.filter(
        created_by=user_profile,
        created_at__date__gte=week_start,
        created_at__date__lte=week_end
    ).count()
    
    # Pending submissions
    pending_submissions = Report.objects.filter(
        Q(assigned_to=user_profile) |
        Q(created_by=user_profile) |
        Q(is_assigned_to_all=True)
    ).filter(
        Q(status='submitted') | Q(status='draft')
    ).distinct().count()
    
    # Total logged days
    total_logged_days = all_logs.values('log_date').distinct().count()
    
    # Sort display checklists by month progress (ascending) to show items needing attention first
    display_checklists_with_progress.sort(key=lambda x: x.month_progress)
    
    context = {
        'user_profile': user_profile,
        'today': today,
        'week_start': week_start,
        'week_end': week_end,
        'assigned_this_week': assigned_this_week,
        'exceptions_this_week': exceptions_this_week,
        'pending_submissions': pending_submissions,
        'daily_checklists': display_checklists_with_progress[:5],  # Show top 5
        'all_checklists_count': user_checklists.count(),
        'total_checklists_completed': total_checklists_completed,
        
        # Progress metrics
        'overall_month_progress': overall_month_progress,
        'overall_year_progress': overall_year_progress,
        'month_completed': month_actual,
        'month_total': month_total,
        'year_completed': year_actual,
        'year_total': year_total,
        'total_logged_days': total_logged_days,
        'weekly_completion_rate': weekly_completion_rate,
        'frequency_summary': frequency_summary,
    }
    
    return render(request, 'control_dashboard/memberboard.html', context)

# ==================== SUBMIT REPORT VIEWS ====================

@login_required
def drafts_page(request):
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except UserProfile.DoesNotExist:
        return redirect('control_dashboard:member_dashboard')
    
    assigned_reports = Report.objects.filter(
        Q(assigned_to=user_profile) |
        Q(is_assigned_to_all=True)
    ).filter(
        status__in=['assigned', 'in_progress']
    ).distinct().order_by('-created_at')
    
    report_types = assigned_reports.values_list('report_type', flat=True).distinct()
    
    context = {
        'user_profile': user_profile,
        'today': timezone.now(),
        'report_types': list(report_types),
        'assigned_reports': assigned_reports,
    }
    return render(request, 'control_dashboard/draft.html', context)


@login_required
def reports_page(request):
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except UserProfile.DoesNotExist:
        return redirect('control_dashboard:member_dashboard')
    
    from .models import ReportSchedule
    
    reports = Report.objects.filter(
        created_by=user_profile
    ).filter(
        Q(status='submitted') | Q(status='completed') | Q(status='draft')
    ).order_by('-created_at')
    
    report_types = reports.values_list('report_type', flat=True).distinct()
    branches = Branch.objects.filter(is_active=True).order_by('name')
    
    # Add schedule info to each report
    for report in reports:
        schedule = ReportSchedule.objects.filter(report=report, is_active=True).first()
        report.has_schedule = bool(schedule)
        if schedule:
            report.next_due_date = schedule.next_due_date
            report.schedule_frequency = schedule.get_frequency_display()
    
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
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except UserProfile.DoesNotExist:
        return redirect('control_dashboard:member_dashboard')
    
    # Get distinct report types from reports created by the user
    report_types = Report.objects.filter(
        created_by=user_profile
    ).values_list('report_type', flat=True).distinct().order_by('report_type')
    
    # Convert to list
    report_types = list(report_types)
    
    # If no report types exist, add some defaults
    if not report_types:
        report_types = [
            'Daily Control Report',
            'Monthly Reconciliation',
            'Exception Report',
            'Compliance Check',
            'Audit Report',
            'Risk Assessment',
            'Incident Report',
            'Performance Report'
        ]
    
    # Get all users for the "To" dropdown
    all_users = UserProfile.objects.filter(status='active').order_by('full_name')
    
    # Get assigned exceptions for the current user
    assigned_exceptions = Report.objects.filter(
        Q(assigned_to=user_profile) |
        Q(created_by=user_profile) |
        Q(is_assigned_to_all=True)
    ).filter(
        Q(status='submitted') | Q(status='draft') | Q(status='rejected')
    ).distinct().order_by('-updated_at')
    
    # Get categories from exceptions
    categories = set()
    for exception in assigned_exceptions:
        if exception.data:
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
    
    # Build exceptions data
    exceptions_data = []
    for exception in assigned_exceptions:
        exception_data = exception.data or {}
        unit = (
            exception_data.get('unit') or 
            exception_data.get('branch') or 
            exception_data.get('BRANCH') or 
            exception_data.get('DEPARTMENT') or
            exception_data.get('BRANCH/UNIT') or
            exception_data.get('branch_unit') or
            'N/A'
        )
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
    
    # Get distinct report types for the dropdown (from exceptions, not all reports)
    exception_report_types = list(set([e['report_type'] for e in exceptions_data]))
    
    context = {
        'user_profile': user_profile,
        'today': timezone.now(),
        'all_users': all_users,
        'report_types': exception_report_types or report_types,  # Use exception types, fallback to defaults
        'assigned_report_types': exception_report_types,
        'categories_list': categories_list,
        'exceptions_json': json.dumps(exceptions_data, default=str),
        'exceptions': exceptions_data,
        'email_recipients': all_users,
        'user_data': {
            'name': user_profile.full_name,
            'email': user_profile.email,
            'username': user_profile.username,
            'department': user_profile.position or 'General'
        },
    }
    
    return render(request, 'control_dashboard/submit.html', context)


# ==================== API - IMPORT/EXPORT EXCEL ====================

@csrf_exempt
@require_http_methods(["POST"])
def api_import_excel(request):
    """
    API endpoint to import Excel data and return preview
    """
    try:
        data = json.loads(request.body)
        file_data = data.get('file_data', [])
        file_name = data.get('file_name', 'uploaded_file.xlsx')
        report_type = data.get('report_type', '')
        
        if not file_data or len(file_data) == 0:
            return JsonResponse({
                'success': False,
                'error': 'No data found in the file'
            }, status=400)
        
        # First row is headers
        headers = file_data[0] if file_data else []
        # Rest are data rows
        rows = file_data[1:] if len(file_data) > 1 else []
        
        # Convert to list of dictionaries
        parsed_data = []
        for row in rows:
            if row and any(cell for cell in row):  # Skip empty rows
                row_dict = {}
                for i, header in enumerate(headers):
                    if i < len(row):
                        row_dict[header] = row[i] if row[i] is not None else ''
                    else:
                        row_dict[header] = ''
                parsed_data.append(row_dict)
        
        # Store in session for later use
        request.session['excel_import_data'] = {
            'headers': headers,
            'data': parsed_data,
            'file_name': file_name,
            'report_type': report_type,
            'row_count': len(parsed_data)
        }
        
        return JsonResponse({
            'success': True,
            'headers': headers,
            'data': parsed_data,
            'row_count': len(parsed_data),
            'message': f'Successfully imported {len(parsed_data)} records'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Error importing Excel: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_save_imported_data(request):
    """
    API endpoint to save imported Excel data to the database
    """
    try:
        data = json.loads(request.body)
        
        # Get data from request
        headers = data.get('headers', [])
        rows_data = data.get('data', [])
        report_type = data.get('report_type', '')
        file_name = data.get('file_name', 'uploaded.xlsx')
        
        if not headers or not rows_data:
            return JsonResponse({
                'success': False,
                'error': 'No data to save. Please import an Excel file first.'
            }, status=400)
        
        if not report_type:
            return JsonResponse({
                'success': False,
                'error': 'Please select a report type.'
            }, status=400)
        
        try:
            user_profile = UserProfile.objects.get(email=request.user.email)
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        # Convert rows to list of dictionaries with proper headers
        normalized_rows = []
        for row in rows_data:
            if isinstance(row, dict):
                # Already a dictionary
                normalized_rows.append(row)
            elif isinstance(row, list):
                # Convert list to dict using headers
                row_dict = {}
                for i, header in enumerate(headers):
                    if i < len(row):
                        row_dict[header] = row[i] if row[i] is not None else ''
                    else:
                        row_dict[header] = ''
                normalized_rows.append(row_dict)
        
        # Create the report with proper data
        report = Report.objects.create(
            report_type=report_type,
            frequency='one-off',
            description=f'Excel Import: {file_name}',
            status='submitted',
            created_by=user_profile,
            data={
                'import_type': 'excel',
                'file_name': file_name,
                'headers': headers,  # Store the actual headers from Excel
                'data': normalized_rows,  # Store as list of dictionaries with actual headers
                'row_count': len(normalized_rows),
                'imported_at': timezone.now().isoformat(),
            }
        )
        
        # Log activity
        log_activity(
            user=user_profile,
            activity_type='report_submitted',
            details=f'Submitted {report_type} with {len(normalized_rows)} records from Excel',
            request=request
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully saved {len(normalized_rows)} records from {file_name}',
            'report_id': report.id,
            'record_count': len(normalized_rows)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Error saving imported data: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def member_checklist(request):
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except UserProfile.DoesNotExist:
        return redirect('control_dashboard:member_dashboard')
    
    from datetime import date, timedelta
    today = timezone.now().date()
    
    user_checklists = Checklist.objects.filter(
        is_active=True
    ).filter(
        Q(assigned_users=user_profile) |
        Q(assignment_target='all') |
        Q(assignment_target=user_profile.position)
    ).distinct().order_by('name')
    
    # Get years for filter
    current_year = timezone.now().year
    years = list(range(current_year - 2, current_year + 1))
    
    checklist_data = []
    for checklist in user_checklists:
        tasks = checklist.tasks.all().order_by('order')
        logs = ChecklistLog.objects.filter(
            checklist=checklist,
            user=user_profile
        ).values_list('log_date', flat=True)
        log_dates = [log.strftime('%Y-%m-%d') for log in logs]
        
        # Calculate progress
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        
        month_expected = checklist.get_expected_occurrences(month_start, today)
        month_actual = ChecklistLog.objects.filter(
            checklist=checklist,
            user=user_profile,
            log_date__gte=month_start,
            log_date__lte=today
        ).count()
        
        year_expected = checklist.get_expected_occurrences(year_start, today)
        year_actual = ChecklistLog.objects.filter(
            checklist=checklist,
            user=user_profile,
            log_date__gte=year_start,
            log_date__lte=today
        ).count()
        
        month_progress = int((month_actual / month_expected * 100)) if month_expected > 0 else 0
        year_progress = int((year_actual / year_expected * 100)) if year_expected > 0 else 0
        
        # Determine status
        if month_progress >= 100:
            status = 'completed'
        elif month_progress >= 70:
            status = 'on_track'
        elif month_progress >= 40:
            status = 'in_progress'
        else:
            status = 'at_risk'
        
        # Calculate next due date
        next_due = checklist.get_next_due_date(user_profile) if hasattr(checklist, 'get_next_due_date') else None
        
        checklist_data.append({
            'id': checklist.id,
            'name': checklist.name,
            'frequency': checklist.frequency,
            'frequency_display': checklist.get_frequency_display(),
            'tasks': [{'description': task.description, 'id': task.id} for task in tasks],
            'logs': log_dates,
            'month_progress': month_progress,
            'year_progress': year_progress,
            'month_expected': month_expected,
            'month_actual': month_actual,
            'year_expected': year_expected,
            'year_actual': year_actual,
            'status': status,
            'frequency_days': checklist.get_frequency_days(),
            'next_due_date': next_due.strftime('%b %d, %Y') if next_due else None,
        })
    
    # Calculate overall progress
    total_month_expected = sum(c['month_expected'] for c in checklist_data)
    total_month_actual = sum(c['month_actual'] for c in checklist_data)
    total_year_expected = sum(c['year_expected'] for c in checklist_data)
    total_year_actual = sum(c['year_actual'] for c in checklist_data)
    
    overall_month_progress = int((total_month_actual / total_month_expected * 100)) if total_month_expected > 0 else 0
    overall_year_progress = int((total_year_actual / total_year_expected * 100)) if total_year_expected > 0 else 0
    
    context = {
        'user_profile': user_profile,
        'checklists': user_checklists,
        'checklist_data': checklist_data,
        'years': years,
        'overall_month_progress': overall_month_progress,
        'overall_year_progress': overall_year_progress,
        'total_checklists': user_checklists.count(),
    }
    
    return render(request, 'control_dashboard/checklist-mem.html', context)


# ==================== API - CHECKLIST LOG ====================

@csrf_exempt
@require_http_methods(["POST"])
def api_log_checklist(request):
    try:
        data = json.loads(request.body)
        
        checklist_id = data.get('checklist_id')
        log_date = data.get('log_date')
        action = data.get('action', 'log')
        
        if not checklist_id:
            return JsonResponse({'success': False, 'error': 'Checklist ID is required'}, status=400)
        
        if not log_date:
            return JsonResponse({'success': False, 'error': 'Log date is required'}, status=400)
        
        try:
            user_profile = UserProfile.objects.get(email=request.user.email)
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        try:
            checklist = Checklist.objects.get(id=checklist_id, is_active=True)
        except Checklist.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Checklist not found'}, status=404)
        
        try:
            date_obj = datetime.strptime(log_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
        
        if action == 'log':
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
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        
        user_checklists = Checklist.objects.filter(
            is_active=True
        ).filter(
            Q(assigned_users=user_profile) |
            Q(assignment_target='all') |
            Q(assignment_target=user_profile.position)
        ).distinct()
        
        total_checklists = user_checklists.count()
        logs = ChecklistLog.objects.filter(user=user_profile)
        total_logs = logs.count()
        
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        weekly_logs = logs.filter(log_date__gte=start_of_week, log_date__lte=end_of_week).count()
        last_7_days = today - timedelta(days=7)
        recent_logs = logs.filter(log_date__gte=last_7_days).count()
        
        daily_checklists = user_checklists.filter(frequency='daily')
        daily_total = daily_checklists.count()
        
        completion_rate = 0
        if daily_total > 0:
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


# ==================== API - SAVE DRAFT ====================

@csrf_exempt
@require_http_methods(["POST"])
def api_save_draft(request):
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
        
        try:
            user_profile = UserProfile.objects.get(email=request.user.email)
            print(f"User Profile: {user_profile}")
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        submission = ReportSubmission.objects.create(
            report_type=report_type,
            template_name=template_name,
            submitted_by=user_profile,
            status='submitted',
            data={
                'form_data': form_data,
                'excel_data': excel_data,
            }
        )
        print(f"Submission created with ID: {submission.id}")
        
        report = Report.objects.create(
            report_type=report_type,
            frequency='one-off',
            description=template_name,
            status='submitted',
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


# ==================== API - DRAFT (GET, EDIT, DELETE) ====================

@csrf_exempt
@require_http_methods(["GET"])
def api_get_draft(request, report_id):
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
        
        data = json.loads(request.body)
        form_data = data.get('form_data', {})
        
        submission_id = report.data.get('submission_id') if isinstance(report.data, dict) else None
        submission = None
        
        if submission_id:
            try:
                submission = ReportSubmission.objects.get(id=submission_id)
                if not isinstance(submission.data, dict):
                    submission.data = {}
                
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

        if not submission:
            submission = ReportSubmission.objects.create(
                report_type=report.report_type,
                template_name=getattr(report, 'description', report.report_type),
                submitted_by=user_profile,
                status='submitted',
                data={'form_data': [form_data]}
            )
        
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
    try:
        lookup_id = int(report_id) if str(report_id).isdigit() else report_id
        report = get_object_or_404(Report, id=lookup_id)
        
        try:
            user_profile = UserProfile.objects.get(email=request.user.email)
            if report.created_by != user_profile and user_profile.role != 'admin':
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User context profile not found'}, status=404)
        
        if isinstance(report.data, dict) and 'submission_id' in report.data:
            submission_id = report.data.get('submission_id')
            if submission_id:
                ReportSubmission.objects.filter(id=submission_id).delete()
        
        report.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Draft and associated data payload permanently removed from database storage.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
def api_get_report_data(request):
    try:
        report_type = request.GET.get('report_type', '')
        
        if not report_type:
            return JsonResponse({'success': False, 'error': 'Report type is required'}, status=400)
        
        user_profile = UserProfile.objects.get(email=request.user.email)
        
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


# ==================== MEMBER ACTIVITY LOGS ====================

@login_required
def member_activity_logs(request):
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except UserProfile.DoesNotExist:
        return redirect('control_dashboard:member_dashboard')
    
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    activity_filter = request.GET.get('activity', '')
    
    queryset = ActivityLog.objects.filter(user=user_profile)
    
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
    
    if activity_filter and activity_filter != 'all':
        queryset = queryset.filter(activity_type=activity_filter)
    
    activity_logs = queryset.order_by('-created_at')[:100]
    
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    
    today_logs = ActivityLog.objects.filter(user=user_profile, created_at__date=today)
    week_logs = ActivityLog.objects.filter(user=user_profile, created_at__date__gte=start_of_week, created_at__date__lte=today)
    month_logs = ActivityLog.objects.filter(user=user_profile, created_at__date__gte=start_of_month, created_at__date__lte=today)
    
    last_activity = ActivityLog.objects.filter(user=user_profile).order_by('-created_at').first()
    last_activity_display = last_activity.created_at.strftime('%b %d, %Y %H:%M') if last_activity else None
    
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


# ==================== API - EXPORT LOGS ====================

@csrf_exempt
@require_http_methods(["GET"])
def api_export_logs(request):
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
    
    user_filter = request.GET.get('user', 'all')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    activity_filter = request.GET.get('activity', '')
    
    queryset = ActivityLog.objects.all().select_related('user')
    
    if user_filter != 'all':
        try:
            queryset = queryset.filter(user_id=int(user_filter))
        except ValueError:
            pass
    
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
    
    if activity_filter and activity_filter != 'all':
        queryset = queryset.filter(activity_type=activity_filter)
    
    logs = queryset.order_by('-created_at')
    
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


# ==================== SUPERVISOR VIEWS (CONTINUED) ====================

@login_required
def team_performance(request):
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'supervisor' and user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    team_members = UserProfile.objects.filter(role='member', status='active').order_by('full_name')
    
    team_data = []
    total_tasks = 0
    total_completed = 0
    
    for member in team_members:
        assigned_checklists = Checklist.objects.filter(assigned_users=member).count()
        completed_checklists = ChecklistLog.objects.filter(user=member).count()
        
        total_tasks += assigned_checklists
        total_completed += completed_checklists
        
        percentage = 0
        if assigned_checklists > 0:
            percentage = int((completed_checklists / assigned_checklists) * 100)
        
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
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'supervisor' and user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    user_filter = request.GET.get('user', 'all')
    category_filter = request.GET.get('category', 'all')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    reports = Report.objects.filter(status='submitted')
    
    if user_filter != 'all':
        try:
            reports = reports.filter(created_by_id=int(user_filter))
        except ValueError:
            pass
    
    if category_filter != 'all':
        reports = reports.filter(report_type=category_filter)
    
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
    
    users = UserProfile.objects.filter(role='member', status='active').order_by('full_name')
    categories = Report.objects.values_list('report_type', flat=True).distinct()
    
    report_data = []
    total_reports = 0
    approved_count = 0
    pending_count = 0
    rejected_count = 0
    
    for report in reports:
        total_reports += 1
        
        if report.status == 'approved':
            approved_count += 1
        elif report.status == 'submitted':
            pending_count += 1
        elif report.status == 'rejected':
            rejected_count += 1
        
        manual_deduction = 0
        if report.data and isinstance(report.data, dict):
            manual_deduction = report.data.get('manual_deduction', 0)
        
        final_score = max(0, 100 - manual_deduction)
        
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
            'status_display': report.get_status_display(),
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
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'supervisor' and user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    user_filter = request.GET.get('user', 'all')
    
    users = UserProfile.objects.filter(role='member', status='active').order_by('full_name')
    
    try:
        deductions = AdHocDeduction.objects.select_related('user', 'created_by').all().order_by('-created_at')
        
        if user_filter != 'all':
            try:
                deductions = deductions.filter(user_id=int(user_filter))
            except ValueError:
                pass
        
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
        
        deduction = AdHocDeduction.objects.create(
            user=user,
            task_description=task_description,
            points=points,
            reason=reason,
            created_by=created_by
        )
        
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
    try:
        deduction = get_object_or_404(AdHocDeduction, id=deduction_id)
        
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
    try:
        deduction = get_object_or_404(AdHocDeduction, id=deduction_id)
        
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
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'supervisor' and user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    type_filter = request.GET.get('type', 'all')
    status_filter = request.GET.get('status', 'all')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    search_query = request.GET.get('search', '')
    
    exceptions = Report.objects.exclude(
        status__in=['assigned', 'in_progress']
    ).order_by('-created_at')
    
    if type_filter != 'all':
        exceptions = exceptions.filter(report_type=type_filter)
    
    if status_filter != 'all':
        exceptions = exceptions.filter(status=status_filter)
    
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
    
    if search_query:
        exceptions = exceptions.filter(
            Q(report_type__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(created_by__full_name__icontains=search_query) |
            Q(created_by__email__icontains=search_query)
        )
    
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
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'supervisor' and user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    team_members = UserProfile.objects.filter(role='member', status='active').order_by('full_name')
    all_checklists = Checklist.objects.filter(is_active=True)
    
    user_completion_data = []
    total_users = team_members.count()
    total_completed = 0
    total_completion_rate = 0
    
    for member in team_members:
        assigned_checklists = all_checklists.filter(
            Q(assigned_users=member) |
            Q(assignment_target='all') |
            Q(assignment_target=member.position)
        ).distinct()
        
        total_assigned = assigned_checklists.count()
        
        completed_checklists = ChecklistLog.objects.filter(
            user=member,
            checklist__in=assigned_checklists
        ).values_list('checklist_id', flat=True).distinct().count()
        
        if total_assigned > 0:
            completion_rate = int((completed_checklists / total_assigned) * 100)
        else:
            completion_rate = 0
        
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
    
    if total_users > 0 and sum(d['total_checklists'] for d in user_completion_data) > 0:
        avg_completion = int(total_completion_rate / total_users)
    else:
        avg_completion = 0
    
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
    try:
        print(f"=== API CHECKLIST DETAIL CALLED ===")
        print(f"User ID: {user_id}")
        print(f"User: {request.user.email if request.user.is_authenticated else 'Not authenticated'}")
        
        try:
            user = UserProfile.objects.get(id=user_id)
            print(f"User found: {user.full_name}")
        except UserProfile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        assigned_checklists = Checklist.objects.filter(
            is_active=True
        ).filter(
            Q(assigned_users=user) |
            Q(assignment_target='all') |
            Q(assignment_target=user.position)
        ).distinct()
        
        print(f"Assigned checklists count: {assigned_checklists.count()}")
        
        logs = ChecklistLog.objects.filter(
            user=user,
            checklist__in=assigned_checklists
        )
        print(f"Logs count: {logs.count()}")
        
        checklist_details = []
        total_completed = 0
        today = timezone.now().date()
        print(f"Today's date: {today}")
        
        for checklist in assigned_checklists:
            tasks = checklist.tasks.all().order_by('order')
            total_tasks = tasks.count()
            print(f"Checklist: {checklist.name}, Tasks: {total_tasks}")
            
            is_completed_today = logs.filter(
                checklist=checklist,
                log_date=today
            ).exists()
            print(f"  Completed today: {is_completed_today}")
            
            completed_tasks = 0
            task_list = []
            for task in tasks:
                task_completed = is_completed_today
                task_list.append({
                    'description': task.description,
                    'is_completed': task_completed,
                })
                if task_completed:
                    completed_tasks += 1
            
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
                'username': user.username,
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
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'supervisor' and user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    user_filter = request.GET.get('user', 'all')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    activity_filter = request.GET.get('activity', '')
    
    queryset = ActivityLog.objects.all().select_related('user')
    
    if user_filter != 'all':
        try:
            queryset = queryset.filter(user_id=int(user_filter))
        except ValueError:
            pass
    
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
    
    if activity_filter and activity_filter != 'all':
        queryset = queryset.filter(activity_type=activity_filter)
    
    activity_logs = queryset.order_by('-created_at')[:200]
    
    users = UserProfile.objects.filter(status='active').order_by('full_name')
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
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    user_filter = request.GET.get('user', 'all')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    activity_filter = request.GET.get('activity', '')
    
    queryset = ActivityLog.objects.all().select_related('user')
    
    if user_filter != 'all':
        try:
            queryset = queryset.filter(user_id=int(user_filter))
        except ValueError:
            pass
    
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
    
    if activity_filter and activity_filter != 'all':
        queryset = queryset.filter(activity_type=activity_filter)
    
    unique_users = queryset.values('user_id').distinct().count()
    today = timezone.now().date()
    today_logs = queryset.filter(created_at__date=today).count()
    
    activity_breakdown = queryset.values('activity_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    user_activity_summary = queryset.values(
        'user__full_name', 'user__email', 'user__role'
    ).annotate(
        total_activities=Count('id')
    ).order_by('-total_activities')[:10]
    
    last_activity_log = queryset.order_by('-created_at').first()
    last_activity = last_activity_log.created_at.strftime('%b %d, %Y %H:%M') if last_activity_log else None
    
    activity_logs = queryset.order_by('-created_at')[:200]
    
    users = UserProfile.objects.filter(status='active').order_by('full_name')
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
        'activity_breakdown': activity_breakdown,
        'user_activity_summary': user_activity_summary,
    }
    
    return render(request, 'control_dashboard/activity.html', context)


# ==================== ANALYTICS DASHBOARD ====================

@login_required
def analytics_dashboard(request):
    """
    Power BI-style analytics dashboard for supervisors and admins
    """
    try:
        user_profile = UserProfile.objects.get(email=request.user.email)
        if user_profile.role not in ['admin', 'supervisor']:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect_dashboard(request.user)
    except UserProfile.DoesNotExist:
        return redirect_dashboard(request.user)
    
    from django.db.models import Count, Q, Sum, Avg
    from datetime import datetime, timedelta
    
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # Get team members
    team_members = UserProfile.objects.filter(role='member', status='active')
    
    # ====== KPI DATA ======
    total_members = team_members.count()
    
    # Reports statistics
    total_reports = Report.objects.filter(
        created_by__in=team_members
    ).count()
    
    reports_this_month = Report.objects.filter(
        created_by__in=team_members,
        created_at__date__gte=month_start,
        created_at__date__lte=today
    ).count()
    
    reports_this_week = Report.objects.filter(
        created_by__in=team_members,
        created_at__date__gte=week_start,
        created_at__date__lte=today
    ).count()
    
    # Checklist completion
    total_checklists = Checklist.objects.filter(
        assigned_users__in=team_members
    ).distinct().count()
    
    total_logs = ChecklistLog.objects.filter(
        user__in=team_members
    ).count()
    
    # Calculate average completion rate
    completion_rates = []
    for member in team_members:
        assigned = Checklist.objects.filter(
            Q(assigned_users=member) |
            Q(assignment_target='all') |
            Q(assignment_target=member.position)
        ).distinct().count()
        
        if assigned > 0:
            completed = ChecklistLog.objects.filter(
                user=member,
                checklist__in=Checklist.objects.filter(
                    Q(assigned_users=member) |
                    Q(assignment_target='all') |
                    Q(assignment_target=member.position)
                )
            ).values('checklist').distinct().count()
            completion_rates.append((completed / assigned) * 100)
    
    avg_completion = int(sum(completion_rates) / len(completion_rates)) if completion_rates else 0
    
    # ====== FREQUENCY STATISTICS ======
    frequency_stats = {}
    frequency_percentages = {}
    total_checklists_all = Checklist.objects.filter(is_active=True).count()
    
    for freq in ['daily', 'weekly', 'monthly', 'quarterly', 'bi-annual', 'one-off']:
        count = Checklist.objects.filter(is_active=True, frequency=freq).count()
        frequency_stats[freq] = count
        frequency_percentages[freq] = int((count / total_checklists_all) * 100) if total_checklists_all > 0 else 0
    
    # ====== OVERALL PROGRESS ======
    overall_month_progress = 0
    overall_year_progress = 0
    
    # ====== CHART DATA ======
    # 1. Reports by type (Pie Chart)
    report_types_data = Report.objects.filter(
        created_by__in=team_members
    ).values('report_type').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    report_types_labels = [item['report_type'] for item in report_types_data]
    report_types_values = [item['count'] for item in report_types_data]
    
    # 2. Reports by day (Line Chart - Last 30 days)
    thirty_days_ago = today - timedelta(days=30)
    daily_reports = []
    for i in range(30):
        date = thirty_days_ago + timedelta(days=i)
        count = Report.objects.filter(
            created_by__in=team_members,
            created_at__date=date
        ).count()
        daily_reports.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })
    
    daily_labels = [d['date'] for d in daily_reports]
    daily_values = [d['count'] for d in daily_reports]
    
    # 3. Member performance (Bar Chart)
    member_performance = []
    for member in team_members[:15]:
        assigned = Checklist.objects.filter(
            Q(assigned_users=member) |
            Q(assignment_target='all') |
            Q(assignment_target=member.position)
        ).distinct().count()
        
        if assigned > 0:
            completed = ChecklistLog.objects.filter(
                user=member
            ).values('checklist').distinct().count()
            rate = int((completed / assigned) * 100)
        else:
            rate = 0
        
        member_performance.append({
            'name': member.full_name or member.email,
            'rate': rate,
            'assigned': assigned,
            'completed': completed
        })
    
    member_performance.sort(key=lambda x: x['rate'], reverse=True)
    member_names = [m['name'] for m in member_performance[:10]]
    member_rates = [m['rate'] for m in member_performance[:10]]
    
    # 4. Checklist completion trend (Last 7 days)
    weekly_completion = []
    for i in range(7):
        date = today - timedelta(days=6-i)
        count = ChecklistLog.objects.filter(
            user__in=team_members,
            log_date=date
        ).count()
        weekly_completion.append({
            'date': date.strftime('%a'),
            'count': count
        })
    
    weekly_labels = [w['date'] for w in weekly_completion]
    weekly_values = [w['count'] for w in weekly_completion]
    
    # 5. Status distribution
    status_data = Report.objects.filter(
        created_by__in=team_members
    ).values('status').annotate(
        count=Count('id')
    )
    status_labels = [s['status'] for s in status_data]
    status_values = [s['count'] for s in status_data]
    
    context = {
        'user_profile': user_profile,
        'today': today,
        'week_start': week_start,
        'month_start': month_start,
        
        # KPIs
        'total_members': total_members,
        'total_reports': total_reports,
        'reports_this_month': reports_this_month,
        'reports_this_week': reports_this_week,
        'total_checklists': total_checklists,
        'total_logs': total_logs,
        'avg_completion': avg_completion,
        'overall_month_progress': overall_month_progress,
        'overall_year_progress': overall_year_progress,
        
        # Frequency stats
        'frequency_stats': frequency_stats,
        'frequency_percentages': frequency_percentages,
        
        # Chart data (JSON)
        'report_types_labels': json.dumps(report_types_labels),
        'report_types_values': json.dumps(report_types_values),
        'daily_labels': json.dumps(daily_labels),
        'daily_values': json.dumps(daily_values),
        'member_names': json.dumps(member_names),
        'member_rates': json.dumps(member_rates),
        'weekly_labels': json.dumps(weekly_labels),
        'weekly_values': json.dumps(weekly_values),
        'status_labels': json.dumps(status_labels),
        'status_values': json.dumps(status_values),
    }
    
    return render(request, 'control_dashboard/analytics.html', context)