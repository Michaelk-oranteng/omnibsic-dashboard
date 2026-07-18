# control_dashboard/models.py

from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    POSITION_CHOICES = [
        ('hoc', 'Head Office Control'),
        ('cc', 'Cluster Control'),
    ]
    
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('supervisor', 'Supervisor'),
        ('member', 'Member'),
    ]
    
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True, default='')
    position = models.CharField(max_length=50, choices=POSITION_CHOICES, default='hoc')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='member')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    def get_position_display(self):
        return dict(self.POSITION_CHOICES).get(self.position, self.position)
    
    def get_role_display(self):
        return dict(self.ROLE_CHOICES).get(self.role, self.role)
    
    def __str__(self):
        return self.email
    
    class Meta:
        db_table = 'user_profiles'
        ordering = ['-created_at']


class ActivityLog(models.Model):
    ACTIVITY_CHOICES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('user_created', 'User Created'),
        ('user_updated', 'User Updated'),
        ('user_deleted', 'User Deleted'),
        ('user_status_changed', 'User Status Changed'),
        ('report_created', 'Report Created'),
        ('report_updated', 'Report Updated'),
        ('report_deleted', 'Report Deleted'),
        ('report_assigned', 'Report Assigned'),
        ('report_completed', 'Report Completed'),
        ('template_created', 'Template Created'),
        ('template_updated', 'Template Updated'),
        ('template_deleted', 'Template Deleted'),
        ('checklist_created', 'Checklist Created'),
        ('checklist_updated', 'Checklist Updated'),
        ('checklist_deleted', 'Checklist Deleted'),
        ('task_status_changed', 'Task Status Changed'),
        ('activity_edited', 'Activity Edited'),
        ('export', 'Report Export'),
        ('exception', 'Logged Exception'),
        ('settings_updated', 'Settings Updated'),
        ('password_changed', 'Password Changed'),
        ('profile_updated', 'Profile Updated'),
    ]
    
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_CHOICES)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def get_activity_type_display(self):
        return dict(self.ACTIVITY_CHOICES).get(self.activity_type, self.activity_type)
    
    def __str__(self):
        return f"{self.user.email} - {self.get_activity_type_display()} - {self.created_at}"
    
    class Meta:
        db_table = 'activity_logs'
        ordering = ['-created_at']


class Report(models.Model):
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
        ('cancelled', 'Cancelled'),
    ]
    
    report_type = models.CharField(max_length=100)
    frequency = models.CharField(max_length=50, choices=FREQUENCY_CHOICES, default='one-off')
    description = models.TextField(blank=True)
    deadline_date = models.DateField(null=True, blank=True)
    deadline_time = models.TimeField(null=True, blank=True)
    created_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='reports_created')
    assigned_to = models.ManyToManyField(UserProfile, related_name='reports_assigned')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='assigned')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_frequency_display(self):
        return dict(self.FREQUENCY_CHOICES).get(self.frequency, self.frequency)
    
    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    def __str__(self):
        return f"{self.report_type} - {self.get_frequency_display()} ({self.get_status_display()})"
    
    class Meta:
        db_table = 'reports'
        ordering = ['-created_at']


# ==================== REPORT SCHEDULE MODEL ====================

