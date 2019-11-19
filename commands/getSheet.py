from commands.base_command  import BaseCommand
from io import open
from Spreadsheet2 import createSheet

import os
from discord import File
import time

class getSheet(BaseCommand):

    lastupdate = 0.0
    sheetpath = None

    def __init__(self):
        # A quick description for the help message
        self.lastupdate = 0.0
        self.sheetpath = None
        description = "gets the reduced Spreadsheet"
        params = []
        super().__init__(description, params)

    # Override the handle() method
    # It will be called every time the command is received
    async def handle(self, params, message, client):

        if time.time() - self.lastupdate < 86400:
            if self.sheetpath is not None:
                f = File(open(self.sheetpath,'rb'),'AchievementSheet.xlsx')
                await message.channel.send(file=f)
                return

        async with message.channel.typing():
            await message.channel.send('This is gonna take a loooooooong time')
            sheetpath = createSheet()
            if sheetpath is not None:
                f = File(open(sheetpath,'rb'),'AchievementSheet.xlsx')
                await message.channel.send(file=f)
            await message.channel.send('There you go! Thanks for waiting')
            self.lastupdate = time.time()

