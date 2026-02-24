from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, 0)

from django import template
from datetime import datetime

register = template.Library()

@register.filter
def month_name(month_number):
    try:
        return datetime(2000, month_number, 1).strftime('%B')
    except:
        return ''


@register.filter
def user_role_name(user):
    """Safely get user's role name (avoids DoesNotExist when user has no Role)."""
    if not user or not user.is_authenticated:
        return None
    try:
        return user.role.role if hasattr(user, 'role') and user.role else None
    except Exception:
        return None