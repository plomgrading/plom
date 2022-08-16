from django import forms

from Connect.models import CoreServerConnection


class CoreConnectionForm(forms.Form):
    """Handle connecting to the core server"""
    server_url = forms.CharField(
        label='URL:',
        widget=forms.TextInput(attrs={'class': 'form-control', 'x-bind:value': 'server_url', 'x-model': 'server_url'}),
        initial='localhost'
    )
    port_number = forms.CharField(
        label='Port number:',
        widget=forms.NumberInput(attrs={'min': 0, 'class': 'form-control', 'x-bind:value': 'port_number', 'x-model': 'port_number'}),
        initial=41984
    )
