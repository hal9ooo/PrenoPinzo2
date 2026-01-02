from django import forms
from .models import Booking

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['title', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start_date")
        end = cleaned_data.get("end_date")

        if start and end and start >= end:
            raise forms.ValidationError("La data di fine deve essere successiva alla data di inizio.")
        return cleaned_data

class DerogaForm(forms.Form):
    new_start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    new_end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    note = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("new_start_date")
        end = cleaned_data.get("new_end_date")

        if start and end and start >= end:
            raise forms.ValidationError("La data di fine deve essere successiva alla data di inizio.")
        return cleaned_data

class RejectForm(forms.Form):
    note = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))

# Import UserProfile model inside the form file if not already imported, or verify import at top
from .models import UserProfile

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone', 'callmebot_apikey', 'whatsapp_enabled', 'avatar']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '+393331234567'
            }),
            'callmebot_apikey': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '123456'
            }),
            'whatsapp_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }
        labels = {
            'phone': 'Numero di Telefono (con prefisso)',
            'callmebot_apikey': 'CallMeBot API Key',
            'whatsapp_enabled': 'Abilita Notifiche WhatsApp',
            'avatar': 'Immagine Profilo'
        }
        help_texts = {
            'phone': 'Formato internazionale obbligatorio (es. +39...)',
            'callmebot_apikey': 'Richiedila inviando un messaggio a CallMeBot'
        }
