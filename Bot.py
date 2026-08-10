import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from Replay_Parser import ReplayParser as RP
from Sheet import Sheet
from Transaction import Transactions

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MOD = int(os.getenv('MOD_ROLE_ID'))

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

def get_sheet_id(div_value):
    if div_value == "F":
        return os.getenv("FLOATZEL_ID")

    if div_value == "S":
        return os.getenv("SWAMPERT_ID")

    if div_value == "P":
        return os.getenv("PALAFIN_ID")

    raise ValueError("Invalid division selected.")

def get_coach_roster(team_rosters, coach_id):
    coach_key = str(coach_id).strip().lower()
    return team_rosters.get(coach_key, {})

def get_roster_points(coach_roster):
    total_points = 0

    for pokemon_data in coach_roster.values():
        total_points += pokemon_data["points"]

    return total_points

def get_rows_to_delete(coach_roster, pokemon_list):
    rows_to_delete = []

    for pokemon in pokemon_list:
        pokemon_name = pokemon.strip().lower()
        rows_to_delete.append(coach_roster[pokemon_name]["row"])

    rows_to_delete.sort(reverse=True)
    return rows_to_delete

def delete_roster_rows(sheet, sheet_id, rows_to_delete):
    for row_number in rows_to_delete:
        sheet.remove_pokemon_from_roster(sheet_id, row_number)

def append_pokemon_to_roster(sheet, sheet_id, coach_id, pokemon_list, pokedex):
    for pokemon in pokemon_list:
        pokemon_name = pokemon.strip().lower()
        pokemon_points = pokedex[pokemon_name]

        roster_row = [coach_id, pokemon, pokemon_points]

        sheet.append_current_roster(sheet_id, roster_row)

@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f'{bot.user} has connected to Discord!')

@bot.tree.command(name="replay", description="Gets the replay and displays KDA for each Pokemon.")
@app_commands.describe(url="Paste the Pokémon Showdown replay URL")
@app_commands.checks.has_role(MOD)
async def replay(interaction: discord.Interaction, url: str):
    await interaction.response.defer(ephemeral=True)  # Defer the response to give more time for processing
    try:
        results = RP(url)
        results = results.run()

        if results is None:
            raise ValueError("The replay could not be parsed.")
        
        await interaction.followup.send(f"{results}")

    except Exception as error:
        await interaction.followup.send(f"An error occurred while fetching the replay: {type(error).__name__}: {error}")

@bot.tree.command(name="upload", description="Uploads all the necessary data to the specified Google Sheet.")
@app_commands.describe(url="Paste the Pokémon Showdown replay URL", div="Select the division for the replay data", week="Type the week for the replay data(1, 2, 3, etc.)")
@app_commands.choices(div=[
    app_commands.Choice(name="Floatzel", value="F"),
    app_commands.Choice(name="Swampert", value="S"),
    app_commands.Choice(name="Palafin", value="P"),
])
@app_commands.checks.has_role(MOD)
async def upload(interaction: discord.Interaction, url: str, div: app_commands.Choice[str], week: int):
    await interaction.response.defer()
    try:
        parser = RP(url)
        message = parser.run()

        if parser.battle is None:
            raise ValueError("The replay could not be parsed.")

        sheet = Sheet()
        sheet_id = get_sheet_id(div.value)
        p1 = parser.battle.p1
        p2 = parser.battle.p2
        replay_data = [
            url, week, p1, p2, parser.battle.winner, parser.battle.differential
        ]

        pokemon_data = []
        teams = [
            (parser.battle.p1, parser.battle.p1_pokemon),
            (parser.battle.p2, parser.battle.p2_pokemon)
        ]
        for player_name, team in teams:
            for pokemon in team.values():
                row_data = [
                    url,
                    week,
                    player_name,
                    pokemon.name,
                    pokemon.active_kills,
                    pokemon.passive_kills,
                    pokemon.deaths
                ]
                pokemon_data.append(row_data)

        uploaded = sheet.append_replay_data(sheet_id, replay_data)
        if not uploaded:
            await interaction.followup.send("That replay has already been uploaded.")
        else:
            sheet.append_pokemon_data(sheet_id, pokemon_data)
            await interaction.followup.send(f"Data uploaded successfully for {p1} vs {p2}.")

    except Exception as error:
        await interaction.followup.send(f"An error occurred while fetching the replay. {type(error).__name__}: {error}")

@bot.tree.command(name="draft", description="Uploads the draft pick to the specified Google Sheet.")
@app_commands.describe(coach="Type the coach's name", pokemon="Type the Pokémon's name. MUST MATCH THE EXACT FORMAT IN THE TIERLIST(Landorus-Therian, Alolan Rattata, Mega Charizard X, Paldean Tauros Blaze, etc).", 
                       div="Select the division for the draft pick")
