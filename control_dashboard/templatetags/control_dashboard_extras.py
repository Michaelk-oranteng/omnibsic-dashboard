# control_dashboard/templatetags/control_dashboard_extras.py

from django import template
from django.template.defaultfilters import stringfilter
from control_dashboard.models import ReportTemplate, TemplateField
from datetime import datetime, date

register = template.Library()

@register.filter
def get_type(value):
    """
    Return the type of a value as a string.
    Usage: {{ my_value|get_type }}
    """
    if value is None:
        return 'None'
    return type(value).__name__

@register.filter
def get_item(obj, key):
    """
    Get an item from a dictionary or list by key/index.
    If obj is a list, try to get the value from the first item.
    Usage: {{ my_obj|get_item:"key_name" }}
    """
    if obj is None:
        return None
    
    # If obj is a list, try to get from the first item
    if isinstance(obj, list):
        if len(obj) > 0 and isinstance(obj[0], dict):
            return obj[0].get(key, '')
        return None
    
    # If obj is a dictionary, get by key
    if isinstance(obj, dict):
        value = obj.get(key, '')
        # If the value is a date/datetime object, format it
        if isinstance(value, (datetime, date)):
            return value
        return value
    
    return None

@register.filter
def is_date(value):
    """
    Check if a value is a date object or a parsable date string.
    Usage: {{ my_value|is_date }}
    """
    if value is None:
        return False
    
    # Check if it's a date/datetime object
    if hasattr(value, 'strftime'):  # It's a date/datetime object
        return True
    
    # Check if it's a string that can be parsed as date
    if isinstance(value, str):
        # Check if it matches common date patterns
        import re
        # Match patterns like "Jan 1, 2024" or "2024-01-01" or "01/01/2024"
        date_patterns = [
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}\b',
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}'
        ]
        for pattern in date_patterns:
            if re.search(pattern, value):
                return True
        
        # Try to parse as ISO format
        try:
            datetime.fromisoformat(value.replace('Z', '+00:00'))
            return True
        except (ValueError, TypeError):
            pass
        
        # Try to parse as date string
        try:
            datetime.strptime(value, '%Y-%m-%d')
            return True
        except (ValueError, TypeError):
            pass
        
        try:
            datetime.strptime(value, '%d/%m/%Y')
            return True
        except (ValueError, TypeError):
            pass
        
        try:
            datetime.strptime(value, '%m/%d/%Y')
            return True
        except (ValueError, TypeError):
            pass
    
    return False

@register.filter
def format_date(value, format_string="M d, Y"):
    """
    Format a date value using Django's date filter.
    Usage: {{ my_value|format_date:"M d, Y" }}
    """
    if value is None:
        return ''
    
    # If it's already a date/datetime object
    if hasattr(value, 'strftime'):
        from django.utils import formats
        return value.strftime(format_string.replace('M', '%b').replace('d', '%d').replace('Y', '%Y'))
    
    # If it's a string, try to parse it
    if isinstance(value, str):
        try:
            # Try to parse common formats
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%b %d, %Y', '%d %b %Y']:
                try:
                    dt = datetime.strptime(value, fmt)
                    return dt.strftime(format_string.replace('M', '%b').replace('d', '%d').replace('Y', '%Y'))
                except ValueError:
                    continue
        except:
            pass
    
    return value

@register.filter
def get_template_fields(report_type):
    """
    Get template fields for a specific report type.
    Usage: {% with template_fields|get_template_fields:report_type as fields %}
    """
    try:
        if not report_type:
            return []
        
        template = ReportTemplate.objects.filter(
            name=report_type,
            is_active=True
        ).first()
        
        if template:
            return template.fields.all().order_by('order')
    except Exception as e:
        print(f"Error getting template fields for {report_type}: {e}")
    
    return []

@register.filter
def get_field_value(data, field_label):
    """
    Get a value from report data by field label.
    Handles both dictionary and list data.
    Usage: {{ report.data|get_field_value:"Branch" }}
    """
    try:
        if not data or not field_label:
            return None
        
        # If data is a list, try to get from first item
        if isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], dict):
                data = data[0]
            else:
                return None
        
        if not isinstance(data, dict):
            return None
        
        # Try exact match first
        if field_label in data:
            return data[field_label]
        
        # Try case-insensitive match
        for key, value in data.items():
            if key.lower() == field_label.lower():
                return value
        
        return None
    except Exception:
        return None

@register.filter
def get_all_rows(data):
    """
    Get all rows from the data if it's a list.
    If it's a dictionary, wrap it in a list.
    Usage: {{ report.data|get_all_rows }}
    """
    if data is None:
        return []
    
    if isinstance(data, list):
        return data
    
    if isinstance(data, dict):
        # Check if there's a special key for all rows
        if '_all_rows' in data:
            return data['_all_rows']
        return [data]
    
    return []

@register.simple_tag
def get_report_template_fields(report_type):
    """
    Simple tag to get template fields.
    Usage: {% get_report_template_fields report_type as fields %}
    """
    try:
        if not report_type:
            return []
        
        template = ReportTemplate.objects.filter(
            name=report_type,
            is_active=True
        ).first()
        
        if template:
            return template.fields.all().order_by('order')
    except Exception:
        pass
    
    return []

@register.filter
def get_status_badge_class(status):
    """
    Get the CSS class for a status badge.
    Usage: {{ report.status|get_status_badge_class }}
    """
    status_classes = {
        'draft': 'badge-secondary',
        'submitted': 'badge-warning',
        'in_review': 'badge-info',
        'approved': 'badge-success',
        'rejected': 'badge-danger',
        'revision_requested': 'badge-warning',
        'assigned': 'badge-primary',
        'in_progress': 'badge-info',
        'completed': 'badge-success',
        'cancelled': 'badge-secondary',
    }
    return status_classes.get(status, 'badge-secondary')

@register.filter
def get_data_value(data, field_label):
    """
    Get a value from data that could be a list or dict.
    This is a more robust version that handles nested structures.
    """
    try:
        if not data or not field_label:
            return ''
        
        # If data is a list, try to find the value in any item
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    # Try exact match
                    if field_label in item:
                        return item[field_label]
                    # Try case-insensitive match
                    for key, value in item.items():
                        if key.lower() == field_label.lower():
                            return value
            return ''
        
        # If data is a dictionary
        if isinstance(data, dict):
            # Try exact match
            if field_label in data:
                return data[field_label]
            # Try case-insensitive match
            for key, value in data.items():
                if key.lower() == field_label.lower():
                    return value
            return ''
        
        return ''
    except Exception:
        return ''

@register.filter
def get_display_value(value):
    """
    Convert a value to a display-friendly format.
    Handles dates, booleans, and None values.
    """
    if value is None:
        return '-'
    
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    
    if hasattr(value, 'strftime'):  # It's a date/datetime object
        return value.strftime('%b %d, %Y')
    
    if isinstance(value, (int, float)):
        return str(value)
    
    return str(value)