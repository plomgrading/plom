from django import forms

from Connect.models import CoreServerConnection


class CoreConnectionForm(forms.Form):
    """Handle connecting to the core server"""
    server_url = forms.URLField(
        label='URL:',
        widget=forms.URLInput(attrs={'class': 'form-control'}),
        initial='https://localhost:41984'
    )
