# bot.py
# Craftquests discord bot made by Bearsy for Lion Forge Guild.
# License: MIT. Good luck, have fun.

import os
import sqlite3
import json

# probably need to install these!
import pandas
import requests
import discord
from dotenv import load_dotenv
from discord.ext import tasks, commands

# import settings
import settings

# connect to database
conn = sqlite3.connect(settings.DB_PATH)

def sql_update(item_id, status, crafter, con=conn):
    """
        Update sqlite3 databse. Modify this function if you have a different
        database setup.

        Parameters are self-explanatory.

        Returns None.
    """

    cursor = con.cursor()

    cursor.execute("""
        UPDATE craftquests_craftingrequest
            SET status = ?,
                crafter = ?
            WHERE id = ?;
     """, (status, crafter, item_id))

    con.commit()

    print(f'Database updated: status {status}, crafter {crafter}, item_id {item_id}')

def __parse_sql(sql_rows):
    """
        Parse sqlite3 databse output. Modify this function if you have a different
        database setup. Helper function for sql_get().

        Parameters:
            sql_rows (str): output from SQL SELECT query.
        
        Returns:
            dict
    """

    column_names = ['id', 'requester', 'item_name', 'custom_name',
                    'quantity', 'crafting_discipline', 'special_instruction', 
                    'status', 'rarity', 'resource_provided', 'pub-date', 'crafter', 'stats']

    request_dict = {str(row[0]): {column_names[i]: row[i] for i,_ in enumerate(column_names)} for row in sql_rows}

    return request_dict

def sql_get(con=conn):
    """
        Request sqlite3 database information. Modify this function if you have a different
        database setup.
    
        Parameters:
            con (sqlite3 connection, optional)

        Returns:
            dict
    """
    cursor = con.cursor()

    # get active items
    cursor.execute("SELECT * FROM craftquests_craftingrequest WHERE status = ?", ("1"))
    rows = cursor.fetchall()
    active_req = __parse_sql(rows)

    # get compeled items
    cursor.execute("SELECT * FROM craftquests_craftingrequest WHERE status = ?", ("0"))
    rows = cursor.fetchall()
    completed_req = __parse_sql(rows)    
    
    # sort active items into claimed and unclaimed
    claimed_req = {}
    unclaimed_req = {}

    for name, val in active_req.items():
        # get crafter name        
        crafter = val['crafter']
        # if no crafter, unclaimed
        if (crafter is None or crafter == ""):
            unclaimed_req[name] = val
        # otherwise, claimed
        elif (type(crafter) == str and len(crafter) > 0):
            claimed_req[name] = val
        else:
            raise ValueError
    
    # output dict
    output = {'completed_req': completed_req,
              'claimed_req': claimed_req,
              'unclaimed_req': unclaimed_req}

    return output

# messaged_requests.csv store all messages that have been processed
messaged_requests = pandas.read_csv('messaged_requests.csv', 
    delimiter=',', header=None, names=['item_id', 'message_id'])
messaged_requests_message = list(map(int, messaged_requests['message_id']))
messaged_requests_item    = list(map(str, messaged_requests['item_id']))

# get discord token and guild
load_dotenv()
TOKEN = settings.DISCORD_TOKEN
GUILD = settings.DISCORD_GUILD

# load discord token
client = discord.Client()
# start requests session
s = requests.Session()

# begin discord.py async events
@client.event
async def on_ready():
    """
        Alert when connected.

        Parameters None.
        Returns None.
    """
    # connect to guild(s)
    guild = discord.utils.get(client.guilds, name=GUILD)

    print(
        f'{client.user} is connected to the following guild:\n'
        f'{guild.name}(id: {guild.id})'
    )

    # change status to online
    await client.change_presence(activity=discord.Game('online'))

# print(sql_get())

# update crafting database every <> seconds
@tasks.loop(seconds=settings.DB_REFRESH_RATE)
async def post_new_item():
    """
        Check and post new items ever <> seconds.

        Parameters none. 
        Returns None.
    """
    # get data
    x = sql_get()
    print(f'Fetched data from {settings.DB_PATH}')
    # sort output dict into unclaimed/claimed/completed
    unclaimed_req = x['unclaimed_req']
    claimed_req = x['claimed_req']
    completed_req = x['completed_req']

    # get all unclaimed and unlisted items
    for item_id in unclaimed_req:
        if item_id not in messaged_requests_item:
            # select item
            item = unclaimed_req[item_id]
            # list of roles to ping
            ping_list = [f'<@&{role_id}>' for role_id in settings.DISCORD_ROLES[item['crafting_discipline']]]
            # discord message to send out
            craftquest_message=(
                f"\n{settings.CRAFTING_DISC_CONVERSION[item['crafting_discipline']]} Request (#{item['id']})\n\n"+
                f"Requester: {item['requester']}\n" +
                f"Item: {settings.RARITY_CONVERSION[item['rarity']]}, {item['item_name']}\n" +
                f"Quantity: {item['quantity']}\n"
                f"Materials provided? {bool(item['resource_provided'])}\n" +
                f"Custom name: {item['custom_name']}\n" +
                f"Stats: {item['stats']}\n" +
                f"Special instruction: {item['special_instruction']}\n" + 
                f"Pings: {','.join(ping_list)}"            
            )
            # for each channel we monitor, send the message out
            for channel_id in settings.DISCORD_CHANNELS:
                # get channel
                channel = await client.fetch_channel(channel_id)
                # send message
                msg = await channel.send(craftquest_message)
                # add reactions
                [await msg.add_reaction(react) for react in settings.MSG_REACTS]

                # update the list of discord listed items
                messaged_requests_message.append(msg.id)
                messaged_requests_item.append(item_id)
            f = open('messaged_requests.csv', 'a+')
            f.write(f'{item_id},{msg.id}\n')
            f.close()

            print(f'Posted Discord Message\n{craftquest_message}\n')

