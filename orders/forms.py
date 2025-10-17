# forms.py
from django import forms
from .models import PreEnteredDO

from django import forms

class PreEnteredDOBulkForm(forms.Form):
    do_numbers = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'Enter DO numbers separated by comma, space, or new line'}),
        label='Delivery Order Numbers',
        help_text='Enter multiple DO numbers separated by comma, space, or newline'
    )