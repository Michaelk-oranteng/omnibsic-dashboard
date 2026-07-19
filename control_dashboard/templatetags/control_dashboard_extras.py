# control_dashboard/templatetags/control_dashboard_extras.py

from django import template
from django.template.defaultfilters import stringfilter
from control_dashboard.models import TemplateField

register = template.Library()

@register.simple_tag
def get_report_template_fields(report_type):
    """
    Get template fields for a given report type.
    """
    try:
        from control_dashboard.models import ReportTemplate
        
        template_obj = ReportTemplate.objects.filter(name=report_type, is_active=True).first()
        if template_obj:
            fields = template_obj.fields.all().order_by('order')
            print(f"Found {fields.count()} fields for {report_type}")
            return fields
        print(f"Template not found for: {report_type}")
        return []
    except Exception as e:
        print(f"Error getting template fields: {e}")
        return []


@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary by key. Handles nested dicts and case-insensitive matching.
    """
    if not dictionary or not key:
        return None
    
    # If dictionary is a dict, try to get the value
    if isinstance(dictionary, dict):
        # Try exact match first
        if key in dictionary:
            return dictionary[key]
        
        # Try case-insensitive match
        key_lower = key.lower()
        for k, v in dictionary.items():
            if k.lower() == key_lower:
                return v
        
        # Try key without spaces (for field matching)
        key_no_spaces = key.replace(' ', '_').lower()
        for k, v in dictionary.items():
            if k.lower() == key_no_spaces:
                return v
        
        # Try key with underscores instead of spaces
        key_with_underscores = key.replace(' ', '_')
        for k, v in dictionary.items():
            if k.lower() == key_with_underscores.lower():
                return v
        
        # Try to find by partial match
        for k, v in dictionary.items():
            if key_lower in k.lower() or k.lower() in key_lower:
                return v
        
        # Debug: Print the dictionary keys to see what's available
        print(f"Key '{key}' not found. Available keys: {list(dictionary.keys())}")
        
        return None
    
    # If dictionary has items, try to find matching key
    if hasattr(dictionary, 'items'):
        for k, v in dictionary.items():
            if k.lower() == key.lower():
                return v
    
    return None