class ReportSchedule(models.Model):
    """
    Model for storing the rendition schedule of all reports.
    This defines the standard reporting schedule including report names,
    deadlines, and responsible officers.
    """
    
    DEADLINE_TYPES = [
        ('monthly_date', 'Monthly Date'),
        ('weekday', 'Weekday'),
        ('custom', 'Custom'),
    ]
    
    # Report Details
    name = models.CharField(max_length=200, unique=True, help_text="Name of the report")
    report_type = models.CharField(max_length=100, help_text="Category/Type of report")
    description = models.TextField(blank=True, help_text="Detailed description of the report")
    
    # Schedule Details
    deadline_type = models.CharField(max_length=50, choices=DEADLINE_TYPES, default='monthly_date')
    deadline_day = models.IntegerField(null=True, blank=True, help_text="Day of month (1-31) for monthly_date type")
    deadline_weekday = models.CharField(max_length=20, blank=True, help_text="Day of week for weekday type")
    deadline_time = models.TimeField(help_text="Time when report is due (GMT)")
    deadline_description = models.CharField(max_length=200, blank=True, help_text="Human readable deadline description")
    
    # Responsible Officers
    responsible_officer = models.ForeignKey(
        UserProfile, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reports_responsible',
        help_text="Primary officer responsible for this report"
    )
    backup_officer = models.ForeignKey(
        UserProfile, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reports_backup',
        help_text="Backup officer for this report"
    )
    responsible_officer_name = models.CharField(max_length=200, blank=True, help_text="Name of responsible officer")
    backup_officer_name = models.CharField(max_length=200, blank=True, help_text="Name of backup officer")
    
    # Additional officers (for reports with multiple assignees like "All")
    additional_officers = models.ManyToManyField(
        UserProfile, 
        blank=True, 
        related_name='reports_additional',
        help_text="Additional officers assigned to this report"
    )
    additional_officers_names = models.TextField(blank=True, help_text="Comma separated names of additional officers")
    
    # Status
    is_active = models.BooleanField(default=True)
    is_recurring = models.BooleanField(default=True, help_text="Whether this is a recurring report")
    frequency = models.CharField(max_length=50, choices=Report.FREQUENCY_CHOICES, default='monthly')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, related_name='schedules_created')
    
    def get_deadline_description(self):
        """Get a human readable deadline description."""
        if self.deadline_type == 'monthly_date':
            return f"{self.deadline_day}th (or last working day before {self.deadline_day}th)"
        elif self.deadline_type == 'weekday':
            return f"{self.deadline_weekday} (or last working day before {self.deadline_weekday})"
        return self.deadline_description
    
    def get_responsible_officer_display(self):
        """Get the responsible officer name."""
        if self.responsible_officer:
            return self.responsible_officer.full_name or self.responsible_officer.email
        return self.responsible_officer_name
    
    def get_backup_officer_display(self):
        """Get the backup officer name."""
        if self.backup_officer:
            return self.backup_officer.full_name or self.backup_officer.email
        return self.backup_officer_name
    
    def get_all_officers(self):
        """Get a list of all officers (responsible, backup, additional)."""
        officers = []
        if self.get_responsible_officer_display():
            officers.append(self.get_responsible_officer_display())
        if self.get_backup_officer_display():
            officers.append(self.get_backup_officer_display())
        
        # Add additional officers names
        if self.additional_officers_names:
            for name in self.additional_officers_names.split(','):
                if name.strip():
                    officers.append(name.strip())
        
        # Add additional officers from ManyToMany
        for officer in self.additional_officers.all():
            officers.append(officer.full_name or officer.email)
        
        return officers
    
    def __str__(self):
        return f"{self.name} - {self.get_deadline_description()}"
    
    class Meta:
        db_table = 'report_schedules'
        ordering = ['name']


# ==================== REPORT INSTANCE MODEL ====================

