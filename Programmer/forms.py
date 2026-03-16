from django import forms
from Client.models import Service, PortfolioItem, Category


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['title', 'description', 'price', 'duration_days', 'category', 'is_active']
        widgets = {
            'title':        forms.TextInput(attrs={'class': 'form-control'}),
            'description':  forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'price':        forms.NumberInput(attrs={'class': 'form-control', 'min': 1000}),
            'duration_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'category':     forms.Select(attrs={'class': 'form-control'}),
            'is_active':    forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'title':        'Xizmat sarlavhasi',
            'description':  'Tavsif',
            'price':        'Narx (so\'m)',
            'duration_days': 'Bajarish muddati (kun)',
            'category':     'Kategoriya',
            'is_active':    'Faol (ko\'rinadigan)',
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price and price < 1000:
            raise forms.ValidationError('Narx kamida 1 000 so\'m bo\'lishi kerak.')
        return price

    def clean_duration_days(self):
        days = self.cleaned_data.get('duration_days')
        if days and days < 1:
            raise forms.ValidationError('Muddat kamida 1 kun.')
        return days


class PortfolioForm(forms.ModelForm):
    technologies_input = forms.CharField(
        required=False,
        label='Texnologiyalar (vergul bilan)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Python, Django, React'})
    )

    class Meta:
        model = PortfolioItem
        fields = ['title', 'description', 'image', 'project_url', 'github_url', 'order']
        widgets = {
            'title':       forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'image':       forms.FileInput(attrs={'class': 'form-control'}),
            'project_url': forms.URLInput(attrs={'class': 'form-control'}),
            'github_url':  forms.URLInput(attrs={'class': 'form-control'}),
            'order':       forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.technologies:
            self.fields['technologies_input'].initial = ', '.join(self.instance.technologies)

    def save(self, commit=True):
        item = super().save(commit=False)
        raw = self.cleaned_data.get('technologies_input', '')
        item.technologies = [t.strip() for t in raw.split(',') if t.strip()] if raw else []
        if commit:
            item.save()
        return item