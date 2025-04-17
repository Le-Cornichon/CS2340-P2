from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Avg
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.pack_strategies import get_pack_strategy

from .forms import CustomUserCreationForm, InitiateTradeForm, ListItemForm
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
def initiate_trade(request):
    if request.method == 'POST':
        form = InitiateTradeForm(user=request.user, data=request.POST)
        form.user = request.user

        if form.is_valid():
            try:
                sender_profile = request.user.profile
                receiver_user = User.objects.get(username__iexact=form.cleaned_data['receiver_username'])
                receiver_profile = receiver_user.profile
                offered_item = form.cleaned_data['offered_item']
                requested_pokemon = form.cleaned_data['requested_pokemon']

                if offered_item.owner != sender_profile:
                    messages.error(request, "You cannot offer a Pokémon you do not own.")
                    return render(request, 'core/initiate_trade.html', {'form': form})

                TradeOffer.objects.create(
                    sender=sender_profile,
                    receiver=receiver_profile,
                    offered_item=offered_item,
                    requested_pokemon=requested_pokemon,
                    status=TradeOffer.STATUS_PENDING
                )
                messages.success(request, f"Trade offer sent successfully to {receiver_user.username}!")
                return redirect('core:view_trades')

            except UserProfile.DoesNotExist:
                 messages.error(request, "Could not find profile for sender or receiver.")
            except User.DoesNotExist:
                 messages.error(request, "Receiver user not found (should have been caught by form validation).")
            except Exception as e:
                 logger.error(f"Error creating trade offer for {request.user.username}: {e}")
                 messages.error(request, "An unexpected error occurred while sending the offer.")

    else:
        form = InitiateTradeForm(user=request.user)

    return render(request, 'core/initiate_trade.html', {'form': form})


@login_required
def view_trades(request):
    try:
        user_profile = request.user.profile
        incoming_offers = TradeOffer.objects.filter(
            receiver=user_profile, status=TradeOffer.STATUS_PENDING
        ).select_related('sender__user', 'offered_item__pokemon', 'requested_pokemon')

        outgoing_offers = TradeOffer.objects.filter(
            sender=user_profile, status=TradeOffer.STATUS_PENDING
        ).select_related('receiver__user', 'offered_item__pokemon', 'requested_pokemon')

        completed_offers = TradeOffer.objects.filter(
            Q(sender=user_profile) | Q(receiver=user_profile),
            status__in=[TradeOffer.STATUS_ACCEPTED, TradeOffer.STATUS_REJECTED, TradeOffer.STATUS_CANCELLED]
        ).select_related('sender__user', 'receiver__user', 'offered_item__pokemon', 'requested_pokemon').order_by('-updated_at')[:20] # Limit history


        context = {
            'incoming_offers': incoming_offers,
            'outgoing_offers': outgoing_offers,
            'completed_offers': completed_offers,
        }
        return render(request, 'core/trade_list.html', context)
    except UserProfile.DoesNotExist:
        messages.error(request, "Your profile could not be found.")
        return redirect('core:index')


@login_required
def view_trade_offer(request, offer_id):
    offer = get_object_or_404(TradeOffer.objects.select_related(
        'sender__user', 'receiver__user', 'offered_item__pokemon', 'requested_pokemon'
        ), id=offer_id)

    if request.user.profile != offer.sender and request.user.profile != offer.receiver:
        messages.error(request, "You do not have permission to view this trade offer.")
        return redirect('core:view_trades')

    is_receiver = request.user.profile == offer.receiver
    is_sender = request.user.profile == offer.sender

    context = {
        'offer': offer,
        'is_receiver': is_receiver,
        'is_sender': is_sender,
    }
    return render(request, 'core/trade_offer_detail.html', context)


