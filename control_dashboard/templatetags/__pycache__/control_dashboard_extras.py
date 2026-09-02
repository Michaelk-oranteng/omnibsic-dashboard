# control_dashboard/templatetags/control_dashboard_extras.py

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary using a key.
    Usage: {{ dict|get_item:key }}
    """
    if dictionary is None:
        return ''
    if key is None:
        return ''
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    # If it's a list, try to find the key in the first item
    if isinstance(dictionary, list) and len(dictionary) > 0:
        if isinstance(dictionary[0], dict):
            return dictionary[0].get(key, '')
    return ''


@register.filter
def get_report_type_fields(report_type):
    """
    Get template fields for a report type.
    This is a fallback function that returns default fields.
    """
    # Define default fields
    default_fields = [
        {'label': 'Branch/Unit', 'field_type': 'dropdown'},
        {'label': 'Date', 'field_type': 'date'},
        {'label': 'Observation', 'field_type': 'textarea'},
        {'label': 'Responsible Staff', 'field_type': 'text'},
        {'label': 'Status', 'field_type': 'dropdown'},
    ]
    return default_fields


@register.simple_tag
def get_report_template_fields(report_type):
    """
    Get template fields for a report type.
    """
    # Define default fields
    default_fields = [
        {'label': 'Branch/Unit', 'field_type': 'dropdown'},
        {'label': 'Date', 'field_type': 'date'},
        {'label': 'Observation', 'field_type': 'textarea'},
        {'label': 'Responsible Staff', 'field_type': 'text'},
        {'label': 'Status', 'field_type': 'dropdown'},
    ]
    return default_fields