@app_commands.choices(div=[
    app_commands.Choice(name="Floatzel", value="F"),
    app_commands.Choice(name="Swampert", value="S"),
    app_commands.Choice(name="Palafin", value="P"),
])
@app_commands.checks.has_role(MOD)
async def draft(interaction: discord.Interaction, coach: str, pokemon: str, div: app_commands.Choice[str]):
    await interaction.response.defer()
    try:
        sheet = Sheet()
        sheet_id = get_sheet_id(div.value)

        coach_id = sheet.get_coach_id(sheet_id, coach)
        if coach_id is None:
            await interaction.followup.send(
                f"Coach `{coach}` could not be found."
            )
            return

        roster_size = sheet.get_roster_size(sheet_id, coach_id)

        if roster_size >= 12:
            await interaction.followup.send(
                f"`{coach}` already has 12 Pokémon on their roster."
            )
            return
        
        if sheet.pokemon_is_rostered(sheet_id, pokemon):
            await interaction.followup.send(
                f"`{pokemon}` has already been drafted."
            )
            return

        pokemon_points = sheet.get_pokemon_points(sheet_id, pokemon)
        if pokemon_points is None:
            await interaction.followup.send(
                f"`{pokemon}` could not be found in the Pokedex."
            )
            return

        current_points = sheet.get_roster_points(sheet_id, coach_id)
        new_total = current_points + pokemon_points

        if new_total > 110:
            remaining_points = 110 - current_points

            await interaction.followup.send(
                f"`{coach}` does not have enough points to draft "
                f"`{pokemon}`.\n"
                f"Pokémon cost: **{pokemon_points}**\n"
                f"Points remaining: **{remaining_points}**"
            )
            return

        roster_row = [
            coach_id,
            pokemon,
            pokemon_points
        ]
        
        sheet.append_current_roster(sheet_id, roster_row)

        remaining_points = 110 - new_total

        await interaction.followup.send(
            f"Draft pick uploaded successfully.\n"
            f"Coach: **{coach}**\n"
            f"Pokémon: **{pokemon}**\n"
            f"Cost: **{pokemon_points}**\n"
            f"Points remaining: **{remaining_points}**"
        )
        
    except Exception as error:
        print(f"Error occurred while uploading draft pick: {error}")
        await interaction.followup.send(f"An error occurred while uploading the draft pick: {type(error).__name__}: {error}")

@bot.tree.command(name="free_agency", description="Uploads the transaction to the specified Google Sheet.")
@app_commands.describe(week="Type the week for the transaction data(1, 2, 3, etc.)", 
                       coach="Type the name of the coach",
                       drop1="Type the name of the first Pokémon removed from the first coach's roster",
                       drop2="Type the name of the second Pokémon removed from the first coach's roster",
                       drop3="Type the name of the third Pokémon removed from the first coach's roster",
                       pickup1="Type the name of the first Pokémon added to the first coach's roster",
                       pickup2="Type the name of the second Pokémon added to the first coach's roster",
                       pickup3="Type the name of the third Pokémon added to the first coach's roster",
                       notes="Type any notes for the transaction",
                       div="Select the division for the transaction")
