import requests

url = "https://replay.pokemonshowdown.com/gen9natdexdraft-2651120147"

log = requests.get(url + ".log").text

print(log)