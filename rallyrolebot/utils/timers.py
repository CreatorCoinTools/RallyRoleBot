import time
import data
import asyncio


class Timers:
    def __init__(self, bot):
        self.bot = bot

    def run_old(self):
        """Starts up old timers that weren't finished when the bot was closed."""

        print('running old timers')
        # get all the timers attached to a self.bot and run them
        timers = data.get_all_timers(self.bot.user.id)
        for timer in timers:
            asyncio.create_task(self.run(timer))

    async def run(self, timer: dict) -> None:
        """
        Run a timer.

        @param timer: Timer object dict
        """
        now = round(time.time())

        # if timer hasn't expired yet, wait for needed amount
        if timer['expires'] > now:
            await asyncio.sleep(int(timer['expires'] - now))

        # call timer event when timer is finished
        self.call_event(timer)

    def call_event(self, timer):
        """
        Call provided timer event.

        @param timer: Timer object dict
        """
        # check if timer has been deleted, if it hasn't call provided event
        timer = data.get_timer(timer['id'])
        if not timer:
            return

        # delete timer
        data.delete_timer(timer['id'])

        # dispatch event
        self.bot.dispatch(f'{timer["event"]}_timer_over', timer)

    def create(self, *, guild_id: int, expires: int, event: str, extras: dict, bot_id: int) -> None:
        """
        Create a new timer to run in the background, slowly ticking away, until its time to strike.

        @param guild_id: guild id
        @param expires: time when timer expires (epoch time)
        @param event: event to call when timer is over "on_{event}_timer_over"
        @param extras: extra values
        @param bot_id: bot id
        """

        timer = {
            'guildId': guild_id,
            'expires': expires,
            'event': event,
            'extras': extras,
            'bot_id': bot_id
        }

        timer_id = data.add_timer(timer)
        timer['id'] = timer_id
        asyncio.create_task(self.run(timer))