@login_required
@transaction.atomic
def accept_trade_offer(request, offer_id):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('core:view_trades')

    offer = get_object_or_404(TradeOffer, id=offer_id)
    receiver_profile = request.user.profile

    if offer.receiver != receiver_profile:
        messages.error(request, "You cannot accept this offer.")
        return redirect('core:view_trades')
    if offer.status != TradeOffer.STATUS_PENDING:
        messages.warning(request, f"This offer is no longer pending (Status: {offer.status}).")
        return redirect('core:view_trades')

    sender_profile = offer.sender
    offered_item = offer.offered_item
    requested_pokemon = offer.requested_pokemon

    offered_item = CollectionItem.objects.select_for_update().get(id=offer.offered_item.id)
    if offered_item.owner != sender_profile:
        offer.status = TradeOffer.STATUS_REJECTED
        offer.save()
        messages.error(request, "Trade failed: Sender no longer owns the offered Pokémon.")
        logger.warning(f"TradeAcceptFail (Item Owner Changed): Offer {offer.id}, Sender {sender_profile.user.username}, Item {offered_item.id}")
        return redirect('core:view_trades')

    receiver_items_match = CollectionItem.objects.select_for_update().filter(
        owner=receiver_profile,
        pokemon=requested_pokemon
    )

    if not receiver_items_match.exists():
        messages.error(request, f"Trade failed: You do not own a {requested_pokemon.name.capitalize()} to trade.")
        logger.warning(f"TradeAcceptFail (Receiver Lacks Item): Offer {offer.id}, Receiver {receiver_profile.user.username}, Requested {requested_pokemon.name}")
        return redirect('core:view_trade_offer', offer_id=offer.id)

    item_to_give = receiver_items_match.first()

    offered_item.owner = receiver_profile
    offered_item.obtained_at = timezone.now()
    offered_item.save()

    item_to_give.owner = sender_profile
    item_to_give.obtained_at = timezone.now()
    item_to_give.save()

    offer.status = TradeOffer.STATUS_ACCEPTED
    offer.save()

    TransactionHistory.objects.create(
        transaction_type=TransactionHistory.TRANSACTION_TRADE,
        trade_offer=offer,
        timestamp=timezone.now()
    )
   
    logger.info(f"Trade Accepted: Offer {offer.id} between {sender_profile.user.username} and {receiver_profile.user.username}.")

    messages.success(request, "Trade accepted successfully!")
    return redirect('core:view_trades')


@login_required
def reject_trade_offer(request, offer_id):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('core:view_trades')

    offer = get_object_or_404(TradeOffer, id=offer_id)

    if offer.receiver != request.user.profile:
        messages.error(request, "You cannot reject this offer.")
        return redirect('core:view_trades')
    if offer.status != TradeOffer.STATUS_PENDING:
        messages.warning(request, f"This offer is no longer pending (Status: {offer.status}).")
        return redirect('core:view_trades')

    offer.status = TradeOffer.STATUS_REJECTED
    offer.save()

    logger.info(f"Trade Rejected: Offer {offer.id} from {offer.sender.user.username} to {offer.receiver.user.username}")

    messages.info(request, "Trade offer rejected.")
    return redirect('core:view_trades')


@login_required
def cancel_trade_offer(request, offer_id):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('core:view_trades')

    offer = get_object_or_404(TradeOffer, id=offer_id)

    if offer.sender != request.user.profile:
        messages.error(request, "You cannot cancel this offer.")
        return redirect('core:view_trades')
    if offer.status != TradeOffer.STATUS_PENDING:
        messages.warning(request, f"This offer is no longer pending (Status: {offer.status}).")
        return redirect('core:view_trades')

    offer.status = TradeOffer.STATUS_CANCELLED
    offer.save()

    logger.info(f"Trade Cancelled: Offer {offer.id} from {offer.sender.user.username} to {offer.receiver.user.username}")

    messages.info(request, "Trade offer cancelled.")
    return redirect('core:view_trades')


