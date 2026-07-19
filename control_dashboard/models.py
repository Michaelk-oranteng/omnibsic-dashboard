# control_dashboard/models.py

from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    """
    User Profile model for storing user information.
    """
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('supervisor', 'Supervisor'),
        ('member', 'Member'),
    ]
    
    POSITION_CHOICES = [
        ('hc', 'Headoffice Control'),
        ('cc', 'Cluster Control'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=200)
    position = models.CharField(max_length=50, choices=POSITION_CHOICES, default='member')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='member')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.full_name or self.email
    
    class Meta:
        db_table = 'user_profiles'
        ordering = ['full_name']


# control_dashboard/models.py - Add this after UserProfile

class Report(models.Model):
    """
    Model for storing reports created by admin.
    """
    FREQUENCY_CHOICES = [
        ('one-off', 'One Off'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]
    
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    report_type = models.CharField(max_length=200)
    frequency = models.CharField(max_length=50, choices=FREQUENCY_CHOICES, default='one-off')
    description = models.TextField(blank=True)
    deadline_date = models.DateField(null=True, blank=True)
    deadline_time = models.TimeField(null=True, blank=True)
    assigned_to = models.ManyToManyField('UserProfile', blank=True, related_name='assigned_reports')
    is_assigned_to_all = models.BooleanField(default=False)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='assigned')
    created_by = models.ForeignKey('UserProfile', on_delete=models.CASCADE, related_name='created_reports')
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.report_type
    
    def get_frequency_display(self):
        return dict(self.FREQUENCY_CHOICES).get(self.frequency, self.frequency)
    
    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    class Meta:
        db_table = 'reports'
        ordering = ['-created_at']


class ReportTemplate(models.Model):
    """
    Model for storing report templates.
    """
    FIELD_TYPES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('checkbox', 'Checkbox'),
        ('dropdown', 'Dropdown'),
        ('textarea', 'Text Area'),
    ]
    
    DATA_SOURCES = [
        ('manual', 'Manual Input'),
        ('branches', 'Branches'),
        ('categories', 'Exception Categories'),
        ('users', 'Users'),
        ('database', 'Database'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey('UserProfile', on_delete=models.SET_NULL, null=True, related_name='created_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'report_templates'
        ordering = ['name']


class TemplateField(models.Model):
    """
    Model for storing template fields.
    """
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='fields')
    label = models.CharField(max_length=200)
    field_type = models.CharField(max_length=50, choices=ReportTemplate.FIELD_TYPES, default='text')
    data_source = models.CharField(max_length=50, choices=ReportTemplate.DATA_SOURCES, default='manual')
    is_required = models.BooleanField(default=False)
    options = models.TextField(blank=True, help_text='Comma-separated options for dropdown fields')
    order = models.IntegerField(default=0)
    
    def get_options_list(self):
        if self.options:
            return [opt.strip() for opt in self.options.split(',') if opt.strip()]
        return []
    
    def __str__(self):
        return f"{self.template.name} - {self.label}"
    
    class Meta:
        db_table = 'template_fields'
        ordering = ['order']


class Checklist(models.Model):
    """
    Model for storing checklists/activities.
    """
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('one-off', 'One-off'),
    ]
    
    ASSIGNMENT_CHOICES = [
        ('all', 'All Users'),
        ('cc', 'Cluster Control'),
        ('hc', 'Head Office Control'),
        ('specific', 'Specific Users'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    frequency = models.CharField(max_length=50, choices=FREQUENCY_CHOICES, default='weekly')
    assignment_target = models.CharField(max_length=50, choices=ASSIGNMENT_CHOICES, default='all')
    assigned_users = models.ManyToManyField('UserProfile', blank=True, related_name='assigned_checklists')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey('UserProfile', on_delete=models.SET_NULL, null=True, related_name='created_checklists')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def get_frequency_display(self):
        return dict(self.FREQUENCY_CHOICES).get(self.frequency, self.frequency)
    
    def get_assignment_display(self):
        return dict(self.ASSIGNMENT_CHOICES).get(self.assignment_target, self.assignment_target)
    
    def get_assigned_users_display(self):
        """Get a display string for assigned users."""
        if self.assignment_target == 'all':
            return 'All Users'
        elif self.assignment_target == 'cc':
            return 'Cluster Control'
        elif self.assignment_target == 'hc':
            return 'Head Office Control'
        else:
            users = self.assigned_users.all()
            if users:
                return ', '.join([user.full_name for user in users])
            return 'No users assigned'
    
    class Meta:
        db_table = 'checklists'
        ordering = ['name']


class ChecklistTask(models.Model):
    """
    Model for storing checklist tasks.
    """
    checklist = models.ForeignKey(Checklist, on_delete=models.CASCADE, related_name='tasks')
    description = models.CharField(max_length=500)
    order = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.checklist.name} - {self.description[:50]}"
    
    class Meta:
        db_table = 'checklist_tasks'
        ordering = ['order']

class ChecklistLog(models.Model):
    """
    Model for storing member checklist completion logs.
    """
    checklist = models.ForeignKey('Checklist', on_delete=models.CASCADE, related_name='logs')
    user = models.ForeignKey('UserProfile', on_delete=models.CASCADE, related_name='checklist_logs')
    log_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'checklist_logs'
        unique_together = ['checklist', 'user', 'log_date']
        ordering = ['-log_date']
    
    def __str__(self):
        return f"{self.checklist.name} - {self.user.full_name} - {self.log_date}"


class ReportSubmission(models.Model):
    """
    Model for storing member report submissions.
    """
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
    ]
    
    report_type = models.CharField(max_length=200)
    template_name = models.CharField(max_length=200, blank=True)
    submitted_by = models.ForeignKey('UserProfile', on_delete=models.CASCADE, related_name='report_submissions')
    submission_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    data = models.JSONField(default=dict)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='submitted')
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.report_type} - {self.submitted_by.full_name} - {self.submission_date.strftime('%Y-%m-%d')}"
    
    class Meta:
        db_table = 'report_submissions'
        ordering = ['-submission_date']

