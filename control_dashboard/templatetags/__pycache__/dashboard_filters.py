from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a key."""
    if dictionary is None:
        return ''
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''

@register.filter
def unique_list(value):
    """
    Return a list with duplicates removed while preserving order.
    Usage: {{ list|unique_list }}
    """
    if not value:
        return []
    if not isinstance(value, (list, tuple)):
        return value
    seen = set()
    result = []
    for item in value:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result