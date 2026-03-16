from django import forms
from django.contrib.auth.forms import (
    PasswordChangeForm as DjangoPasswordChangeForm,
    SetPasswordForm as DjangoSetPasswordForm,
)
from django.core.exceptions import ValidationError
from .models import User, Order, Review, Complaint



class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Parol', min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Kamida 8 ta belgi'})
    )
    password2 = forms.CharField(
        label='Parolni tasdiqlang',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    role = forms.ChoiceField(
        choices=[(User.ROLE_CLIENT, 'Mijoz'), (User.ROLE_DEVELOPER, 'Dasturchi')],
        label='Rol',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'role']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'username':   forms.TextInput(attrs={'class': 'form-control'}),
            'email':      forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'first_name': 'Ism',
            'last_name':  'Familiya',
            'username':   'Foydalanuvchi nomi',
            'email':      'Email',
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Bu email allaqachon ro\'yxatdan o\'tgan.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('Bu username band.')
        return username

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Parollar mos kelmadi.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.is_active = False  # email tasdiqlash kerak
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'})
    )
    password = forms.CharField(
        label='Parol',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    remember_me = forms.BooleanField(required=False, label='Eslab qolish')


class ProfileUpdateForm(forms.ModelForm):
    skills_input = forms.CharField(
        required=False, label='Ko\'nikmalar (vergul bilan)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Python, Django, React'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'company', 'bio', 'portfolio_url', 'avatar', 'contact_public']
        widgets = {
            'first_name':     forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':      forms.TextInput(attrs={'class': 'form-control'}),
            'phone':          forms.TextInput(attrs={'class': 'form-control'}),
            'company':        forms.TextInput(attrs={'class': 'form-control'}),
            'bio':            forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'portfolio_url':  forms.URLInput(attrs={'class': 'form-control'}),
            'avatar':         forms.FileInput(attrs={'class': 'form-control'}),
            'contact_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.skills:
            self.fields['skills_input'].initial = ', '.join(self.instance.skills)

    def save(self, commit=True):
        user = super().save(commit=False)
        raw = self.cleaned_data.get('skills_input', '')
        user.skills = [s.strip() for s in raw.split(',') if s.strip()] if raw else []
        if commit:
            user.save()
        return user


class PasswordChangeForm(DjangoPasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs['class'] = 'form-control'


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        if not User.objects.filter(email=email, is_active=True).exists():
            raise ValidationError('Bu email bilan faol foydalanuvchi topilmadi.')
        return email


class SetPasswordForm(DjangoSetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs['class'] = 'form-control'



class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['requirements']
        widgets = {
            'requirements': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 5,
                'placeholder': 'Loyiha haqida qo\'shimcha ma\'lumot kiriting...'
            })
        }
        labels = {'requirements': 'Talablar va izohlar'}


class OrderAcceptForm(forms.Form):
    deadline_days = forms.IntegerField(
        min_value=1, max_value=90,
        label='Bajarish muddati (kun)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'value': 7})
    )


class OrderRejectForm(forms.Form):
    reason = forms.CharField(
        label='Rad etish sababi',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )


class OrderRevisionForm(forms.Form):
    reason = forms.CharField(
        label='Tuzatish talabi',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )


class OrderDisputeForm(forms.Form):
    reason = forms.CharField(
        label='Nizo sababi',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )


class OrderCancelForm(forms.Form):
    reason = forms.CharField(
        label='Bekor qilish sababi',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )


class DeliveryForm(forms.Form):
    delivery_file = forms.FileField(
        required=False, label='Fayl yuklash',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    delivery_url = forms.URLField(
        required=False, label='URL (GitHub, drive va h.k.)',
        widget=forms.URLInput(attrs={'class': 'form-control'})
    )
    message = forms.CharField(
        required=False, label='Izoh',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('delivery_file') and not cleaned.get('delivery_url'):
            raise ValidationError('Fayl yoki URL dan kamida biri kerak.')
        return cleaned


class MessageForm(forms.Form):
    text = forms.CharField(
        required=False, label='',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Xabar yozing...'})
    )
    file = forms.FileField(
        required=False, label='',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('text') and not cleaned.get('file'):
            raise ValidationError('Xabar matni yoki fayl kerak.')
        return cleaned



class ReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i, f'{i} ⭐') for i in range(1, 6)],
        label='Reyting',
        widget=forms.RadioSelect
    )

    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4})
        }
        labels = {'comment': 'Sharh matni'}



class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['reported_user', 'reason', 'description', 'order']
        widgets = {
            'reported_user': forms.Select(attrs={'class': 'form-control'}),
            'reason':        forms.Select(attrs={'class': 'form-control'}),
            'description':   forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'order':         forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'reported_user': 'Shikoyat qilinayotgan foydalanuvchi',
            'reason':        'Sabab',
            'description':   'Batafsil tavsif',
            'order':         'Bog\'liq buyurtma (ixtiyoriy)',
        }

    def clean(self):
        cleaned = super().clean()
        reported = cleaned.get('reported_user')
        return cleaned