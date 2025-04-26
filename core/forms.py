from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CollectionItem, Pokemon, UserProfile

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True

class InitiateTradeForm(forms.Form):
    receiver_username = forms.CharField(max_length=150, label="Receiver's Username")
    offered_item = forms.ModelChoiceField(
        queryset=CollectionItem.objects.none(),
        label="Pokémon You Offer",
        empty_label=None
    )
    requested_pokemon = forms.ModelChoiceField(
        queryset=Pokemon.objects.all().order_by('name'),
        label="Pokémon You Want",
        empty_label=None
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.fields['offered_item'].queryset = CollectionItem.objects.filter(owner=user.profile).select_related('pokemon')
        except UserProfile.DoesNotExist:
             self.fields['offered_item'].queryset = CollectionItem.objects.none()


    def clean_receiver_username(self):
        username = self.cleaned_data['receiver_username']
        if username.lower() == self.user.username.lower():
             raise forms.ValidationError("You cannot trade with yourself.")
        try:
            User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            raise forms.ValidationError(f"User '{username}' not found.")
        return username

class ListItemForm(forms.Form):
    price = forms.IntegerField(
        min_value=1,
        required=True,
        label="Set Price (Coins)",
        widget=forms.NumberInput(attrs={'placeholder': 'Enter price'})
    )