@login_required
def list_item(request, item_id):
    item_to_list = get_object_or_404(CollectionItem, id=item_id)
    user_profile = request.user.profile

    if item_to_list.owner != user_profile:
        messages.error(request, "You do not own this Pokémon.")
        return redirect('core:view_collection')

    existing_listing = None
    if hasattr(item_to_list, 'listing'):
        existing_listing = item_to_list.listing

        if existing_listing.status == MarketplaceListing.STATUS_AVAILABLE:
            messages.warning(request, "This Pokémon is already listed on the marketplace.")
            return redirect('core:view_listing_detail', listing_id=existing_listing.id)

    if request.method == 'POST':
        form = ListItemForm(request.POST)
        if form.is_valid():
            price = form.cleaned_data['price']
            try:
                if existing_listing and existing_listing.status in [MarketplaceListing.STATUS_CANCELLED, MarketplaceListing.STATUS_SOLD]:
                    existing_listing.price = price
                    existing_listing.seller = user_profile
                    existing_listing.status = MarketplaceListing.STATUS_AVAILABLE
                    existing_listing.listed_at = timezone.now()
                    existing_listing.sold_at = None
                    existing_listing.save()
                    action_message = "re-listed"
                elif not existing_listing:
                    MarketplaceListing.objects.create(
                        item=item_to_list,
                        seller=user_profile,
                        price=price,
                        status=MarketplaceListing.STATUS_AVAILABLE
                    )
                    action_message = "listed"
                else:
                     messages.error(request, f"Cannot list item due to unexpected existing listing status: {existing_listing.status}")
                     return redirect('core:view_collection')


                messages.success(request, f"{item_to_list.pokemon.name.capitalize()} successfully {action_message} for sale at {price} Coins!")
                return redirect('core:view_marketplace')

            except Exception as e:
                 logger.error(f"Error listing/re-listing item {item_id} for user {request.user.username}: {e}")
                 messages.error(request, f"An error occurred while listing the item. Error: {e}")
    else:
        form = ListItemForm()

    context = {
        'form': form,
        'item_to_list': item_to_list,
        'existing_listing_status': existing_listing.status if existing_listing else None
    }
    return render(request, 'core/list_item_form.html', context)


def view_marketplace(request):
    listings = MarketplaceListing.objects.filter(status=MarketplaceListing.STATUS_AVAILABLE).select_related(
        'item__pokemon', 'seller__user'
    ).order_by('-listed_at')

    pokemon_list = Pokemon.objects.filter(
        pk__in=listings.values_list('item__pokemon_id', flat=True).distinct()
        ).order_by('name')

    selected_pokemon_id = request.GET.get('pokemon_id', '')
    if selected_pokemon_id and selected_pokemon_id.isdigit():
        listings = listings.filter(item__pokemon_id=int(selected_pokemon_id))

    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_asc':
        listings = listings.order_by('price')
    elif sort_by == 'price_desc':
        listings = listings.order_by('-price')
    elif sort_by == 'oldest':
         listings = listings.order_by('listed_at')

    context = {
        'listings': listings,
        'pokemon_list': pokemon_list,
        'selected_pokemon_id': selected_pokemon_id,
        'sort_by': sort_by,
    }
    return render(request, 'core/marketplace.html', context)


def view_listing_detail(request, listing_id):
    listing = get_object_or_404(MarketplaceListing.objects.select_related(
        'item__pokemon', 'seller__user'
    ), id=listing_id)

    recent_sales = TransactionHistory.objects.filter(
        transaction_type=TransactionHistory.TRANSACTION_MARKET,
        pokemon=listing.item.pokemon,
    ).order_by('-timestamp')[:5]

    avg_price_data = TransactionHistory.objects.filter(
         transaction_type=TransactionHistory.TRANSACTION_MARKET,
         pokemon=listing.item.pokemon
    ).aggregate(average_price=Avg('price'))
    avg_price = avg_price_data.get('average_price')


    context = {
        'listing': listing,
        'recent_sales': recent_sales,
        'average_sale_price': avg_price,
    }
    return render(request, 'core/listing_detail.html', context)


