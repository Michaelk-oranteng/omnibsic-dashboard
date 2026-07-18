# control_dashboard/management/commands/seed_templates.py

from django.core.management.base import BaseCommand
from control_dashboard.models import ReportTemplate, TemplateField, Branch, ExceptionCategory
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Seed report templates for all report types'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting template seeding...'))
        
        # Check if branches exist
        branch_count = Branch.objects.count()
        if branch_count == 0:
            self.stdout.write(self.style.WARNING('No branches found! Please run seed_exception_data first.'))
            self.stdout.write(self.style.WARNING('Run: python manage.py seed_exception_data'))
            return
        
        self.seed_templates()
        self.stdout.write(self.style.SUCCESS('Template seeding completed!'))

    def seed_templates(self):
        """Seed all report templates"""
        
        templates = [
            {
                'name': 'Security Sweep Report',
                'description': 'Security sweep findings report',
                'fields': [
                    {'label': 'BRANCH/UNIT', 'field_type': 'dropdown', 'data_source': 'database', 'is_required': True},
                    {'label': 'DATE', 'field_type': 'date', 'data_source': 'manual', 'is_required': True},
                    {'label': 'OBSERVATION', 'field_type': 'textarea', 'data_source': 'manual', 'is_required': True},
                    {'label': 'RESPONSIBLE STAFF', 'field_type': 'text', 'data_source': 'manual', 'is_required': True},
                    {'label': 'STATUS', 'field_type': 'dropdown', 'data_source': 'options', 'is_required': True, 'options': 'Open, Closed'},
                ]
            },
            {
                'name': 'Weekly Exceptions Report',
                'description': 'Weekly summary of exceptions',
                'fields': [
                    {'label': 'BRANCH/UNIT', 'field_type': 'dropdown', 'data_source': 'database', 'is_required': True},
                    {'label': 'EXCEPTION', 'field_type': 'textarea', 'data_source': 'manual', 'is_required': True},
                    {'label': 'DATE EXCEPTION WAS NOTED', 'field_type': 'date', 'data_source': 'manual', 'is_required': True},
                    {'label': 'TARGET DATE FOR CLOSURE', 'field_type': 'date', 'data_source': 'manual', 'is_required': True},
                    {'label': 'CATEGORY OF EXCEPTION', 'field_type': 'dropdown', 'data_source': 'database', 'is_required': True},
                    {'label': 'RESPONSIBLE OFFICER', 'field_type': 'text', 'data_source': 'manual', 'is_required': True},
                    {'label': 'SUPERVISOR', 'field_type': 'text', 'data_source': 'manual', 'is_required': True},
                    {'label': 'AUDITEE\'S RESPONSE', 'field_type': 'textarea', 'data_source': 'manual', 'is_required': False},
                    {'label': 'REMARKS', 'field_type': 'textarea', 'data_source': 'manual', 'is_required': False},
                    {'label': 'STATUS', 'field_type': 'dropdown', 'data_source': 'options', 'is_required': True, 'options': 'Open, Closed'},
                    {'label': 'INCOME/COST SAVED', 'field_type': 'number', 'data_source': 'manual', 'is_required': False},
                ]
            },
            {
                'name': 'Cash Imbalance Report',
                'description': 'Cash imbalance investigation report',
                'fields': [
                    {'label': 'DATE', 'field_type': 'date', 'data_source': 'manual', 'is_required': True},
                    {'label': 'BRANCH', 'field_type': 'dropdown', 'data_source': 'database', 'is_required': True},
                    {'label': 'AMOUNT RECORDED', 'field_type': 'number', 'data_source': 'manual', 'is_required': True},
                    {'label': 'OUTSTANDING', 'field_type': 'number', 'data_source': 'manual', 'is_required': True},
                    {'label': 'AMOUNT RECORDED (2)', 'field_type': 'number', 'data_source': 'manual', 'is_required': True},
                    {'label': 'OUTSTANDING (2)', 'field_type': 'number', 'data_source': 'manual', 'is_required': True},
                    {'label': 'RESPONSIBLE STAFF', 'field_type': 'text', 'data_source': 'manual', 'is_required': True},
                ]
            },
            {
                'name': 'Cash Count Report',
                'description': 'Cash count verification report',
                'fields': [
                    {'label': 'DATE', 'field_type': 'date', 'data_source': 'manual', 'is_required': True},
                    {'label': 'BRANCH', 'field_type': 'dropdown', 'data_source': 'database', 'is_required': True},
                    {'label': 'CURRENCY', 'field_type': 'dropdown', 'data_source': 'options', 'is_required': True, 'options': 'GHS, USD, GBP, EUR'},
                    {'label': 'CASH COUNTED', 'field_type': 'number', 'data_source': 'manual', 'is_required': True},
                    {'label': 'GL', 'field_type': 'number', 'data_source': 'manual', 'is_required': True},
                    {'label': 'DIFFERENCE', 'field_type': 'number', 'data_source': 'manual', 'is_required': True},
                    {'label': 'REASON FOR DIFFERENCE', 'field_type': 'textarea', 'data_source': 'manual', 'is_required': False},
                    {'label': 'ATM TRANSACTIONS CAUSING DIFFERENCE IDENTIFIED?', 'field_type': 'dropdown', 'data_source': 'options', 'is_required': True, 'options': 'Yes, No'},
                    {'label': 'RESPONSIBLE STAFF', 'field_type': 'text', 'data_source': 'manual', 'is_required': True},
                    {'label': 'REMARKS', 'field_type': 'textarea', 'data_source': 'manual', 'is_required': False},
                ]
            },
        ]

        template_count = 0
        for template_data in templates:
            try:
                # Check if template already exists
                template, created = ReportTemplate.objects.get_or_create(
                    name=template_data['name'],
                    defaults={
                        'description': template_data['description'],
                        'is_active': True
                    }
                )
                
                if created:
                    template_count += 1
                    self.stdout.write(f'Created template: {template_data["name"]}')
                else:
                    self.stdout.write(f'Template already exists: {template_data["name"]}')
                    # Delete existing fields to update
                    template.fields.all().delete()
                    self.stdout.write(f'  - Updated fields for: {template_data["name"]}')
                
                # Add fields
                for idx, field_data in enumerate(template_data['fields']):
                    # For database source fields, add options from the database
                    options = field_data.get('options', '')
                    
                    if field_data['data_source'] == 'database' and field_data['label'] in ['BRANCH/UNIT', 'BRANCH']:
                        # For branch fields, we'll use the Branch model
                        branches = Branch.objects.filter(is_active=True).values_list('name', flat=True)
                        options = ', '.join(branches) if branches.exists() else ''
                        self.stdout.write(f'  - Added branch options for: {field_data["label"]}')
                    
                    if field_data['data_source'] == 'database' and field_data['label'] == 'CATEGORY OF EXCEPTION':
                        # For category fields, use ExceptionCategory model
                        categories = ExceptionCategory.objects.filter(is_active=True).values_list('name', flat=True)
                        options = ', '.join(categories) if categories.exists() else ''
                        self.stdout.write(f'  - Added category options for: {field_data["label"]}')
                    
                    TemplateField.objects.create(
                        template=template,
                        label=field_data['label'],
                        field_type=field_data['field_type'],
                        data_source=field_data['data_source'],
                        is_required=field_data.get('is_required', False),
                        options=options,
                        order=idx
                    )
                    self.stdout.write(f'  - Added field: {field_data["label"]}')
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error creating template {template_data["name"]}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Created/Updated {template_count} templates'))