from django import forms


class CommentForm(forms.Form):
    content = models.TextField(label="reply", max_length=2000)