@app_commands.choices(div=[
    app_commands.Choice(name="Floatzel", value="F"),
    app_commands.Choice(name="Swampert", value="S"),
    app_commands.Choice(name="Palafin", value="P"),
])
@app_commands.checks.has_role(MOD)
async def free_agency(interaction: discord.Interaction, 
                      week: int, coach: str, div: app_commands.Choice[str],
                      drop1: str = None, drop2: str = None, drop3: str = None,
                      pickup1: str = None, pickup2: str = None, pickup3: str = None,
                      notes: str = None):
    await interaction.response.defer() 
    try:
        sheet = Sheet()
        sheet_id = get_sheet_id(div.value)
        coach_id = sheet.get_coach_id(sheet_id, coach)
        if coach_id is None:
            raise ValueError(f"Coach `{coach}` could not be found.")

        removed = [drop1, drop2, drop3]
        added = [pickup1, pickup2, pickup3]

        transaction = Transactions(
            week=week,
            coach_1_id=coach_id,
            removed = removed,
            added = added,
            notes=notes
        )

        transaction.validate()

        transaction_data = sheet.get_transaction_data(sheet_id)

        pokedex = transaction_data['pokedex']
        rostered_pokemon = transaction_data['rostered_pokemon']
        team_rosters = transaction_data['team_rosters']

        coach_roster = get_coach_roster(team_rosters, coach_id)

        for pokemon in transaction.removed:
            pokemon_lower = pokemon.strip().lower()
            if pokemon_lower not in pokedex:
                raise ValueError(f"`{pokemon}` could not be found in the Pokedex.")
            if pokemon_lower not in coach_roster:
                raise ValueError(f"`{pokemon}` is not on `{coach}`'s roster and cannot be removed.")
            

        for pokemon in transaction.added:
            pokemon_lower = pokemon.strip().lower()
            if pokemon_lower not in pokedex:
                raise ValueError(f"`{pokemon}` could not be found in the Pokedex.")

            if pokemon_lower in rostered_pokemon:
                raise ValueError(f"`{pokemon}` is already on a roster.")

        current_roster_size = len(coach_roster)

        new_roster_size = (current_roster_size - len(transaction.removed) + len(transaction.added))

        if new_roster_size > 12:
            raise ValueError(f"This transaction would give `{coach}` more than 12 Pokémon.")      
        elif new_roster_size < 0:
            raise ValueError(f"This transaction would give `{coach}` an invalid roster size.")

        current_points = get_roster_points(coach_roster)

        removed_points = 0
        for pokemon in transaction.removed:
            pokemon_name = pokemon.strip().lower()
            removed_points += coach_roster[pokemon_name]["points"]

        added_points = 0
        for pokemon in transaction.added:
            pokemon_name = pokemon.strip().lower()
            added_points += pokedex[pokemon_name]

        new_points = (current_points - removed_points + added_points)

        if new_points > 110:
            raise ValueError(f"This transaction would put `{coach}` at {new_points}/110 points.")

        rows_to_delete = get_rows_to_delete(coach_roster, transaction.removed)
        delete_roster_rows(sheet, sheet_id, rows_to_delete)

        append_pokemon_to_roster(sheet, sheet_id, coach_id, transaction.added, pokedex)

        transaction_id = sheet.get_next_transaction_id(sheet_id)

        transaction_row = [
            transaction_id,
            transaction.week,
            "Free Agent",
            transaction.coach_1_id,
            drop1,
            drop2,
            drop3,
            pickup1,
            pickup2,
            pickup3, 
            transaction.notes
        ]

        sheet.append_transaction(sheet_id, transaction_row)
        await interaction.followup.send("Transaction uploaded successfully.")

    except Exception as error:
        await interaction.followup.send(f"An error occurred while uploading the transaction: {type(error).__name__}: {error}")

@bot.tree.command(name="trade", description="Uploads a trade to the specified Google Sheet.")
@app_commands.describe(week="Type the week for the transaction data(1, 2, 3, etc.)", 
                       coach="Type the name of the coach",
                       coach2="Type the name of the second coach",
                       drop1="Type the name of the first Pokémon removed from the first coach's roster",
                       drop2="Type the name of the second Pokémon removed from the first coach's roster",
                       drop3="Type the name of the third Pokémon removed from the first coach's roster",
                       pickup1="Type the name of the first Pokémon added to the first coach's roster",
                       pickup2="Type the name of the second Pokémon added to the first coach's roster",
                       pickup3="Type the name of the third Pokémon added to the first coach's roster",
                       notes="Type any notes for the transaction",
                       div="Select the division for the transaction")