# activate the new item posting
post_new_item.start()

# events when reactions are added or removed
@client.event
async def on_raw_reaction_add(payload):
    """
        Handle new reactions. See discord.py API for the payload parameter.
    """
    # get all the necessary info from payload
    guild = await client.fetch_guild(payload.guild_id)
    channel = await client.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    channel = await client.fetch_channel(payload.channel_id)
    user = await guild.fetch_member(payload.user_id)
    reaction = payload.emoji

    # ignore if the reaction is added by the bot
    if user == client.user:
        return

    # we only want messages sent by the bot
    if message.id not in messaged_requests_message:
        return

    # get the necessary username
    username = user.nick
    if user.nick is None:
        username = user.name

    # get item id
    item_idx = messaged_requests_message.index(message.id)
    item_id  = messaged_requests_item[item_idx]

    # get the most updated crafter/item status
    x = sql_get()
    unclaimed_req = x['unclaimed_req']
    claimed_req = x['claimed_req']
    completed_req = x['completed_req']
    simple_req = {}

    for req in [unclaimed_req, claimed_req, completed_req]:
        for tmp_item_id, item in req.items():
            simple_req[tmp_item_id] = [item['crafter'], item['status']]

    # get the current crafter/status of the item
    current_crafter = simple_req[item_id][0]
    current_status  = simple_req[item_id][1]

    # check if valid reaction
    if reaction.name not in settings.MSG_REACTS:
        await message.remove_reaction(reaction, user)
    
    # if it is valid, but already claimed, be anger
    elif (type(current_crafter) == str and len(current_crafter) > 0 and
            current_crafter != username):
        msg = await channel.send(f'<@{user.id}>: Request #{item_id} is already claimed by {current_crafter}.')
        await message.remove_reaction(reaction, user)
    
    # otherwise, valid reaction
    else:
        # claimed interaction    
        if reaction.name == settings.MSG_REACTS[0]:        
            sql_update(item_id, 1, username)
            
        # completed
        elif reaction.name in [settings.MSG_REACTS[1]]:
            # if currently no crafter, but a check mark is clicked, remove it and tell user to claim it first
            if current_crafter is None:
                msg = await channel.send(f'<@{user.id}>: Please claim the request first using {settings.MSG_REACTS[0]}.')
                await message.remove_reaction(reaction, user)
            # if current status is completed, can't check mark anymore
            elif current_status == 0:
                await message.remove_reaction(reaction, user)
            # otherwise, actually let the user mark it as complete
            else:
                sql_update(item_id, 0, username)

@client.event
async def on_raw_reaction_remove(payload):
    """
        Handle events when reaction is removed. See discord.py API for payload param.
    """

    # get important info from payload
    message = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
    reaction = payload.emoji
    guild = await client.fetch_guild(payload.guild_id)
    channel = await client.fetch_channel(payload.channel_id)
    user = await guild.fetch_member(payload.user_id)

    # get the right username
    username = user.nick
    if type(user.nick) == None:
        username = user.nick

    # we only want messages sent by the bot
    if message.id not in messaged_requests_message:
        return

    # get item id
    item_idx = messaged_requests_message.index(message.id)
    item_id  = messaged_requests_item[item_idx]

    # get the most updated crafter/item status
    x = sql_get()
    unclaimed_req = x['unclaimed_req']
    claimed_req = x['claimed_req']
    completed_req = x['completed_req']
    simple_req = {}

    for req in [unclaimed_req, claimed_req, completed_req]:
        for tmp_item_id, item in req.items():
            simple_req[tmp_item_id] = [item['crafter'], item['status']]

    current_crafter = simple_req[item_id][0]
    current_status  = simple_req[item_id][1]

    # only let current crafter remove reaction
    if (username != current_crafter):
        return
    
    # claimed interaction    
    if reaction.name == settings.MSG_REACTS[0]:
        # if removing claimed interaction, remove the check mark reaction too, if exists
        await message.remove_reaction(settings.MSG_REACTS[1], user)
        sql_update(item_id, 1, None)

    # completed/canceled
    elif reaction.name in [settings.MSG_REACTS[1]]:
        sql_update(item_id, 1, current_crafter)

# test function (ignore)
# @client.event
# async def on_message(message):
#     if message.author == client.user:
#         return
    
#     if message.content.startswith('$hello'):
#         msg = await message.channel.send('Hello!')
#         for react in settings.MSG_REACTS:        
#             await msg.add_reaction(react)   

#         print(msg.id)

# run the bot
client.run(TOKEN)
