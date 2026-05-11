import json
from decimal import Decimal
from django import forms
from .models import (
    Listing, Offer, WishlistItem, CATEGORY_CHOICES, SUBCATEGORY_CHOICES,
    SUBCATEGORY_FLAT_CHOICES, CONDITION_CHOICES,
)


class LoginForm(forms.Form):
    phone = forms.CharField(
        max_length=20,
        label='WhatsApp Number',
        widget=forms.TextInput(attrs={
            'placeholder': '024 XXX XXXX',
            'inputmode': 'numeric',
            'autofocus': True,
        }),
    )

    def clean_phone(self):
        raw = self.cleaned_data['phone'].strip().replace(' ', '').replace('-', '')
        if raw.startswith('+233'):
            local = raw[4:]
        elif raw.startswith('233'):
            local = raw[3:]
        elif raw.startswith('0'):
            local = raw[1:]
        else:
            local = raw
        if not local.isdigit() or len(local) != 9:
            raise forms.ValidationError('Enter a valid Ghanaian number, e.g. 024 XXX XXXX')
        return f'+233{local}'


class ListingForm(forms.ModelForm):
    subcategory = forms.ChoiceField(
        choices=[('', '— Select subcategory —')] + SUBCATEGORY_FLAT_CHOICES,
        label='Subcategory',
    )

    class Meta:
        model = Listing
        fields = [
            'title',
            'category',
            'subcategory',
            'description',
            'condition',
            'user_estimated_value',
            'location',
            'want_text',
            'image',
        ]
        labels = {
            'user_estimated_value': 'Your estimated value (GHS)',
            'want_text': 'What do you want in exchange?',
            'image': 'Photo (optional)',
        }
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. iPhone 12, 64GB'}),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe your item – condition, accessories included, etc.',
            }),
            'want_text': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'e.g. Looking for a laptop or GHS 1,500 cash',
            }),
            'user_estimated_value': forms.NumberInput(attrs={'min': 0, 'step': '0.01'}),
            'location': forms.TextInput(attrs={'placeholder': 'e.g. Accra, East Legon'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].choices = [('', '— Select category —')] + list(CATEGORY_CHOICES)
        self.subcategory_choices_json = json.dumps(SUBCATEGORY_CHOICES)

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and hasattr(image, 'size') and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Photo must be under 5 MB.')
        return image

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get('category')
        subcategory = cleaned.get('subcategory')
        if not subcategory:
            self.add_error('subcategory', 'Please select a subcategory.')
        elif category:
            valid = {slug for slug, _ in SUBCATEGORY_CHOICES.get(category, [])}
            if subcategory not in valid:
                self.add_error('subcategory', 'Select a valid subcategory for the chosen category.')
        return cleaned


class OfferForm(forms.ModelForm):
    offered_item_value = forms.DecimalField(
        required=False,
        min_value=Decimal('0'),
        label='Estimated value of your offered item (GHS)',
        widget=forms.NumberInput(attrs={
            'min': 0,
            'step': '0.01',
            'placeholder': '0.00',
            'id': 'id_offered_item_value',
        }),
        help_text='Leave 0 if you are only offering cash.',
    )

    cash_topup = forms.DecimalField(
        required=False,
        min_value=Decimal('0'),
        initial=Decimal('0'),
        label='Cash top-up you will add (GHS)',
        widget=forms.NumberInput(attrs={
            'min': 0,
            'step': '0.01',
            'placeholder': '0.00',
            'id': 'id_cash_topup',
        }),
    )

    class Meta:
        model = Offer
        fields = ['offered_item_description', 'cash_topup', 'message']
        labels = {
            'offered_item_description': 'What item are you offering? (optional)',
            'message': 'Message to seller (optional)',
        }
        widgets = {
            'offered_item_description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'e.g. Samsung Galaxy S21, good condition',
            }),
            'message': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Any message for the seller…',
            }),
        }

    def clean(self):
        cleaned = super().clean()
        description = (cleaned.get('offered_item_description') or '').strip()
        cash = cleaned.get('cash_topup') or Decimal('0')
        if not description and cash == Decimal('0'):
            raise forms.ValidationError(
                'Please offer at least an item or a cash amount — your offer cannot be empty.'
            )
        return cleaned


class WishlistItemForm(forms.ModelForm):
    class Meta:
        model = WishlistItem
        fields = ['title', 'category', 'description', 'max_budget']
        labels = {
            'title': 'What are you looking for?',
            'max_budget': 'Max budget (GHS, optional)',
        }
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. MacBook Pro, PlayStation 5'}),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Any specific details — model, size, condition preference…',
            }),
            'max_budget': forms.NumberInput(attrs={'min': 0, 'step': '0.01', 'placeholder': '0.00'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].choices = [('', '— Any category —')] + list(CATEGORY_CHOICES)
        self.fields['category'].required = False