@app_commands.choices(div=[
    app_commands.Choice(name="Floatzel", value="F"),
    app_commands.Choice(name="Swampert", value="S"),
    app_commands.Choice(name="Palafin", value="P"),
])
@app_commands.checks.has_role(MOD)
async def trade(interaction: discord.Interaction, 
                      week: int, coach: str, coach2: str, div: app_commands.Choice[str],
                      drop1: str = None, drop2: str = None, drop3: str = None,
                      pickup1: str = None, pickup2: str = None, pickup3: str = None,
                      notes: str = None):
    await interaction.response.defer() 
    try:
        sheet = Sheet()
        sheet_id = get_sheet_id(div.value)

        coach_1_id = sheet.get_coach_id(sheet_id, coach)
        if coach_1_id is None:
            raise ValueError(
                f"Coach `{coach}` could not be found."
            )

        coach_2_id = sheet.get_coach_id(sheet_id, coach2)
        if coach_2_id is None:
            raise ValueError(
                f"Coach `{coach2}` could not be found."
            )

        removed = [drop1, drop2, drop3]
        added = [pickup1, pickup2, pickup3]

        transaction = Transactions(
            week=week,
            coach_1_id=coach_1_id,
            coach_2_id=coach_2_id,
            removed=removed,
            added=added,
            notes=notes
        )
        transaction.validate()

        transaction_data = sheet.get_transaction_data(sheet_id)
        pokedex = transaction_data["pokedex"]
        team_rosters = transaction_data["team_rosters"]

        coach_1_roster = get_coach_roster(team_rosters, coach_1_id)
        coach_2_roster = get_coach_roster(team_rosters, coach_2_id)

        # Coach 1 must own everything they are sending.
        for pokemon in transaction.removed:
            pokemon_name = pokemon.strip().lower()

            if pokemon_name not in pokedex:
                raise ValueError(
                    f"`{pokemon}` could not be found in the Pokedex."
                )

            if pokemon_name not in coach_1_roster:
                raise ValueError(
                    f"`{pokemon}` is not on `{coach}`'s roster."
                )

        # Coach 2 must own everything Coach 1 is receiving.
        for pokemon in transaction.added:
            pokemon_name = pokemon.strip().lower()

            if pokemon_name not in pokedex:
                raise ValueError(
                    f"`{pokemon}` could not be found in the Pokedex."
                )

            if pokemon_name not in coach_2_roster:
                raise ValueError(
                    f"`{pokemon}` is not on `{coach2}`'s roster."
                )

        coach_1_new_size = (len(coach_1_roster) - len(transaction.removed) + len(transaction.added))
        coach_2_new_size = (len(coach_2_roster) - len(transaction.added) + len(transaction.removed))

        if coach_1_new_size > 12:
            raise ValueError(
                f"This trade would give `{coach}` more than 12 Pokémon."
            )

        if coach_2_new_size > 12:
            raise ValueError(
                f"This trade would give `{coach2}` more than 12 Pokémon."
            )

        coach_1_current_points = get_roster_points(coach_1_roster)
        coach_2_current_points = get_roster_points(coach_2_roster)

        coach_1_removed_points = 0
        for pokemon in transaction.removed:
            pokemon_name = pokemon.strip().lower()
            coach_1_removed_points += (
                coach_1_roster[pokemon_name]["points"]
            )

        coach_1_added_points = 0
        for pokemon in transaction.added:
            pokemon_name = pokemon.strip().lower()
            coach_1_added_points += (
                coach_2_roster[pokemon_name]["points"]
            )

        coach_1_new_points = (coach_1_current_points - coach_1_removed_points + coach_1_added_points)
        coach_2_new_points = (coach_2_current_points - coach_1_added_points + coach_1_removed_points)

        if coach_1_new_points > 110:
            raise ValueError(
                f"This trade would put `{coach}` at "
                f"{coach_1_new_points}/110 points."
            )

        if coach_2_new_points > 110:
            raise ValueError(
                f"This trade would put `{coach2}` at "
                f"{coach_2_new_points}/110 points."
            )

        coach_1_rows = get_rows_to_delete(coach_1_roster, transaction.removed)
        coach_2_rows = get_rows_to_delete(coach_2_roster, transaction.added)

        rows_to_delete = coach_1_rows + coach_2_rows
        rows_to_delete.sort(reverse=True)
        delete_roster_rows(sheet, sheet_id, rows_to_delete)

        append_pokemon_to_roster(sheet, sheet_id, coach_1_id, transaction.added, pokedex)
        append_pokemon_to_roster(sheet, sheet_id, coach_2_id, transaction.removed, pokedex)

        transaction_id = sheet.get_next_transaction_id(sheet_id)

        coach_1_transaction_row = [
            transaction_id,
            transaction.week,
            "Trade",
            coach_1_id,
            drop1,
            drop2,
            drop3,
            pickup1,
            pickup2,
            pickup3,
            transaction.notes
        ]

        coach_2_transaction_row = [
            transaction_id,
            transaction.week,
            "Trade",
            coach_2_id,
            pickup1,
            pickup2,
            pickup3,
            drop1,
            drop2,
            drop3,
            transaction.notes
        ]

        sheet.append_transaction(sheet_id, coach_1_transaction_row)
        sheet.append_transaction(sheet_id, coach_2_transaction_row)

        await interaction.followup.send(
            f"Trade uploaded successfully.\n"
            f"**{coach}** receives: "
            f"{', '.join(transaction.added)}\n"
            f"**{coach2}** receives: "
            f"{', '.join(transaction.removed)}"
        )

    except Exception as error:
        await interaction.followup.send(f"An error occurred while uploading the trade: {type(error).__name__}: {error}")

