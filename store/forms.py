from django import forms


class BankDetailsForm(forms.Form):
    bank_code = forms.ChoiceField(label='Bank', choices=[])
    account_number = forms.RegexField(
        regex=r'^\d{10}$',
        label='Account number',
        max_length=10,
        error_messages={'invalid': 'Enter a valid 10-digit account number.'},
    )

    def __init__(self, *args, banks=None, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [('', 'Select your bank')]
        choices += [(b['code'], b['name']) for b in (banks or [])]
        self.fields['bank_code'].choices = choices