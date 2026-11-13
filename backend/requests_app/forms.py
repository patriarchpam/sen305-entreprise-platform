from django import forms
from django.contrib.auth import get_user_model
from .models import Category, Comment, ServiceRequest


class ServiceRequestForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ["category", "title", "description", "location", "priority"]
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if len(title) < 8:
            raise forms.ValidationError("Use at least 8 characters.")
        return title


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if len(body) < 3:
            raise forms.ValidationError("Enter a meaningful comment.")
        return body


class AssignmentForm(forms.Form):
    technician = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(),
        empty_label="Select a technician",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields["technician"].queryset = User.objects.filter(
            is_active=True, is_staff=True
        ).order_by("username")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class ResolutionForm(forms.Form):
    work_notes = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
    )

    def clean_work_notes(self):
        notes = self.cleaned_data["work_notes"].strip()
        if len(notes) < 3:
            raise forms.ValidationError("Enter meaningful resolution work notes.")
        return notes
