import json
from decimal import Decimal
from django import forms
from .models import (
    Listing, Offer, WishlistItem, CATEGORY_CHOICES, SUBCATEGORY_CHOICES,
    SUBCATEGORY_FLAT_CHOICES, CONDITION_CHOICES, GHANA_REGION_CHOICES,
    TRANSACTION_TYPE_CHOICES, LISTING_TYPE_CHOICES, LISTING_BEHAVIOUR_CHOICES,
    DURATION_CHOICES, COLLECTION_METHOD_CHOICES, CASH_TOPUP_DIRECTION_CHOICES,
    RENTAL_PERIOD_CHOICES, WANT_TYPE_CHOICES, TERM_TYPE_CHOICES,
    CONDITION_ACCEPTABLE_CHOICES, NOTIFICATION_FREQUENCY_CHOICES,
    CONTACT_REVEAL_CHOICES, BarterUser,
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
        required=False,
    )
    class Meta:
        model = Listing
        fields = [
            'transaction_type',
            'listing_type',
            'title',
            'category',
            'subcategory',
            'description',
            'condition',
            'listing_behaviour',
            'duration_days',
            'user_estimated_value',
            'location_region',
            'location_city',
            'location_neighbourhood',
            'want_text',
            'collection_method',
            'cash_topup_direction',
            # Category-specific
            'brand',
            'model_name',
            'size',
            'colour',
            'gender',
            'materials_used',
            'service_scope',
            'service_timeline_days',
            'repair_description',
            'warranty_offered',
            'warranty_duration_days',
            # Rental-specific
            'rental_period_unit',
            'rental_payment_description',
            'deposit_required',
            'deposit_description',
            'availability_notes',
            'rental_conditions',
        ]
        labels = {
            'user_estimated_value': 'Your estimated value (GHS)',
            'want_text': 'What do you want in exchange?',
            'location_region': 'Region',
            'location_city': 'City / Town',
            'location_neighbourhood': 'Neighbourhood (optional)',
            'listing_behaviour': 'Listing duration',
            'duration_days': 'Duration',
            'collection_method': 'Collection method',
            'cash_topup_direction': 'Cash top-up',
            'model_name': 'Model',
            'service_timeline_days': 'Delivery timeline (days)',
            'warranty_duration_days': 'Warranty duration (days)',
            'rental_period_unit': 'Rental period',
            'rental_payment_description': 'What payment do you accept for rental?',
            'deposit_description': 'Deposit details',
            'availability_notes': 'Availability',
            'rental_conditions': 'Rental conditions',
        }
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. iPhone 12, 64GB'}),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe your item – condition, accessories included, etc.',
            }),
            'want_text': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'e.g. Looking for a laptop, plants, or GHS 1,500 cash',
            }),
            'user_estimated_value': forms.NumberInput(attrs={'min': 0, 'step': '0.01'}),
            'location_city': forms.TextInput(attrs={'placeholder': 'e.g. Accra, Kumasi'}),
            'location_neighbourhood': forms.TextInput(attrs={'placeholder': 'e.g. East Legon, Osu'}),
            'brand': forms.TextInput(attrs={'placeholder': 'e.g. Apple, Samsung, Nike'}),
            'model_name': forms.TextInput(attrs={'placeholder': 'e.g. iPhone 12, Galaxy S21'}),
            'size': forms.TextInput(attrs={'placeholder': 'e.g. M, 42, 10'}),
            'colour': forms.TextInput(attrs={'placeholder': 'e.g. Black, White'}),
            'materials_used': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'e.g. Cotton yarn, resin, pine wood',
            }),
            'service_scope': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Describe what is included in this service or commission.',
            }),
            'repair_description': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'What was repaired or replaced?',
            }),
            'rental_payment_description': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'e.g. Canned drinks, cash, food items',
            }),
            'deposit_description': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'e.g. GHS 200 refundable deposit, or equivalent item',
            }),
            'availability_notes': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'e.g. Available weekends only, contact me to confirm',
            }),
            'rental_conditions': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'e.g. Must be collected and returned same day, no outdoor use',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].choices = [('', '— Select category —')] + list(CATEGORY_CHOICES)
        self.fields['location_region'].choices = [('', '— Select region —')] + list(GHANA_REGION_CHOICES)
        self.fields['duration_days'].required = False
        self.fields['condition'].required = False
        self.subcategory_choices_json = json.dumps(SUBCATEGORY_CHOICES)

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get('category')
        subcategory = cleaned.get('subcategory')
        listing_type = cleaned.get('listing_type')
        behaviour = cleaned.get('listing_behaviour')
        duration = cleaned.get('duration_days')

        if subcategory and category:
            valid = {slug for slug, _ in SUBCATEGORY_CHOICES.get(category, [])}
            if subcategory not in valid:
                self.add_error('subcategory', 'Select a valid subcategory for the chosen category.')

        if listing_type != 'service' and not cleaned.get('condition'):
            self.add_error('condition', 'Please select a condition.')

        if behaviour == 'temporary' and not duration:
            self.add_error('duration_days', 'Please select a duration for temporary listings.')

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
        fields = [
            'offered_item_description',
            'cash_topup',
            'message',
            'rental_start_date',
            'rental_end_date',
            'rental_payment_offered',
        ]
        labels = {
            'offered_item_description': 'What item are you offering? (optional)',
            'message': 'Message to seller (optional)',
            'rental_start_date': 'Rental start date',
            'rental_end_date': 'Rental end date',
            'rental_payment_offered': 'What are you offering as payment?',
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
            'rental_start_date': forms.DateInput(attrs={'type': 'date'}),
            'rental_end_date': forms.DateInput(attrs={'type': 'date'}),
            'rental_payment_offered': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'e.g. 2 crates of malt, GHS 100 cash',
            }),
        }

    def clean(self):
        cleaned = super().clean()
        description = (cleaned.get('offered_item_description') or '').strip()
        cash = cleaned.get('cash_topup') or Decimal('0')
        rental_payment = (cleaned.get('rental_payment_offered') or '').strip()
        if not description and cash == Decimal('0') and not rental_payment:
            raise forms.ValidationError(
                'Please describe what you are offering — an item, cash, or rental payment.'
            )
        return cleaned


