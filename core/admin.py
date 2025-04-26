from pyexpat.errors import messages
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User 
from .models import (
    Pokemon, UserProfile, CollectionItem, TradeOffer, MarketplaceListing, TransactionHistory,
    PokemonPack, PackRarityOdds, Notification, TradingEvent
)

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'
    fk_name = 'user'
    fields = ('in_game_currency', 'last_login_bonus')
    readonly_fields = ('last_login_bonus',)

class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_currency', 'date_joined')
    list_select_related = ('profile',)
    list_filter = BaseUserAdmin.list_filter + ('profile__last_login_bonus',)
    search_fields = BaseUserAdmin.search_fields + ('profile__user__username',)

    def get_currency(self, instance):
        if hasattr(instance, 'profile'):
            return instance.profile.in_game_currency
        return 'N/A'
    get_currency.short_description = 'Currency' 
    get_currency.admin_order_field = 'profile__in_game_currency'

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin) 
admin.site.register(CollectionItem)
admin.site.register(Notification)



@admin.register(TradeOffer) 
class TradeOfferAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'offered_item_display', 'requested_pokemon', 'status', 'is_suspicious', 'created_at')
    list_filter = ('status', 'is_suspicious', 'created_at', 'sender__user__username', 'receiver__user__username')
    search_fields = ('sender__user__username', 'receiver__user__username', 'requested_pokemon__name', 'offered_item__pokemon__name')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_suspicious',)

    def offered_item_display(self, obj):
        return f"{obj.offered_item.pokemon.name.capitalize()} (ID: {obj.offered_item.id}, Rarity: {obj.offered_item.pokemon.rarity})"
    offered_item_display.short_description = 'Offered Item'

@admin.register(MarketplaceListing) 
class MarketplaceListingAdmin(admin.ModelAdmin):
    pass

@admin.register(TransactionHistory)
class TransactionHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction_type', 'user_profile_display', 'seller_display', 'pack_purchased', 'pokemon_display', 'price', 'timestamp')
    list_filter = ('transaction_type', 'timestamp')
    search_fields = ('user_profile__user__username', 'seller__user__username', 'pokemon__name', 'pack_purchased__name', 'trade_offer__id')

    def user_profile_display(self, obj):
         return obj.user_profile.user.username if obj.user_profile else 'N/A'
    user_profile_display.short_description = 'User'

    def seller_display(self, obj):
        return obj.seller.user.username if obj.seller else 'N/A'
    seller_display.short_description = 'Seller'

    def pokemon_display(self, obj):
        return obj.pokemon.name.capitalize() if obj.pokemon else 'N/A'
    pokemon_display.short_description = 'Pokémon'

class PackRarityOddsInline(admin.TabularInline):
    model = PackRarityOdds
    extra = 1
    fields = ('rarity', 'probability')

@admin.register(PokemonPack)
class PokemonPackAdmin(admin.ModelAdmin):
    list_display = ('name', 'cost', 'is_available', 'description')
    list_filter = ('is_available',)
    search_fields = ('name', 'description')
    inlines = [PackRarityOddsInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        try:
            pack = form.instance
            total_prob = 0
            for inline_form in formsets[0]:
                 if inline_form.cleaned_data and not inline_form.cleaned_data.get('DELETE'):
                     probability = inline_form.cleaned_data.get('probability', 0)
                     total_prob += probability if probability else 0

            if not (0.999 < total_prob < 1.001):
                 self.message_user(
                     request,
                     f"Warning: Probabilities for pack '{pack.name}' sum to {total_prob:.4f}, which is not 1.0. Please correct the odds.",
                     level=messages.WARNING
                 )
        except Exception as e:
            self.message_user(request, f"Could not validate probability sum: {e}", level=messages.ERROR)

@admin.register(TradingEvent)
class TradingEventAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_active')
    list_filter = ('start_date', 'end_date')
    search_fields = ('name', 'description')
