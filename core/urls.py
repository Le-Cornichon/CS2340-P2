from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('collection/', views.view_collection, name='view_collection'),
    path('search/', views.search_pokemon, name='search_pokemon'),
    path('trades/', views.view_trades, name='view_trades'),
    path('trades/initiate/', views.initiate_trade, name='initiate_trade'),
    path('trades/offer/<int:offer_id>/', views.view_trade_offer, name='view_trade_offer'),
    path('trades/offer/<int:offer_id>/accept/', views.accept_trade_offer, name='accept_trade_offer'),
    path('trades/offer/<int:offer_id>/reject/', views.reject_trade_offer, name='reject_trade_offer'),
    path('trades/offer/<int:offer_id>/cancel/', views.cancel_trade_offer, name='cancel_trade_offer'),
    path('marketplace/', views.view_marketplace, name='view_marketplace'),
    path('marketplace/list/<int:item_id>/', views.list_item, name='list_item'),
    path('marketplace/listing/<int:listing_id>/', views.view_listing_detail, name='view_listing_detail'),
    path('marketplace/listing/<int:listing_id>/purchase/', views.purchase_listing, name='purchase_listing'),
    path('marketplace/listing/<int:listing_id>/cancel/', views.cancel_listing, name='cancel_listing'),
    path('notifications/', views.view_notifications, name='view_notifications'),
    path('history/', views.view_transaction_history, name='view_transaction_history'),
    path('store/', views.view_store, name='view_store'),
    path('store/packs/', views.view_packs, name='view_packs'),
    path('store/packs/<int:pack_id>/odds/', views.view_pack_odds, name='view_pack_odds'),
    path('store/packs/<int:pack_id>/purchase/', views.purchase_pack, name='purchase_pack'),
    path('store/currency/purchase/', views.purchase_currency, name='purchase_currency'),
]