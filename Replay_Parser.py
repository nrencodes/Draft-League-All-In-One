import requests
from streamlit import status
from Battle import Battle
from Pokemon import Pokemon

class ReplayParser:
    def __init__(self, replay_url):
        self.replay_url = replay_url
        self.log = None
        self.battle = None
        self.status_inflictor_candidate = None

    def fetch_log(self):
        response = requests.get(self.replay_url + ".log")
        response.raise_for_status()  # Raise an error for bad responses
        self.log = response.text
        return self.log

    def resolve_pokemon_name(self, team, revealed_name):
        if revealed_name in team:
            return revealed_name

        matching_key = None

        for stored_name in team:
            # Only look at forms that Showdown hid during team preview.
            if not stored_name.endswith("-*"):
                continue

            base_name = stored_name[:-2]

            if (
                revealed_name == base_name
                or revealed_name.startswith(base_name + "-")
            ):
                matching_key = stored_name
                break

        if matching_key is None:
            return revealed_name

        pokemon = team.pop(matching_key)
        pokemon.name = revealed_name
        team[revealed_name] = pokemon   

        return revealed_name
    
    def parse_log(self):
        if self.log is None:
            return None

        players = {}
        
        for line in self.log.splitlines():
            if not line.strip():
                continue
            
            parts = line.split("|")[1:]
            if not parts:
                continue

            event = parts[0]
            if event == 'player':
                player_num = parts[1]
                player_name = parts[2]
                players[player_num] = player_name

                if "p1" in players and "p2" in players and self.battle is None:
                    self.battle = Battle(self.replay_url, players["p1"], players["p2"])
                
            elif event == 'poke' and self.battle is not None:
                side = parts[1]
                pokemon_name = parts[2].split(",")[0]  # Get the Pokemon name before any comma
  
                owner = self.battle.p1 if side == "p1" else self.battle.p2
                pokemon = Pokemon(pokemon_name, owner)

                if side == "p1":
                    self.battle.p1_pokemon[pokemon_name] = pokemon
                elif side == "p2":
                    self.battle.p2_pokemon[pokemon_name] = pokemon

            elif event == "turn" and self.battle is not None:
                self.battle.turns += 1
            
            elif event in {"switch", "drag"} and self.battle is not None:
                side, nickname = parts[1].split(": ", 1)
                pokemon = parts[2].split(",")[0]

                if side.startswith("p1"):
                    team = self.battle.p1_pokemon
                else:
                    team = self.battle.p2_pokemon

                pokemon_name = self.resolve_pokemon_name(
                    team,
                    pokemon
                )

                self.battle.nickname_map[nickname] = pokemon_name
                
                if side == "p1a":
                    self.battle.p1a = pokemon_name
                elif side == "p1b":
                    self.battle.p1b = pokemon_name
                elif side == "p2a":
                    self.battle.p2a = pokemon_name
                elif side == "p2b":
                    self.battle.p2b = pokemon
                self.status_inflictor_candidate = None

            elif event == "replace" and self.battle is not None:
                side, nickname = parts[1].split(": ", 1)
                revealed_name = parts[2].split(",")[0]

                if side.startswith("p1"):
                    team = self.battle.p1_pokemon
                else:
                    team = self.battle.p2_pokemon

                pokemon_name = self.resolve_pokemon_name(
                    team,
                    revealed_name
                )

                self.battle.nickname_map[nickname] = pokemon_name

                if side == "p1a":
                    self.battle.p1a = pokemon_name
                elif side == "p1b":
                    self.battle.p1b = pokemon_name
                elif side == "p2a":
                    self.battle.p2a = pokemon_name
                elif side == "p2b":
                    self.battle.p2b = pokemon_name
            
            elif event == "detailschange" and self.battle is not None:
                side, nickname = parts[1].split(": ", 1)
                new_name = parts[2].split(",")[0] 
                is_silent = "[silent]" in parts
                if is_silent:
                    continue

                old_name = self.battle.nickname_map.get(nickname)
                if old_name is None:
                    continue

                if side.startswith("p1"):
                    pokemon = self.battle.p1_pokemon.pop(old_name, None)
                    if pokemon is not None:
                        pokemon.name = new_name
                        self.battle.p1_pokemon[new_name] = pokemon
                else:
                    pokemon = self.battle.p2_pokemon.pop(old_name, None)
                    if pokemon is not None:
                        pokemon.name = new_name
                        self.battle.p2_pokemon[new_name] = pokemon
                self.battle.nickname_map[nickname] = new_name

                if side == "p1a":
                    self.battle.p1a = new_name
                elif side == "p1b":
                    self.battle.p1b = new_name
                elif side == "p2a":
                    self.battle.p2a = new_name
                elif side == "p2b":
                    self.battle.p2b = new_name

            elif event == '-damage' and self.battle is not None:
                side, nickname = parts[1].split(": ", 1)
                damaged_name = self.battle.nickname_map[nickname]
                
                hp = parts[2]
                if hp.endswith("fnt") or hp.startswith("0"):
                    victim_side = side[:2]  # p1 or p2
                    victim = (
                        self.battle.p1_pokemon.get(damaged_name)
                        or self.battle.p2_pokemon.get(damaged_name)
                    )
                    if victim:
                        victim.deaths += 1
                        victim.is_dead = True

                    killer_name = None
                    damage_source = None

                    # Look through the extra information for a damage source.
                    for part in parts[3:]:
                        if part.startswith("[from]"):
                            damage_source = part.replace("[from] ", "")
                            break            

                    if damage_source is not None:
                        if damage_source in {"Stealth Rock", "Spikes", "Toxic Spikes"}:
                            killer_name = self.battle.hazards_set[victim_side][damage_source]

                        elif damage_source in {"psn", "tox", "brn"}:
                            killer_name = victim.status_inflictor

                        elif damage_source == "Sandstorm":
                            killer_name = self.battle.weather_inflictor
                        
                        # TODO: Implement other infliction sources like Leech Seed, Curse
                        # TODO: Implement self damage sources 
                        # Recoil and Life Orb already accounted for
                        # Explosion and Self-Destruct account for
                        # Still need rocky helmet, and abilities (iron barbs, rough skin, aftermath)
                        # confusion as well
                        # TODO: Implement items that are tricked onto victim pokemon like sticky barb

                        if killer_name is not None and killer_name != victim.name:
                            killer = (
                                self.battle.p1_pokemon.get(killer_name)
                                or self.battle.p2_pokemon.get(killer_name)
                            )

                            if killer is not None:
                                killer.passive_kills += 1

                    else: 
                        if victim_side == "p1":
                            killer_name = self.battle.p2a
                            killer = self.battle.p2_pokemon.get(killer_name)
                        else:
                            killer_name = self.battle.p1a
                            killer = self.battle.p1_pokemon.get(killer_name)

                        if killer is not None:
                            killer.active_kills += 1

            elif event == "faint" and self.battle is not None:
                side, nickname = parts[1].split(": ", 1)
                pokemon_name = self.battle.nickname_map[nickname]

                pokemon = (
                    self.battle.p1_pokemon.get(pokemon_name)
                    or self.battle.p2_pokemon.get(pokemon_name)
                )

                if pokemon is not None and not pokemon.is_dead:
                    pokemon.deaths += 1
                    pokemon.is_dead = True

            elif event == "-sidestart":
                # |-sidestart|p2: Malski|move: Stealth Rock
                player = parts[1].split(":")[0]
                hazard = parts[2].replace("move: ", "")
                inflictor = self.battle.p1a if player == "p2" else self.battle.p2a
                self.battle.add_hazard(player, hazard, inflictor)
            
            elif event == "-weather" and self.battle is not None:
                weather = parts[1]

                # Weather ended
                if weather == "none":
                    self.battle.clear_weather()

                # Weather upkeep
                elif len(parts) > 2 and "[upkeep]" in parts[2]:
                    continue

                # Weather from an ability
                elif len(parts) > 3 and "[of]" in parts[3]:
                    _, nickname = parts[3].replace("[of] ", "").split(": ", 1)
                    setter = self.battle.nickname_map[nickname]
                    self.battle.set_weather(weather, setter)

            elif event == 'move' and self.battle is not None:
                _, nickname = parts[1].split(": ", 1)
                move = parts[2]

                move_user = self.battle.nickname_map[nickname]
                self.status_inflictor_candidate = move_user

                if move in self.battle.weather_moves:
                    setter = self.battle.nickname_map[nickname]
                    self.battle.set_weather(move, setter)

            elif event == '-status' and self.battle is not None:
                side, nickname = parts[1].split(": ", 1)
                victim_side = side[:2]  # p1 or p2
                pokemon_name = self.battle.nickname_map[nickname]
                victim = (
                    self.battle.p1_pokemon.get(pokemon_name)
                    or self.battle.p2_pokemon.get(pokemon_name)
                )

                victim.status = parts[2]
                from_part = None
                of_part = None

                for part in parts[3:]:
                    if part.startswith("[from]"):
                        from_part = part
                    elif part.startswith("[of]"):
                        of_part = part

                if of_part is not None:
                    source = of_part.replace("[of] ", "")
                    _, inflictor_nickname = source.split(": ", 1)

                    victim.status_inflictor = self.battle.nickname_map[inflictor_nickname]
                
                elif from_part is not None and "item: " in from_part:
                    victim.status_inflictor = pokemon_name
                
                elif self.status_inflictor_candidate is not None:
                    victim.status_inflictor = self.status_inflictor_candidate

                elif victim.status in {"psn", "tox"} and self.battle.hazards_set[victim_side]["Toxic Spikes"]:
                    victim.status_inflictor = self.battle.hazards_set[victim_side]["Toxic Spikes"]

                self.status_inflictor_candidate = None
                                   
            elif event == 'win' and self.battle is not None:
                self.battle.winner = parts[1]
                self.battle.loser = self.battle.p2 if self.battle.winner == self.battle.p1 else self.battle.p1

            # TODO: Implement -start and -end for afflictions
            # TODO: Implement -curestatus event to handle status curing and update the status_inflictor accordingly.
            # TODO: Implement hazard removal events to clear hazards and update the inflictor accordingly.
            # TODO: Implement delayed attacking moves like Future Sight and Doom Desire

    def results(self):
        if self.battle is None:
            return None

        message = ""

        winner = self.battle.winner

        if self.battle.p1 == winner:
            winner_team = self.battle.p1_pokemon.values()
        else:
            winner_team = self.battle.p2_pokemon.values()

        remaining = 0
        for pokemon in winner_team:
            if pokemon.deaths == 0:
                remaining += 1

        self.battle.differential = remaining
        message += f"**Result:** ||{winner} won {remaining}-0||\n\n"

        message += f"**{self.battle.p1}:**||\n"

        for pokemon in self.battle.p1_pokemon.values():
            message += (
                f"{pokemon.name} has "
                f"{pokemon.active_kills} direct kills, "
                f"{pokemon.passive_kills} passive kills, "
                f"and {pokemon.deaths} deaths.\n"
            )

        message += "||\n"

        message += f"**{self.battle.p2}:**||\n"

        for pokemon in self.battle.p2_pokemon.values():
            message += (
                f"{pokemon.name} has "
                f"{pokemon.active_kills} direct kills, "
                f"{pokemon.passive_kills} passive kills, "
                f"and {pokemon.deaths} deaths.\n"
            )

        message += "||\n"
        message += f"**URL:** {self.replay_url}\n"

        return message
    
    def run(self):
        self.fetch_log()
        self.parse_log()
        return self.results()

if __name__ == "__main__":
    parser = ReplayParser(
        "https://replay.pokemonshowdown.com/gen9natdexdraft-2645361325"
    )

    results = parser.run()

    from pprint import pprint
    pprint(results)