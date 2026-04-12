from django import forms
from .models import ChildProfile


class ChildProfileForm(forms.ModelForm):
    class Meta:
        model = ChildProfile
        fields = ['name', 'age']