@login_required
@transaction.atomic
def purchase_listing(request, listing_id):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('core:view_marketplace')

    listing = get_object_or_404(MarketplaceListing.objects.select_for_update(), id=listing_id)
    buyer_profile = request.user.profile
    seller_profile = listing.seller
    item_to_buy = listing.item

    if listing.status != MarketplaceListing.STATUS_AVAILABLE:
        messages.error(request, "This item is no longer available for sale.")
        return redirect('core:view_marketplace')
    if buyer_profile == seller_profile:
        messages.error(request, "You cannot buy your own listing.")
        return redirect('core:view_listing_detail', listing_id=listing.id)
    if buyer_profile.in_game_currency < listing.price:
        messages.error(request, "You do not have enough Coins to purchase this item.")
        return redirect('core:view_listing_detail', listing_id=listing.id)

    item_to_buy = CollectionItem.objects.select_for_update().get(id=listing.item.id)
    if item_to_buy.owner != seller_profile:
         listing.status = MarketplaceListing.STATUS_CANCELLED
         listing.save()
         messages.error(request, "Purchase failed: Seller no longer owns this item.")
         logger.warning(f"MarketPurchaseFail (Item Owner Changed): Listing {listing.id}, Buyer {buyer_profile.user.username}")
         return redirect('core:view_marketplace')


    buyer_profile.in_game_currency -= listing.price
    seller_profile.in_game_currency += listing.price

    item_to_buy.owner = buyer_profile
    item_to_buy.obtained_at = timezone.now()

    listing.status = MarketplaceListing.STATUS_SOLD
    listing.sold_at = timezone.now()

    buyer_profile.save()
    seller_profile.save()
    item_to_buy.save()
    listing.save()

    TransactionHistory.objects.create(
        transaction_type=TransactionHistory.TRANSACTION_MARKET,
        buyer=buyer_profile,
        seller=seller_profile,
        collection_item=item_to_buy,
        pokemon=item_to_buy.pokemon,
        price=listing.price
    )

    logger.info(f"Market Purchase: Buyer {buyer_profile.user.username} bought Item {item_to_buy.id} "
                f"({item_to_buy.pokemon.name}) from Seller {seller_profile.user.username} "
                f"for {listing.price} Coins. Listing {listing.id}")

    messages.success(request, f"Successfully purchased {item_to_buy.pokemon.name.capitalize()} for {listing.price} Coins!")
    return redirect('core:view_collection')


@login_required
def cancel_listing(request, listing_id):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('core:view_marketplace')

    listing = get_object_or_404(MarketplaceListing, id=listing_id)
    user_profile = request.user.profile

    if listing.seller != user_profile:
        messages.error(request, "You cannot cancel this listing.")
        return redirect('core:view_marketplace')
    if listing.status != MarketplaceListing.STATUS_AVAILABLE:
        messages.warning(request, "This listing cannot be cancelled (Status: {listing.status}).")
        return redirect('core:view_marketplace')

    listing.status = MarketplaceListing.STATUS_CANCELLED
    listing.save()

    logger.info(f"Market Listing Cancelled: Listing {listing.id} by Seller {user_profile.user.username}")
    messages.info(request, "Your marketplace listing has been cancelled.")
    return redirect('core:view_collection') 

@login_required
def view_notifications(request):
    try:
        user_profile = request.user.profile
        notifications = Notification.objects.filter(recipient=user_profile)

        unread_notifications = notifications.filter(is_read=False)
        unread_notifications.update(is_read=True)

        context = {
            'notifications': notifications
        }
        return render(request, 'core/notifications.html', context)

    except UserProfile.DoesNotExist:
        messages.error(request, "Your profile could not be found.")
        return redirect('core:index')
    
@login_required
def view_transaction_history(request):
    try:
        user_profile = request.user.profile

        history_list = TransactionHistory.objects.filter(
            Q(user_profile=user_profile) |
            Q(seller=user_profile) |
            Q(trade_offer__sender=user_profile) |
            Q(trade_offer__receiver=user_profile)
        ).select_related(
            'user_profile__user',
            'seller__user',
            'pokemon',
            'trade_offer__sender__user',
            'trade_offer__receiver__user',
            'trade_offer__offered_item__pokemon',
            'trade_offer__requested_pokemon'
        ).distinct().order_by('-timestamp')

        page = request.GET.get('page', 1)
        paginator = Paginator(history_list, 15)

        try:
            history_page = paginator.page(page)
        except PageNotAnInteger:
            history_page = paginator.page(1)
        except EmptyPage:
            history_page = paginator.page(paginator.num_pages)


        context = {
            'history_page': history_page
        }
        return render(request, 'core/transaction_history.html', context)

    except UserProfile.DoesNotExist:
        messages.error(request, "Your profile could not be found.")
        return redirect('core:index')
    except Exception as e:
        logger.error(f"Error fetching transaction history for {request.user.username}: {e}")
        messages.error(request, "An error occurred while fetching your transaction history.")
        return redirect('core:index')

