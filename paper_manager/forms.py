from django import forms
from .models import Paper

class PaperForm(forms.ModelForm):
    """
    Defines a form for creating a Paper model instance with (required)fields for
    'title', 'citation_style', 'file', 'start_bibliography', and 'end_bibliography' while excluding 'authors'.
    It also includes widgets for 'start_bibliography' and 'end_bibliography' with specific attributes.
    Additionally, it includes a field for the author of the paper.
    """
    class Meta:
        model = Paper
        fields = ['title', 'citation_style', 'file', 'start_bibliography', 'end_bibliography']
        exclude = ['authors']
        widgets = {
            'start_bibliography': forms.Textarea(attrs={'class': 'form-control', 'required': True}),
            'end_bibliography': forms.Textarea(attrs={'class': 'form-control', 'required': True}),
        }

    author = forms.CharField(max_length=100, required=False)


class AddPaperFileForm(forms.ModelForm):
    """
    Defines a form for updating the 'file' field of a Paper model instance.
    """
    class Meta:
        model = Paper
        fields = ['file']
