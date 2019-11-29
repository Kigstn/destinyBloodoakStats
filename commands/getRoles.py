from commands.base_command  import BaseCommand

from functions              import getUserIDbySnowflakeAndClanLookup, getFullMemberMap
from functions              import getPlayerRoles, assignRolesToUser,removeRolesFromUser, getUserMap
from dict                   import requirementHashes, clanids

import discord

raiderText = '⁣           Raider       ⁣'
achText = '⁣        Achievements       ⁣'

fullMemberMap = getFullMemberMap()

class getRoles(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "lists all the roles you earned"
        params = []
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):

        destinyID = getUserMap(message.author.id)
        if not destinyID:
            await message.channel.send('please sign up using !registerbo')
            return
        
        async with message.channel.typing():
            (roleList,removeRoles) = getPlayerRoles(destinyID)
            await assignRolesToUser(roleList, message.author, message.guild)
            await removeRolesFromUser(removeRoles,message.author,message.guild)

            for role in roleList:
                if role in requirementHashes['Addition']:
                    await message.author.add_roles(discord.utils.get(message.guild.roles, name=achText))
                else:
                    await message.author.add_roles(discord.utils.get(message.guild.roles, name=raiderText))
            await message.channel.send(f'you have the roles {", ".join(roleList)}')


class assignAllRoles(BaseCommand):
    def __init__(self):
        # A quick description for the help message
        description = "Assigns everyone the roles they earned"
        params = []
        super().__init__(description, params)
    
    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):
        for discordUser in message.guild.members:
            
            destinyID = getUserMap(message.author.id)
            if not destinyID:
                destinyID = getUserIDbySnowflakeAndClanLookup(discordUser,fullMemberMap)

            async with message.channel.typing():
                (newRoles, removeRoles) = getPlayerRoles(destinyID)
                await assignRolesToUser(newRoles, discordUser, message.guild)
                await removeRolesFromUser(removeRoles, discordUser, message.guild)
            await message.channel.send('All roles assigned')