class ReportInstance(models.Model):
    """
    Model for tracking individual instances of reports.
    Each instance represents a specific report for a specific period.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('overdue', 'Overdue'),
    ]
    
    report_schedule = models.ForeignKey(
        ReportSchedule, 
        on_delete=models.CASCADE, 
        related_name='instances'
    )
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    due_date = models.DateField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        UserProfile, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='submitted_reports'
    )
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    review_comments = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        UserProfile, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reviewed_reports'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Data storage
    data = models.JSONField(default=dict, blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def is_overdue(self):
        """Check if the report is overdue."""
        from django.utils import timezone
        if self.status in ['pending', 'in_progress'] and self.due_date < timezone.now().date():
            return True
        return False
    
    def get_status_display(self):
        if self.is_overdue() and self.status not in ['submitted', 'approved', 'rejected']:
            return 'Overdue'
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    def __str__(self):
        return f"{self.report_schedule.name} - {self.period_start} to {self.period_end}"
    
    class Meta:
        db_table = 'report_instances'
        ordering = ['-due_date']


# ==================== TEMPLATE BUILDER MODELS ====================

class ReportTemplate(models.Model):
    """
    Model for storing report templates.
    """
    FIELD_TYPES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('dropdown', 'Dropdown'),
        ('checkbox', 'Checkbox'),
        ('textarea', 'Text Area'),
    ]
    
    DATA_SOURCES = [
        ('manual', 'Manual Entry'),
        ('database', 'Database Lookup'),
        ('options', 'Predefined Options'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='templates_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'report_templates'
        ordering = ['-created_at']


class TemplateField(models.Model):
    """
    Model for storing fields within a template.
    """
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='fields')
    label = models.CharField(max_length=200)
    field_type = models.CharField(max_length=50, choices=ReportTemplate.FIELD_TYPES, default='text')
    data_source = models.CharField(max_length=50, choices=ReportTemplate.DATA_SOURCES, default='manual')
    is_required = models.BooleanField(default=False)
    options = models.TextField(blank=True, help_text='Comma separated options for dropdown/checkbox')
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_options_list(self):
        if self.options:
            return [opt.strip() for opt in self.options.split(',') if opt.strip()]
        return []
    
    def __str__(self):
        return f"{self.template.name} - {self.label}"
    
    class Meta:
        db_table = 'template_fields'
        ordering = ['order']


class TemplateAssignment(models.Model):
    """
    Model for assigning templates to reports.
    """
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='assignments')
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='template_assignments')
    assigned_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='template_assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'template_assignments'
        unique_together = ['template', 'report']


# ==================== CHECKLIST MODELS ====================

class Checklist(models.Model):
    """
    Model for storing checklists/activities.
    """
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]
    
    ASSIGNMENT_CHOICES = [
        ('all', 'All Personnel'),
        ('hoc', 'Head Office Control'),
        ('cc', 'Cluster Control'),
        ('specific', 'Specific Users'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    frequency = models.CharField(max_length=50, choices=FREQUENCY_CHOICES, default='weekly')
    assignment_target = models.CharField(max_length=50, choices=ASSIGNMENT_CHOICES, default='all')
    assigned_users = models.ManyToManyField(UserProfile, blank=True, related_name='assigned_checklists')
    created_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='checklists_created')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_frequency_display(self):
        return dict(self.FREQUENCY_CHOICES).get(self.frequency, self.frequency)
    
    def get_assignment_display(self):
        return dict(self.ASSIGNMENT_CHOICES).get(self.assignment_target, self.assignment_target)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'checklists'
        ordering = ['-created_at']


class ChecklistTask(models.Model):
    """
    Model for storing tasks within a checklist.
    """
    checklist = models.ForeignKey(Checklist, on_delete=models.CASCADE, related_name='tasks')
    description = models.TextField()
    order = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.checklist.name} - Task {self.order + 1}"
    
    class Meta:
        db_table = 'checklist_tasks'
        ordering = ['order']


class Draft(models.Model):
    """
    Model for storing draft reports.
    """
    STATUS_CHOICES = [
        ('', 'No Status'),
        ('draft', 'Draft'),
        ('submitted', 'Submitted for Review'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('revision_requested', 'Revision Requested'),
    ]
    
    report_type = models.CharField(max_length=100)
    template = models.ForeignKey('ReportTemplate', on_delete=models.SET_NULL, null=True, blank=True, related_name='drafts')
    created_by = models.ForeignKey('UserProfile', on_delete=models.CASCADE, related_name='drafts')
    assigned_to = models.ForeignKey('UserProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_drafts')
    data = models.JSONField(default=dict)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='', blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comments = models.TextField(blank=True)
    reviewed_by = models.ForeignKey('UserProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_drafts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_status_display(self):
        if not self.status:
            return 'Saved'
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    def __str__(self):
        return f"{self.report_type} - {self.created_by.email} ({self.get_status_display()})"
    
    class Meta:
        db_table = 'drafts'
        ordering = ['-created_at']


class Branch(models.Model):
    """Model for storing branch information"""
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'branches'
        ordering = ['name']
        verbose_name_plural = 'Branches'

    def __str__(self):
        return self.name


class ExceptionCategory(models.Model):
    """Model for storing exception categories"""
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exception_categories'
        ordering = ['name']
        verbose_name_plural = 'Exception Categories'

    def __str__(self):
        return self.name


class DraftReview(models.Model):
    """
    Model for tracking draft review history.
    """
    REVIEW_ACTIONS = [
        ('submitted', 'Submitted for Review'),
        ('assigned', 'Assigned to Reviewer'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('revision_requested', 'Revision Requested'),
        ('resubmitted', 'Resubmitted'),
    ]
    
    draft = models.ForeignKey('Draft', on_delete=models.CASCADE, related_name='reviews')
    action = models.CharField(max_length=50, choices=REVIEW_ACTIONS)
    performed_by = models.ForeignKey('UserProfile', on_delete=models.CASCADE, related_name='draft_reviews')
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'draft_reviews'
        ordering = ['-created_at']
    
    def get_action_display(self):
        return dict(self.REVIEW_ACTIONS).get(self.action, self.action)
    
    def __str__(self):
        return f"{self.draft.report_type} - {self.get_action_display()} - {self.created_at}"


class ChecklistLog(models.Model):
    """
    Model for storing checklist completion logs.
    This is a dedicated table for tracking which dates a user completed a checklist.
    """
    checklist = models.ForeignKey(Checklist, on_delete=models.CASCADE, related_name='logs')
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='checklist_logs')
    completion_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'checklist_logs'
        unique_together = ['checklist', 'user', 'completion_date']
        ordering = ['-completion_date']
    
    def __str__(self):
        return f"{self.checklist.name} - {self.user.email} - {self.completion_date}"