from django import template

register = template.Library()


@register.filter
def replace(value, args):
    """Usage: {{ value|replace:"_: " }} replaces first arg char with second arg char."""
    try:
        old, new = args.split(':')
        return value.replace(old, new)
    except (ValueError, AttributeError):
        return value


@register.filter
def yesno_smart(value):
    """Render Python True/False as Yes/No; pass all other values through unchanged."""
    if value is True:
        return 'Yes'
    if value is False:
        return 'No'
    return value