@bot.tree.command(name="team_wipe", description="Deletes an entire team's current roster.")
@app_commands.describe(coach="Coach whose roster should be deleted", div="Select the division")
@app_commands.choices(div=[
    app_commands.Choice(name="Floatzel", value="F"),
    app_commands.Choice(name="Swampert", value="S"),
    app_commands.Choice(name="Palafin", value="P")
])
@app_commands.checks.has_role(MOD)
async def team_wipe(interaction: discord.Interaction, coach: str, div: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)
    try:
        sheet = Sheet()
        sheet_id = get_sheet_id(div.value)

        coach_id = sheet.get_coach_id(sheet_id, coach)
        if coach_id is None:
            raise ValueError(
                f"`{coach}` could not be found."
            )

        transaction_data = sheet.get_transaction_data(sheet_id)
        team_rosters = transaction_data["team_rosters"]

        coach_roster = get_coach_roster(team_rosters, coach_id)
        if len(coach_roster) == 0:
            raise ValueError(
                f"`{coach}` does not currently have any Pokemon."
            )

        rows_to_delete = []
        for pokemon_data in coach_roster.values():
            rows_to_delete.append(pokemon_data["row"])
        rows_to_delete.sort(reverse=True)
        delete_roster_rows(sheet, sheet_id, rows_to_delete)

        await interaction.followup.send(
            f"`{coach}`'s entire roster was deleted.\n"
            f"Removed {len(rows_to_delete)} Pokemon."
        )

    except Exception as error:
        await interaction.followup.send(f"An error occurred while wiping the team: {type(error).__name__}: {error}")

@bot.tree.command(name="forfeit", description="Record a forfeited match.")
@app_commands.describe(week="Week of the match", winner="Winning coach", loser="Losing coach", div="Division")
@app_commands.choices(div=[
    app_commands.Choice(name="Floatzel", value="F"),
    app_commands.Choice(name="Swampert", value="S"),
    app_commands.Choice(name="Palafin", value="P"),
])
@app_commands.checks.has_role(MOD)
async def forfeit(interaction: discord.Interaction, week: int, winner: str, loser: str, div: app_commands.Choice[str]):
    await interaction.response.defer()
    try:
        sheet = Sheet()
        sheet_id = get_sheet_id(div.value)

        winner_showdown = sheet.get_showdown_name(sheet_id, winner)
        loser_showdown = sheet.get_showdown_name(sheet_id, loser)

        if winner_showdown is None:
            raise ValueError(f"Coach `{winner}` could not be found.")

        if loser_showdown is None:
            raise ValueError(f"Coach `{loser}` could not be found.")

        replay_data = [
            "FORFEIT",
            week,
            winner_showdown,
            loser_showdown,
            winner_showdown,
            3
        ]

        sheet.append_replay_data(sheet_id, replay_data)

        await interaction.followup.send(
            f"Successfully recorded a forfeit.\n"
            f"**Winner:** {winner}\n"
            f"**Loser:** {loser}"
        )
    except Exception as error:
        await interaction.followup.send(f"An error occurred while recording the forfeit: {type(error).__name__}: {error}")

@bot.tree.command(name="double_forfeit" ,description="Record a double forfeit.")
@app_commands.describe(week="Week of the match", coach_1="First coach", coach_2="Second coach", div="Division")
@app_commands.choices(div=[
    app_commands.Choice(name="Floatzel", value="F"),
    app_commands.Choice(name="Swampert", value="S"),
    app_commands.Choice(name="Palafin", value="P"),
])
@app_commands.checks.has_role(MOD)
async def double_forfeit(interaction: discord.Interaction, week: int, coach_1: str, coach_2: str, div: app_commands.Choice[str]):
    await interaction.response.defer()
    try:
        sheet = Sheet()
        sheet_id = get_sheet_id(div.value)

        coach_1_showdown = sheet.get_showdown_name(sheet_id, coach_1)
        coach_2_showdown = sheet.get_showdown_name(sheet_id, coach_2)

        if coach_1_showdown is None:
            raise ValueError(f"Coach `{coach_1}` could not be found.")

        if coach_2_showdown is None:
            raise ValueError(f"Coach `{coach_2}` could not be found.")

        replay_data = [
            "DOUBLE FORFEIT",
            week,
            coach_1_showdown,
            coach_2_showdown,
            "",
            3
        ]

        sheet.append_replay_data(sheet_id, replay_data)

        await interaction.followup.send(
            f"Successfully recorded a double forfeit.\n"
            f"**{coach_1}** and **{coach_2}** both receive a loss and -3 differential."
        )

    except Exception as error:
        await interaction.followup.send(f"An error occurred while recording the double forfeit: {type(error).__name__}: {error}")

bot.run(TOKEN)