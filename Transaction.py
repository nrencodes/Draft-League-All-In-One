class Transactions:
    MAX_CHANGES = 4

    def __init__(self, week, coach_1_id, removed=None, added=None, 
                 coach_2_id=None, notes=None):
        self.week = week
        self.notes = notes
        self.coach_1_id = coach_1_id
        self.coach_2_id = coach_2_id

        self.removed = []
        self.added = []

        if removed is not None:
            for pokemon in removed:
                self.add_pokemon_if_present(self.removed, pokemon)

        if added is not None:
            for pokemon in added:
                self.add_pokemon_if_present(self.added, pokemon)

    def add_pokemon_if_present(self, pokemon_list, pokemon):
        if pokemon is not None:
            pokemon = pokemon.strip()
            if pokemon != "":
                pokemon_list.append(pokemon.lower())

    def is_trade(self):
        return self.coach_2_id is not None
    
    def validate(self):
        self.validate_required_data()
        self.validate_duplicates()
        if self.is_trade():
            self.validate_trade()

    def validate_required_data(self):
        if self.week is None:
            raise ValueError("Week is required.")

        if self.week < 0:
            raise ValueError("Week cannot be negative.")
        
        if self.coach_1_id is None:
            raise ValueError("The first coach is required.")

        if len(self.removed) == 0 and len(self.added) == 0:
            raise ValueError(
                "The transaction must remove or add at least one Pokémon."
            )

    def validate_duplicates(self):
        if len(self.removed) != len(set(self.removed)):
            raise ValueError(
                "The same Pokémon cannot be removed more than once."
            )

        if len(self.added) != len(set(self.added)):
            raise ValueError(
                "The same Pokémon cannot be added more than once."
            )

        for pokemon in self.removed:
            if pokemon in self.added:
                raise ValueError(
                    f"`{pokemon}` cannot be both removed and added "
                    f"in the same transaction."
                )

    def validate_trade(self):
        if self.coach_2_id is None:
            raise ValueError(
                "The second coach is required for a trade."
            )

        if self.coach_1_id == self.coach_2_id:
            raise ValueError(
                "A coach cannot trade with themselves."
            )

        if len(self.removed) == 0:
            raise ValueError(
                "The first coach must send at least one Pokémon."
            )

        if len(self.added) == 0:
            raise ValueError(
                "The first coach must receive at least one Pokémon."
            )
