# google on how to get these
# probably should put them in an .env file, up to you
DISCORD_TOKEN=''
DISCORD_GUILD=''


# path to the database storing all crafting info
DB_PATH = ''
# refresh rate for checking on items
DB_REFRESH_RATE = 30 #in seconds
# list of channels for the bot to look in
DISCORD_CHANNELS = {}
# discord roles ID
DISCORD_ROLES = {
    'ALC': [],
    'ARM': [],
    'JWL': [],
    'CKG': [],
    'LTW': [],
    'NEC': [],
    'RUN': [],
    'STO': [],
    'WPN': [],
    'WOO': [],
    'BKS': []
}
# abbrv. to full name
CRAFTING_DISC_CONVERSION = {
    'ALC': 'Alchemy',
    'ARM': 'Armorsmithing',
    'JWL': 'Jewelcrafting',
    'CKG': 'Cooking',
    'LTW': 'Leatherworking',
    'NEC': 'Necromancy',
    'RUN': 'Runemaking',
    'STO': 'Stonemasonry',
    'WPN': 'Weaponsmithing',
    'WOO': 'Woodworking',
    'BKS': 'Blacksmithing'
}
# rarity conversion
RARITY_CONVERSION = {
    'C' : 'Common',
    'U' : 'Uncommon',
    'R' : 'Rare',
    'E' : 'Epic',
    'L' : 'Legendary'
}
# keep in order of claimed, completed
MSG_REACTS = ['👀', '✅']