from collections import defaultdict

class Pokemon:
    def __init__(self, name: str, owner: str):
        self.name = name
        self.owner = owner
        self.is_dead = False
        
        self.active_kills = 0
        self.passive_kills = 0
        self.deaths = 0

        self.status = None
        self.status_inflictor = None

        self.afflictions = defaultdict(lambda: None)