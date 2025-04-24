import random
from abc import ABC, abstractmethod
from .models import Pokemon, PackRarityOdds, CollectionItem, UserProfile
from typing import List, Union


class PackOpeningStrategy(ABC):

    @abstractmethod
    def open_pack(self, pack, user_profile) -> List[CollectionItem]:
        pass

    def _get_pokemon_by_rarity(self, rarity: str) -> List[Pokemon]: 
        return list(Pokemon.objects.filter(rarity=rarity))

    def _select_pokemon_instance(self, pokemon_list: List[Pokemon]) -> Union[Pokemon, None]: 
        if not pokemon_list:
            return None
        return random.choice(pokemon_list)

class StandardPackStrategy(PackOpeningStrategy):

    NUM_POKEMON_PER_PACK = 5

    def open_pack(self, pack, user_profile) -> List[CollectionItem]:
        awarded_items = []
        odds = PackRarityOdds.objects.filter(pack=pack).order_by('probability')
        if not odds:
            print(f"Warning: Pack '{pack.name}' has no rarity odds defined.")
            return []

        rarities = [o.rarity for o in odds]
        probabilities = [o.probability for o in odds]

        prob_sum = sum(probabilities)
        if prob_sum > 0 and not (0.999 < prob_sum < 1.001):
             probabilities = [p / prob_sum for p in probabilities]
             print(f"Warning: Probabilities for pack '{pack.name}' normalized from sum {prob_sum}.")
        elif prob_sum <= 0:
             print(f"Error: Probabilities for pack '{pack.name}' sum to {prob_sum}. Cannot open.")
             return []


        print(f"Opening pack '{pack.name}' for {user_profile.user.username}. Rarity draws:")

        for _ in range(self.NUM_POKEMON_PER_PACK):
            chosen_rarity = random.choices(rarities, weights=probabilities, k=1)[0]
            print(f" - Drew rarity: {chosen_rarity}")

            available_pokemon_for_rarity = self._get_pokemon_by_rarity(chosen_rarity)
            selected_pokemon = self._select_pokemon_instance(available_pokemon_for_rarity)

            if selected_pokemon:
                item = CollectionItem.objects.create(
                    owner=user_profile,
                    pokemon=selected_pokemon
                )
                awarded_items.append(item)
                print(f"   - Awarded: {selected_pokemon.name.capitalize()}")
            else:
                print(f"   - Warning: No Pokemon found for rarity '{chosen_rarity}'.")

        return awarded_items

PACK_STRATEGIES = {
    'default': StandardPackStrategy(),
    'standard': StandardPackStrategy(),
}

def get_pack_strategy(pack) -> PackOpeningStrategy:
    """Selects the appropriate strategy for the given pack."""
    strategy_key = getattr(pack, 'strategy_type', 'default').lower()
    return PACK_STRATEGIES.get(strategy_key, PACK_STRATEGIES['default'])
