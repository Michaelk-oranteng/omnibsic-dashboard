from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
import re
from datetime import date, timedelta


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
    
    # Link to Django's built-in User model
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile',
        null=True,
        blank=True
    )
    
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=200)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    position = models.CharField(max_length=50, choices=POSITION_CHOICES, default='member')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='member')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.full_name or self.email
    
    def generate_username_from_email(self):
        """
        Generate username from email address.
        Example: john.doe@company.com -> john.doe
        """
        if not self.email:
            return None
        
        # Remove everything after @
        username = self.email.split('@')[0]
        
        # Remove any special characters except dot and underscore
        username = re.sub(r'[^a-zA-Z0-9._]', '', username)
        
        # Convert to lowercase
        username = username.lower()
        
        # Handle edge cases
        if not username:
            username = f"user_{self.id}" if self.id else "user_temp"
        
        # Make it unique if it already exists
        original_username = username
        counter = 1
        while UserProfile.objects.filter(username=username).exclude(id=self.id).exists():
            username = f"{original_username}{counter}"
            counter += 1
        
        return username
    
    def create_django_user(self, password=None):
        """
        Create a Django User from this profile.
        """
        if self.user:
            return self.user
        
        # Generate username if not set
        if not self.username:
            self.username = self.generate_username_from_email()
        
        # Create Django user
        user = User.objects.create_user(
            username=self.username,
            email=self.email,
            password=password or 'defaultpassword123'
        )
        
        # Set full name
        name_parts = self.full_name.split(' ', 1)
        user.first_name = name_parts[0]
        user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        user.save()
        
        self.user = user
        self.save()
        
        return user
    
    class Meta:
        db_table = 'user_profiles'
        ordering = ['full_name']


# ============================================
# SIGNALS: Auto-generate username and create user
# ============================================

@receiver(pre_save, sender=UserProfile)
def auto_generate_username(sender, instance, **kwargs):
    """
    Automatically generate username before saving.
    """
    if not instance.username and instance.email:
        instance.username = instance.generate_username_from_email()


@receiver(post_save, sender=UserProfile)
def create_user_for_profile(sender, instance, created, **kwargs):
    """
    Automatically create Django User when UserProfile is created.
    """
    if created and not instance.user:
        try:
            instance.create_django_user()
        except Exception as e:
            print(f"Error creating user for {instance.email}: {e}")


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
    
    def get_display_data(self):
        """
        Get display data for the report, handling both Excel imports and regular reports.
        """
        report_data = self.data or {}
        
        # Check if this is an Excel import
        if report_data.get('import_type') == 'excel':
            headers = report_data.get('headers', [])
            rows_data = report_data.get('data', [])
            
            # Normalize rows - they should already be dictionaries with proper headers
            normalized_rows = []
            for row in rows_data:
                if isinstance(row, dict):
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
            
            return {
                'is_excel': True,
                'headers': headers,
                'rows': normalized_rows,
                'row_count': len(normalized_rows),
            }
        else:
            # Regular report (non-Excel)
            result = {
                'is_excel': False,
                'rows': [],
                'row_count': 0
            }
            
            # Try to extract from form_data
            if 'form_data' in report_data and report_data['form_data']:
                form = report_data['form_data'][0] if isinstance(report_data['form_data'], list) else report_data['form_data']
                if isinstance(form, dict):
                    row = {
                        'Branch': form.get('BRANCH_UNIT', form.get('BRANCH', form.get('branch', '-'))),
                        'Date': form.get('DATE', form.get('date', '-')),
                        'Observation': form.get('OBSERVATION', form.get('details', form.get('OBSERVATION', '-'))),
                        'Responsible_Staff': form.get('RESPONSIBLE_STAFF', form.get('responsible_staff', '-')),
                        'Status': form.get('STATUS', form.get('status', 'Open'))
                    }
                    result['rows'] = [row]
                    result['row_count'] = 1
            
            return result


