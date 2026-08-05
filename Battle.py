class Battle:
    def __init__(self, replay_url: str, p1: str, p2: str):
        self.replay_url = replay_url
        self.p1 = p1
        self.p1_pokemon = {}

        self.p2 = p2
        self.p2_pokemon = {}

        self.nickname_map = {}
        self.hazards_set = {
            "p1": {
                "Stealth Rock": "",
                "Spikes": "",
                "Toxic Spikes": "",
            },
            "p2": {
                "Stealth Rock": "",
                "Spikes": "",
                "Toxic Spikes": "",
            },
        }

        self.weather_moves = ["Chilly Reception", "Rain Dance", "Sunny Day", "Sandstorm"]
        self.weather = ""
        self.weather_inflictor = ""

        self.winner = ""
        self.loser = ""
        self.differential = 0
        
        # Player 1 active Pokemon
        self.p1a = None
        self.p1b = None

        # Player 2 active Pokemon
        self.p2a = None
        self.p2b = None

        self.turns = 0
    
    def add_hazard(self, player: str, hazard: str, inflictor: str):
        if player in self.hazards_set and hazard in self.hazards_set[player]:
            self.hazards_set[player][hazard] = inflictor

    def end_hazard(self, player: str, hazard: str):
        if player in self.hazards_set and hazard in self.hazards_set[player]:
            self.hazards_set[player][hazard] = ""

    def set_weather(self, weather: str, inflictor: str):
        self.weather = weather
        self.weather_inflictor = inflictor

    def clear_weather(self):
        self.weather = ""
        self.weather_inflictor = ""
