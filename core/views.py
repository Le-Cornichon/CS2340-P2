from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from .models import (
    CollectionItem,
    Notification,
    PackRarityOdds,
    Pokemon,
    PokemonPack,
    UserProfile,
    TradeOffer,
    MarketplaceListing,
    TransactionHistory
)

import logging
logger = logging.getLogger(__name__)

def index(request):
    context = {
        'message': "Welcome to PokéTrade!"
    }
    return render(request, 'core/index.html', context)


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('core:index')
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/register.html', {'form': form})


def search_pokemon(request):
    query = request.GET.get('q', '')
    results = []
    searched = False

    if query:
        searched = True
        results = Pokemon.objects.filter(name__icontains=query).order_by('pokedex_id')

    context = {
        'query': query,
        'results': results,
        'searched': searched,
    }
    return render(request, 'core/search_results.html', context)


@login_required
def view_collection(request):
    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)
        print(f"Warning: UserProfile created on-the-fly for {request.user.username}")

    collection_items_base = CollectionItem.objects.filter(owner=user_profile).select_related('pokemon')

    types1 = collection_items_base.values_list('pokemon__type1', flat=True)
    types2 = collection_items_base.exclude(pokemon__type2__isnull=True).exclude(pokemon__type2='').values_list('pokemon__type2', flat=True)
    available_types = sorted(list(set(list(types1) + list(types2))))

    all_rarities_from_db = collection_items_base.values_list('pokemon__rarity', flat=True)
    available_rarities = sorted(list(set(all_rarities_from_db)))


    collection_items_filtered = collection_items_base
    selected_type = request.GET.get('type', '')
    selected_rarity = request.GET.get('rarity', '')

    if selected_type:
        collection_items_filtered = collection_items_filtered.filter(
            Q(pokemon__type1__iexact=selected_type) | Q(pokemon__type2__iexact=selected_type)
        )

    if selected_rarity:
        collection_items_filtered = collection_items_filtered.filter(pokemon__rarity__iexact=selected_rarity)

    context = {
        'collection_items': collection_items_filtered.order_by('pokemon__pokedex_id'),
        'available_types': available_types,
        'available_rarities': available_rarities,
        'selected_type': selected_type,
        'selected_rarity': selected_rarity,
    }
    return render(request, 'core/collection.html', context)