# control_dashboard/models.py

class Branch(models.Model):
    """Model for storing branch/department names."""
    name = models.CharField(max_length=200, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'branches'
        ordering = ['name']


class ExceptionCategory(models.Model):
    """Model for storing exception categories."""
    name = models.CharField(max_length=200, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'exception_categories'
        ordering = ['name']

# models.py

class ActivityLog(models.Model):
    """
    Model to track user activities across the application.
    """
    ACTIVITY_TYPES = (
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('report_created', 'Report Created'),
        ('report_updated', 'Report Updated'),
        ('report_deleted', 'Report Deleted'),
        ('report_submitted', 'Report Submitted'),
        ('report_approved', 'Report Approved'),
        ('report_rejected', 'Report Rejected'),
        ('checklist_completed', 'Checklist Completed'),
        ('template_created', 'Template Created'),
        ('template_updated', 'Template Updated'),
        ('template_deleted', 'Template Deleted'),
        ('user_created', 'User Created'),
        ('user_updated', 'User Updated'),
        ('user_deleted', 'User Deleted'),
        ('email_sent', 'Email Sent'),
        ('draft_saved', 'Draft Saved'),
        ('draft_deleted', 'Draft Deleted'),
        ('deduction_created', 'Deduction Created'),
        ('deduction_updated', 'Deduction Updated'),
        ('deduction_deleted', 'Deduction Deleted'),
        ('score_updated', 'Score Updated'),
    )
    
    ACTIVITY_ICONS = {
        'login': 'fa-sign-in-alt',
        'logout': 'fa-sign-out-alt',
        'report_created': 'fa-file-alt',
        'report_updated': 'fa-edit',
        'report_deleted': 'fa-trash',
        'report_submitted': 'fa-paper-plane',
        'report_approved': 'fa-check-circle',
        'report_rejected': 'fa-times-circle',
        'checklist_completed': 'fa-check-double',
        'template_created': 'fa-cog',
        'template_updated': 'fa-cog',
        'template_deleted': 'fa-cog',
        'user_created': 'fa-user-plus',
        'user_updated': 'fa-user-edit',
        'user_deleted': 'fa-user-minus',
        'email_sent': 'fa-envelope',
        'draft_saved': 'fa-save',
        'draft_deleted': 'fa-trash-alt',
        'deduction_created': 'fa-minus-circle',
        'deduction_updated': 'fa-edit',
        'deduction_deleted': 'fa-trash',
        'score_updated': 'fa-star',
    }
    
    user = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='activity_logs'
    )
    activity_type = models.CharField(
        max_length=50,
        choices=ACTIVITY_TYPES
    )
    details = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed description of the activity"
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="IP address of the user"
    )
    user_agent = models.TextField(
        blank=True,
        null=True,
        help_text="User agent string"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['activity_type']),
        ]
    
    def __str__(self):
        return f"{self.user.full_name} - {self.get_activity_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def get_activity_icon(self):
        """Get the FontAwesome icon class for this activity type."""
        return self.ACTIVITY_ICONS.get(self.activity_type, 'fa-circle')

# views.py - Update the log_activity function

def log_activity(user, activity_type, details, request=None):
    """
    Helper function to log user activities.
    """
    try:
        ip_address = request.META.get('REMOTE_ADDR') if request else None
        user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
        
        ActivityLog.objects.create(
            user=user,
            activity_type=activity_type,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    except Exception as e:
        # Log error but don't break the application
        print(f"Error logging activity: {e}")

# models.py

class AdHocDeduction(models.Model):
    """
    Model to track ad-hoc deductions/penalties for team members.
    """
    user = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='ad_hoc_deductions',
        help_text="The team member receiving the deduction"
    )
    task_description = models.CharField(
        max_length=255,
        help_text="Description of the task or report"
    )
    points = models.IntegerField(
        default=0,
        help_text="Number of points deducted (0-100)"
    )
    reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for the deduction"
    )
    created_by = models.ForeignKey(
        'UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_deductions',
        help_text="Supervisor who created the deduction"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the deduction was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the deduction was last updated"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Ad-Hoc Deduction'
        verbose_name_plural = 'Ad-Hoc Deductions'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['points']),
        ]
    
    def __str__(self):
        return f"{self.user.full_name} - -{self.points}% - {self.task_description[:30]}"
    
    def get_points_display(self):
        """Return formatted points display."""
        return f"-{self.points}%"
    
    def get_badge_class(self):
        """Return the CSS class for the deduction badge."""
        if self.points >= 20:
            return 'high'
        elif self.points >= 10:
            return 'medium'
        else:
            return 'low'
    
    def get_status_color(self):
        """Return the color for the deduction badge."""
        if self.points >= 20:
            return 'danger'
        elif self.points >= 10:
            return 'warning'
        else:
            return 'success'