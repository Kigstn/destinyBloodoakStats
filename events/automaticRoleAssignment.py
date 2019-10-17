from events.base_event      import BaseEvent
from commands.base_command  import BaseCommand
from utils                  import get_channel

from datetime               import datetime
from commands.getRoles      import getAllRoles

# Your friendly example event
# You can name this class as you like, but make sure to set BaseEvent
# as the parent class
class AutomaticRoleAssignment(BaseEvent):

    def __init__(self):
        interval_minutes = 2  # Set the interval for this event
        super().__init__(interval_minutes)

    # Override the run() method
    # It will be called once every {interval_minutes} minutes
    async def run(self, client):
        #print('autorun')
        channel = get_channel(client, "testing")
        #print(channel)
        lastMessage = await channel.fetch_message(channel.last_message_id)
        await getAllRoles().handle(None,lastMessage,client)
        #print('roles gotten')
        await channel.send('automatic role-assignment complete')