class Checklist(models.Model):
    """
    Model for storing checklists/activities.
    """
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('bi-annual', 'Bi-Annual'),
        ('annual', 'Annual'),
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
    
    def get_frequency_days(self):
        """Return the number of days between each occurrence based on frequency."""
        frequency_map = {
            'daily': 1,
            'weekly': 7,
            'monthly': 30,
            'quarterly': 91,
            'bi-annual': 182,
            'one-off': 365,  # One-off doesn't repeat
        }
        return frequency_map.get(self.frequency, 7)
    
    def get_expected_occurrences(self, start_date=None, end_date=None):
        """
        Calculate expected occurrences for a date range based on frequency.
        For daily frequency, only counts weekdays (Monday-Friday).
        For monthly frequency, counts months.
        For weekly frequency, counts weeks.
        """
        from datetime import timedelta
        
        if not start_date:
            start_date = timezone.now().date().replace(month=1, day=1)
        if not end_date:
            end_date = timezone.now().date()
        
        # If end_date is before start_date, swap them
        if end_date < start_date:
            start_date, end_date = end_date, start_date
        
        # For one-off, return 1 if the date range includes any date
        if self.frequency == 'one-off':
            return 1
        
        # For daily frequency, count only weekdays (Monday to Friday)
        if self.frequency == 'daily':
            current = start_date
            count = 0
            while current <= end_date:
                # Monday = 0, Sunday = 6, so weekdays are 0-4
                if current.weekday() < 5:  # Monday to Friday
                    count += 1
                current += timedelta(days=1)
            return count
        
        # For monthly frequency, count the number of months in the range
        if self.frequency == 'monthly':
            months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
            return months
        
        # For weekly frequency, count the number of weeks in the range
        if self.frequency == 'weekly':
            days_diff = (end_date - start_date).days + 1
            weeks = days_diff // 7
            return max(1, weeks)
        
        # For quarterly frequency, count the number of quarters
        if self.frequency == 'quarterly':
            days_diff = (end_date - start_date).days + 1
            quarters = days_diff // 91
            return max(1, quarters)
        
        # For bi-annual frequency, count the number of half-years
        if self.frequency == 'bi-annual':
            days_diff = (end_date - start_date).days + 1
            half_years = days_diff // 182
            return max(1, half_years)
        
        # For other frequencies, calculate based on days difference
        days_diff = (end_date - start_date).days + 1
        frequency_days = self.get_frequency_days()
        return max(1, days_diff // frequency_days)
    
    def get_completion_percentage(self, user_profile, start_date=None, end_date=None):
        """
        Calculate completion percentage for a user based on frequency.
        Capped at 100%.
        """
        if not start_date:
            start_date = timezone.now().date().replace(month=1, day=1)
        if not end_date:
            end_date = timezone.now().date()
        
        # If end_date is before start_date, swap them
        if end_date < start_date:
            start_date, end_date = end_date, start_date
        
        expected = self.get_expected_occurrences(start_date, end_date)
        if expected == 0:
            return 0
        
        # Get actual logs
        actual = ChecklistLog.objects.filter(
            checklist=self,
            user=user_profile,
            log_date__gte=start_date,
            log_date__lte=end_date
        ).count()
        
        # Calculate percentage and cap at 100%
        percentage = int((actual / expected) * 100)
        return min(percentage, 100)
    
    def get_monthly_completion(self, user_profile, month=None, year=None):
        """Calculate completion percentage for a specific month."""
        today = timezone.now().date()
        if month is None:
            month = today.month
        if year is None:
            year = today.year
        
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        return self.get_completion_percentage(user_profile, start_date, end_date)
    
    def get_year_to_date_completion(self, user_profile):
        """Calculate year-to-date completion percentage."""
        today = timezone.now().date()
        start_date = date(today.year, 1, 1)
        return self.get_completion_percentage(user_profile, start_date, today)
    
    def get_monthly_expected(self, user_profile, month=None, year=None):
        """Get the expected number of occurrences for a specific month."""
        today = timezone.now().date()
        if month is None:
            month = today.month
        if year is None:
            year = today.year
        
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        return self.get_expected_occurrences(start_date, end_date)
    
    def get_monthly_actual(self, user_profile, month=None, year=None):
        """Get the actual number of completions for a specific month."""
        today = timezone.now().date()
        if month is None:
            month = today.month
        if year is None:
            year = today.year
        
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        return ChecklistLog.objects.filter(
            checklist=self,
            user=user_profile,
            log_date__gte=start_date,
            log_date__lte=end_date
        ).count()
    
    def get_year_to_date_expected(self, user_profile):
        """Get the expected number of occurrences for year-to-date."""
        today = timezone.now().date()
        start_date = date(today.year, 1, 1)
        return self.get_expected_occurrences(start_date, today)
    
    def get_year_to_date_actual(self, user_profile):
        """Get the actual number of completions for year-to-date."""
        today = timezone.now().date()
        start_date = date(today.year, 1, 1)
        return ChecklistLog.objects.filter(
            checklist=self,
            user=user_profile,
            log_date__gte=start_date,
            log_date__lte=today
        ).count()
    
    def get_next_due_date(self, user_profile):
        """
        Calculate the next due date based on frequency and last completion.
        For daily, skips weekends.
        """
        from datetime import timedelta
        
        if self.frequency == 'one-off':
            return None
        
        # Get the last log for this checklist and user
        last_log = ChecklistLog.objects.filter(
            checklist=self,
            user=user_profile
        ).order_by('-log_date').first()
        
        if not last_log:
            # If no logs, next due is today (or next weekday for daily)
            today = timezone.now().date()
            next_date = today
            if self.frequency == 'daily':
                while next_date.weekday() >= 5:  # Skip weekends
                    next_date += timedelta(days=1)
            return next_date
        
        # Calculate next due date based on frequency
        if self.frequency == 'daily':
            next_date = last_log.log_date + timedelta(days=1)
            # Skip weekends
            while next_date.weekday() >= 5:
                next_date += timedelta(days=1)
        elif self.frequency == 'weekly':
            next_date = last_log.log_date + timedelta(days=7)
        elif self.frequency == 'monthly':
            # Add one month
            if last_log.log_date.month == 12:
                next_date = date(last_log.log_date.year + 1, 1, last_log.log_date.day)
            else:
                next_date = date(last_log.log_date.year, last_log.log_date.month + 1, last_log.log_date.day)
        elif self.frequency == 'quarterly':
            next_date = last_log.log_date + timedelta(days=91)
        elif self.frequency == 'bi-annual':
            next_date = last_log.log_date + timedelta(days=182)
        else:
            days = self.get_frequency_days()
            next_date = last_log.log_date + timedelta(days=days)
        
        # If next date is in the past, set to today (or next weekday)
        if next_date < timezone.now().date():
            next_date = timezone.now().date()
            if self.frequency == 'daily':
                while next_date.weekday() >= 5:
                    next_date += timedelta(days=1)
        
        return next_date
    
    def get_actual_completion_count(self, user_profile, start_date=None, end_date=None):
        """Get the actual number of completed occurrences."""
        if not start_date:
            start_date = timezone.now().date().replace(month=1, day=1)
        if not end_date:
            end_date = timezone.now().date()
        
        if end_date < start_date:
            start_date, end_date = end_date, start_date
        
        return ChecklistLog.objects.filter(
            checklist=self,
            user=user_profile,
            log_date__gte=start_date,
            log_date__lte=end_date
        ).count()
    
    class Meta:
        db_table = 'checklists'
        ordering = ['name']


class ReportSchedule(models.Model):
    """Model for storing report schedules and predicting next due dates."""
    
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('one-off', 'One-off'),
    ]
    
    report = models.ForeignKey('Report', on_delete=models.CASCADE, related_name='schedules')
    frequency = models.CharField(max_length=50, choices=FREQUENCY_CHOICES, default='weekly')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    due_time = models.TimeField(null=True, blank=True)
    last_submitted = models.DateTimeField(null=True, blank=True)
    next_due_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'report_schedules'
        ordering = ['next_due_date']
    
    def calculate_next_due_date(self):
        """Calculate the next due date based on frequency."""
        if not self.last_submitted:
            return self.start_date
        
        last_date = self.last_submitted.date()
        
        frequency_map = {
            'daily': 1,
            'weekly': 7,
            'monthly': 30,
            'quarterly': 91,
            'yearly': 365,
            'one-off': None,
        }
        
        days = frequency_map.get(self.frequency)
        if not days:
            return None
        
        next_date = last_date + timedelta(days=days)
        
        # For daily, skip weekends if needed
        if self.frequency == 'daily':
            while next_date.weekday() >= 5:  # Saturday or Sunday
                next_date += timedelta(days=1)
        
        if self.end_date and next_date > self.end_date:
            return None
        
        return next_date
    
    def save(self, *args, **kwargs):
        if not self.next_due_date:
            self.next_due_date = self.calculate_next_due_date()
        super().save(*args, **kwargs)
    
    def get_frequency_display(self):
        return dict(self.FREQUENCY_CHOICES).get(self.frequency, self.frequency)


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