class CounterOfferForm(forms.Form):
    counter_cash_topup = forms.DecimalField(
        min_value=Decimal('0'),
        label='Request cash top-up of (GHS)',
        widget=forms.NumberInput(attrs={'min': 0, 'step': '0.01', 'placeholder': '0.00'}),
    )
    counter_message = forms.CharField(
        required=False,
        label='Message to offerer (optional)',
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'e.g. I can accept your item but need GHS 300 top-up.',
        }),
    )


class WishlistItemForm(forms.ModelForm):
    class Meta:
        model = WishlistItem
        fields = [
            'title',
            'category',
            'description',
            'want_type',
            'term_type',
            'condition_acceptable',
            'size_preference',
            'notification_frequency',
            'max_budget',
        ]
        labels = {
            'title': 'What are you looking for?',
            'max_budget': 'Max budget (GHS, optional)',
            'want_type': 'Are you looking to acquire or rent?',
            'term_type': 'How urgent is this want?',
            'condition_acceptable': 'Minimum acceptable condition',
            'size_preference': 'Size preference (optional)',
            'notification_frequency': 'Notify me',
        }
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. MacBook Pro, PlayStation 5, potted plants'}),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Any specific details — model, size, colour, condition preference…',
            }),
            'max_budget': forms.NumberInput(attrs={'min': 0, 'step': '0.01', 'placeholder': '0.00'}),
            'size_preference': forms.TextInput(attrs={'placeholder': 'e.g. Size M, UK 10, 42 inches'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].choices = [('', '— Any category —')] + list(CATEGORY_CHOICES)
        self.fields['category'].required = False


class ProfileForm(forms.ModelForm):
    class Meta:
        model = BarterUser
        fields = [
            'name',
            'bio',
            'whatsapp_number',
            'location_region',
            'location_city',
            'location_neighbourhood',
            'contact_reveal_preference',
            'portfolio_url',
            'website_url',
        ]
        labels = {
            'name': 'Display name',
            'bio': 'About you (optional)',
            'whatsapp_number': 'WhatsApp number (if different from login)',
            'location_region': 'Region',
            'location_city': 'City / Town',
            'location_neighbourhood': 'Neighbourhood (optional)',
            'contact_reveal_preference': 'When to reveal my contact',
            'portfolio_url': 'Portfolio / Instagram link (optional)',
            'website_url': 'Website link (optional)',
        }
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Tell traders a bit about yourself…'}),
            'whatsapp_number': forms.TextInput(attrs={'placeholder': '024 XXX XXXX'}),
            'location_city': forms.TextInput(attrs={'placeholder': 'e.g. Accra, Kumasi'}),
            'location_neighbourhood': forms.TextInput(attrs={'placeholder': 'e.g. East Legon, Adum'}),
            'portfolio_url': forms.URLInput(attrs={'placeholder': 'https://instagram.com/yourhandle'}),
            'website_url': forms.URLInput(attrs={'placeholder': 'https://yoursite.com'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['location_region'].choices = [('', '— Select region —')] + list(GHANA_REGION_CHOICES)
        self.fields['location_region'].required = False