@login_required
def view_store(request):
    context = {
        'page_title': 'PokéTrade Store'
    }
    return render(request, 'core/store.html', context)

@login_required
def view_packs(request):
    available_packs = PokemonPack.objects.filter(is_available=True)
    context = {
        'packs': available_packs,
        'page_title': 'Available Packs'
    }
    return render(request, 'core/pack_list.html', context)

@login_required
def view_pack_odds(request, pack_id):
    pack = get_object_or_404(PokemonPack, id=pack_id)
    odds = PackRarityOdds.objects.filter(pack=pack).order_by('-probability')
    context = {
        'pack': pack,
        'odds': odds,
        'page_title': f'{pack.name} Rarity Odds'
    }
    return render(request, 'core/pack_odds.html', context)

@login_required
@transaction.atomic
def purchase_pack(request, pack_id):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('core:view_packs')

    pack = get_object_or_404(PokemonPack, id=pack_id, is_available=True)
    user_profile = request.user.profile

    if user_profile.in_game_currency < pack.cost:
        messages.error(request, f"You need {pack.cost} Coins to buy the '{pack.name}', but you only have {user_profile.in_game_currency}.")
        return redirect('core:view_packs')

    profile_in_txn = UserProfile.objects.select_for_update().get(pk=user_profile.pk)
    if profile_in_txn.in_game_currency < pack.cost:
         messages.error(request, "Insufficient funds (checked again). Purchase cancelled.")
         return redirect('core:view_packs')

    profile_in_txn.in_game_currency -= pack.cost
    profile_in_txn.save()

    strategy = get_pack_strategy(pack)
    try:
        awarded_items = strategy.open_pack(pack=pack, user_profile=profile_in_txn)
    except Exception as e:
        logger.error(f"Error opening pack {pack.id} for user {profile_in_txn.user.username} using strategy {type(strategy).__name__}: {e}")
        messages.error(request, "An error occurred while opening the pack. Your currency has not been charged.")
        profile_in_txn.in_game_currency += pack.cost 
        profile_in_txn.save()
        return redirect('core:view_packs')


    TransactionHistory.objects.create(
        transaction_type=TransactionHistory.TRANSACTION_PACK_PURCHASE,
        user_profile=profile_in_txn,
        pack_purchased=pack,
        price=pack.cost
    )

    if awarded_items:
        awarded_names = ", ".join([item.pokemon.name.capitalize() for item in awarded_items])
        messages.success(request, f"You opened a {pack.name} and received: {awarded_names}! They have been added to your collection.")
    else:
        messages.warning(request, f"You opened a {pack.name}, but unfortunately it was empty this time.")

    logger.info(f"User {profile_in_txn.user.username} purchased pack {pack.id} ('{pack.name}') for {pack.cost}. Awarded {len(awarded_items)} items.")

    return redirect('core:view_collection')

@login_required
@require_POST
@transaction.atomic
def purchase_currency(request):

    AMOUNT_TO_ADD = 1000
    try:
        profile = UserProfile.objects.select_for_update().get(user=request.user)
        profile.in_game_currency += AMOUNT_TO_ADD
        profile.save()

        TransactionHistory.objects.create(
            transaction_type=TransactionHistory.TRANSACTION_CURRENCY_PURCHASE,
            user_profile=profile,
            price=AMOUNT_TO_ADD
        )

        messages.success(request, f"Successfully added {AMOUNT_TO_ADD} Coins to your balance! (Simulated Purchase)")
        logger.info(f"User {profile.user.username} 'purchased' {AMOUNT_TO_ADD} currency.")

    except UserProfile.DoesNotExist:
        messages.error(request, "Could not find your profile.")
    except Exception as e:
        messages.error(request, "An error occurred during the simulated purchase.")
        logger.error(f"Error during simulated currency purchase for {request.user.username}: {e}")

    return redirect('core:view_store')


