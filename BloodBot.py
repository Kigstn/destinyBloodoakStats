#!/usr/bin/env python3
import sys

import discord
import message_handler

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from events.base_event              import BaseEvent
from events                         import *
import asyncio
import datetime
import random
import re

from discord.ext.commands import Bot

from threading import Thread
from threading import current_thread

from functions.database import insertIntoMessageDB
from static.config      import NOW_PLAYING, COMMAND_PREFIX, BOT_TOKEN

# Set to remember if the bot is already running, since on_ready may be called
# more than once on reconnects
this = sys.modules[__name__]
this.running = False

# Scheduler that will be used to manage events
sched = AsyncIOScheduler()


###############################################################################

def launch_event_loops(client):
    print("Loading events...", flush=True)
    n_ev = 0
    for ev in BaseEvent.__subclasses__():
        event = ev()
        sched.add_job(event.run, 'interval', (client,),
                        minutes=event.interval_minutes)
        n_ev += 1
    sched.start()
    print(f"{n_ev} events loaded", flush=True)
    print(f"Startup complete!", flush=True)


def main():
    """the main method"""
    # Initialize the client
    print("Starting up...")
    client = Bot('!')
    # Define event handlers for the client
    # on_ready may be called multiple times in the event of a reconnect,
    # hence the running fla
    @client.event
    async def on_ready():
        if this.running:
            return

        this.running = True

        # Set the playing status
        if NOW_PLAYING:
            print("Setting NP game", flush=True)
            await client.change_presence(
                activity=discord.Game(name=NOW_PLAYING))
        print("Logged in!", flush=True)

        
        t1 = Thread(target=launch_event_loops, args=(client,))
        t1.start()


    # The message handler for both new message and edits
    @client.event
    async def common_handle_message(message):
        text = message.content
        if 'äbidöpfel' in text:
            texts = [   '<:NeriaHeart:671389916277506063> <:NeriaHeart:671389916277506063> <:NeriaHeart:671389916277506063>', 
                        'knows what`s up', 'knows you can do the thing', 'has been voted plushie of the month', 'knows da wey',
                        'yes!', 'does`nt yeet teammtes of the map, be like Häbidöpfel', 'debuggin has proven effective 99.9% of the time',
                        'is cuteness incarnate']
            addition = random.choice(texts)
            await message.channel.send(f'Häbidöpfel {addition}')
        if text.startswith(COMMAND_PREFIX) and text != COMMAND_PREFIX:
            cmd_split = text[len(COMMAND_PREFIX):].split()
            try:
                await message_handler.handle_command(cmd_split[0].lower(), 
                                      cmd_split[1:], message, client)
            except:
                print("Error while handling message", flush=True)
                raise
        else:
            badwords = ['kanen', 'cyber', 'dicknugget', 'nigg', 'cmonbrug', ' bo ', 'bloodoak', 'ascend', 'cock', 'cunt']
            goodchannels = [670400011519000616, 670400027155365929, 670402166103474190, 670362162660900895, 672541982157045791]
            if not message.content.startswith('http') and len(message.clean_content) > 5 and not any([badword in message.clean_content.lower() for badword in badwords]) and message.channel.id in goodchannels:
                formattedtime = message.created_at.strftime('%Y-%m-%dT%H:%M')
                success = insertIntoMessageDB(message.clean_content,message.author.id,message.channel.id,message.id, formattedtime)

    tasks = []
    @client.event
    async def on_message(message):
        if message.author == client.user:
            return
        asyncio.ensure_future(common_handle_message(message))

    @client.event
    async def on_member_join(member):
        guestObj = discord.utils.get(member.guild.roles, name="Guest")
        await member.add_roles(guestObj)

    @client.event
    async def on_message_edit(before, after):
        await common_handle_message(after)

    @client.event
    async def on_voice_state_update(member, before, after):
        if before.channel is None:
            #print(f'{member.name} joined VC {after.channel.name}')
            await joined_channel(member, after.channel)
            return

        if after.channel is None:
            #print(f'{member.name} left VC {before.channel.name}')
            await left_channel(member, before.channel)
            return

        if before.channel != after.channel:
            #print(f'{member.name} changed VC from {before.channel.name} to {after.channel.name}')
            await joined_channel(member, after.channel)
            await left_channel(member, before.channel)
            return

    async def joined_channel(member, channel):
        nummatch = re.findall(r'\d\d', channel.name)
        if nummatch:
            number = int(nummatch[-1])
            nextnumber = number + 1
            if nextnumber == 8:
                #await member.send('What the fuck are you doing')
                return
            nextnumberstring = str(nextnumber).zfill(2)

            channelnamebase = channel.name.replace(nummatch[-1], '')

            if not discord.utils.get(member.guild.voice_channels, name=channelnamebase + nextnumberstring):
                await channel.clone(name=channelnamebase + nextnumberstring)
                newchannel = discord.utils.get(member.guild.voice_channels, name=channelnamebase + nextnumberstring)
                await newchannel.edit(position=channel.position + 1)
                if 'PVP' in channel.name:
                    await newchannel.edit(position=channel.position + 1, user_limit=6)
       
    
    async def left_channel(member, channel):
        defaultchannels = 2
        nummatch = re.findall(r'\d\d', channel.name)
        if nummatch:
            number = int(nummatch[-1])
            previousnumber = number - 1
            previousnumberstring = str(previousnumber).zfill(2)

            channelnamebase = channel.name.replace(nummatch[-1], '')
            
            achannel = channel
            while achannel is not None:
                number = number + 1
                achannel = discord.utils.get(member.guild.voice_channels, name=channelnamebase + str(number).zfill(2))
            number = number - 1

            for i in range(defaultchannels+1, number+1, 1):
                higher = discord.utils.get(member.guild.voice_channels, name=channelnamebase + str(i).zfill(2))
                below = discord.utils.get(member.guild.voice_channels, name=channelnamebase + str(i - 1).zfill(2))
                if higher and not higher.members:
                    if below and not below.members:
                        await higher.delete()
            
            for i in range(defaultchannels+1, number + 1, 1):
                higher = discord.utils.get(member.guild.voice_channels, name=channelnamebase + str(i).zfill(2))
                below = discord.utils.get(member.guild.voice_channels, name=channelnamebase + str(i - 1).zfill(2))
                if higher and not below:
                        await higher.edit(name=channelnamebase + str(i-1).zfill(2))

    # Finally, set the bot running
    client.run(BOT_TOKEN)

###############################################################################


if __name__ == "__main__":
    # p = Process(target=start_server)
    # p.start()
    # print('server started')

    main()

    #p.join()
