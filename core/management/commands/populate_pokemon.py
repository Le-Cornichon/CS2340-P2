
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Pokemon
import random


class Command(BaseCommand):
    help = 'Fetches Pokémon data from PokéAPI and populates the database'

    def get_rarity(self, pokedex_id):
        if pokedex_id in [150, 151]:
            return 'Mythic'
        if pokedex_id > 140:
            return 'Rare'
        elif pokedex_id > 100:
            return 'Uncommon'
        else:
            return 'Common'

    def handle(self, *args, **options):
        self.stdout.write('Fetching Pokémon data from PokéAPI...')
        POKEAPI_BASE_URL = 'https://pokeapi.co/api/v2/pokemon/'
        limit = settings.POKEMON_DATA_FETCH_LIMIT

        created_count = 0
        skipped_count = 0

        for i in range(1, limit + 1):
            pokemon_url = f"{POKEAPI_BASE_URL}{i}/"
            try:
                response = requests.get(pokemon_url, timeout=10)
                response.raise_for_status()
                data = response.json()

                pokedex_id = data['id']

                if Pokemon.objects.filter(pokedex_id=pokedex_id).exists():
                    self.stdout.write(self.style.WARNING(
                        f'Skipping #{pokedex_id}: {data["name"]} - Already exists.'))
                    skipped_count += 1
                    continue

                name = data['name']
                types = data['types']
                type1 = types[0]['type']['name']
                type2 = types[1]['type']['name'] if len(types) > 1 else None
                image_url = data['sprites']['other']['official-artwork']['front_default']

                rarity = self.get_rarity(pokedex_id)

                Pokemon.objects.create(
                    pokedex_id=pokedex_id,
                    name=name,
                    type1=type1,
                    type2=type2,
                    rarity=rarity,
                    image_url=image_url
                )
                created_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'Successfully added #{pokedex_id}: {name.capitalize()} ({rarity})'))

            except requests.exceptions.RequestException as e:
                self.stderr.write(self.style.ERROR(
                    f'Error fetching data for Pokémon ID {i}: {e}'))
            except Exception as e:
                self.stderr.write(self.style.ERROR(
                    f'An error occurred processing Pokémon ID {i}: {e}'))

        self.stdout.write(self.style.SUCCESS(
            f'\nPokémon population complete. Added: {created_count}, Skipped: {skipped_count}'))
