import gspread
from google.oauth2.service_account import Credentials


class Sheet:
    def __init__(self):
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file("creds.json", scopes=scopes)
        self.client = gspread.authorize(creds)

    def append_replay_data(self, sheet_id, row_data):
        spreadsheet = self.client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("Replays")
        replay_url = row_data[0]
        existing_urls = sheet.col_values(1)

        if replay_url.startswith("FORFEIT") or replay_url.startswith("DOUBLE FORFEIT"):
            pass
        else:
            for existing_url in existing_urls:
                if existing_url.strip() == replay_url.strip():
                    return False

        sheet.append_row(
        row_data,
        value_input_option="USER_ENTERED",
        table_range="A:F"
        )
        
        return True
        
    def append_pokemon_data(self, sheet_id, row_data):
        spreadsheet = self.client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("Pokemon Stats")
        sheet.append_rows(row_data)

    def append_current_roster(self, sheet_id, row_data):
        spreadsheet = self.client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("Current Roster")
        sheet.append_row(row_data)

    def pokemon_is_rostered(self, sheet_id, pokemon_name):
        spreadsheet = self.client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("Current Roster")
        rostered_pokemon = sheet.col_values(2)

        for rostered in rostered_pokemon[1:]:
            if rostered.strip().lower() == pokemon_name.strip().lower():
                return True
        return False

    def get_pokemon_points(self, sheet_id, pokemon_name):
        spreadsheet = self.client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("Pokedex")

        names = sheet.col_values(9)
        points = sheet.col_values(6)

        for name, point_value in zip(names[1:], points[1:]):
            if name.strip().lower() == pokemon_name.strip().lower():
                return int(point_value)

        return None

    def get_roster_points(self, sheet_id, coach_id):
        spreadsheet = self.client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("Current Roster")

        coach_ids = sheet.col_values(1)
        points = sheet.col_values(3)

        total = 0

        for i in range(1, len(coach_ids)):
            if coach_ids[i].strip().lower() == coach_id.strip().lower():
                total += int(points[i])

        return total

    def get_coach_id(self, sheet_id, coach_name):
        spreadsheet = self.client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("Coach Info")

        coach_names = sheet.col_values(3) 
        coach_ids = sheet.col_values(1) 
        
        for i in range(1, len(coach_names)):
            if coach_names[i].strip().lower() == coach_name.strip().lower():
                return coach_ids[i]

        return None

    def get_roster_size(self, sheet_id, coach_id):
        spreadsheet = self.client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("Current Roster")

        coach_ids = sheet.col_values(1)
        roster_size = 0

        for existing_coach_id in coach_ids[1:]:
            if existing_coach_id.strip().lower() == coach_id.strip().lower():
                roster_size += 1

        return roster_size

    def coach_owns_pokemon(self, sheet_id, coach_id, pokemon_name):
        spreadsheet = self.client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("Current Roster")

        coach_ids = sheet.col_values(1)
        pokemon_names = sheet.col_values(2)

        coach_id = str(coach_id).strip().lower()
        pokemon_name = pokemon_name.strip().lower()

        for i in range(1, len(coach_ids)):
            if (coach_ids[i].strip().lower() == coach_id and
                    pokemon_names[i].strip().lower() == pokemon_name):
                return True

        return False

    def remove_pokemon_from_roster(self, sheet_id, row):
        spreadsheet = self.client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("Current Roster")
        sheet.delete_rows(row)

    def append_transaction(self, sheet_id, row_data):
        spreadsheet = self.client.open_by_key(sheet_id) 
        sheet = spreadsheet.worksheet("Transactions")
        sheet.append_row(row_data)


    def get_next_transaction_id(self, sheet_id):
        spreadsheet = self.client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("Transactions")
        transaction_ids = sheet.col_values(1)[1:]

        if len(transaction_ids) == 0:
            return 1

        last_transaction_id = int(transaction_ids[-1])
        return last_transaction_id + 1

    def pokemon_exists(self, sheet_id, pokemon):
        worksheet = self.client.open_by_key(sheet_id).worksheet("Pokedex")

        values = worksheet.col_values(9)

        for value in values[1:]:
            if value.strip().lower() == pokemon.strip().lower():
                return True
            
        return False

    def get_transaction_data(self, sheet_id):
        spreadsheet = self.client.open_by_key(sheet_id)
        pokedex_sheet = spreadsheet.worksheet("Pokedex")
        roster_sheet = spreadsheet.worksheet("Current Roster")

        pokedex_data = pokedex_sheet.get("F3:I")
        roster_data = roster_sheet.get("A2:C")

        pokedex = {}
        for row in pokedex_data:
            if len(row) < 4:
                continue
            pokemon_name = row[3].strip().lower()
            point_value = row[0].strip()
            if pokemon_name == "":
                continue
            if point_value == "" or point_value == "Banned":
                continue
            pokedex[pokemon_name] = int(point_value)

        rostered_pokemon = set()
        team_rosters = {}

        for row_number, row in enumerate(roster_data, start=2):
            if len(row) < 3:
                continue

            coach_id = row[0].strip().lower()
            pokemon_name = row[1].strip().lower()
            pokemon_points = row[2].strip()
            if coach_id == "":
                continue
            if pokemon_name == "":
                continue
            if pokemon_points == "" or pokemon_points == "Banned":
                continue

            rostered_pokemon.add(pokemon_name)
            if coach_id not in team_rosters:
                team_rosters[coach_id] = {}

            team_rosters[coach_id][pokemon_name] = {
                "points": int(pokemon_points),
                "row": row_number
            }

        return {
            "pokedex": pokedex,
            "rostered_pokemon": rostered_pokemon,
            "team_rosters": team_rosters
        }

    def get_showdown_name(self, sheet_id, coach_name):
        spreadsheet = self.client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("Coach Info")

        coach_names = sheet.col_values(8)[1:] 
        showdown_names = sheet.col_values(6)[1:]  

        coach_name = coach_name.strip().lower()

        for i in range(len(coach_names)):
            if coach_names[i].strip().lower() == coach_name:
                return showdown_names[i]

        return None