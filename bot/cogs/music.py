from discord_slash.model import ButtonStyle, SlashCommandOptionType
from discord_slash import SlashContext, ComponentContext
import discord_slash.utils.manage_components as mc
from urllib.error import HTTPError
from discord_slash import cog_ext
from discord.ext import commands
from yt_dlp import YoutubeDL
from urllib import request
import concurrent.futures
import datetime
import asyncio
import discord
import random
import time
import re
import os

ERR_NOT_IN_VC = 'You must be in a voice channel to use this command.'
ERR_NO_PLAYER = 'Nothing is playing.'
ERR_UNKNOWN = 'An unknown error has occurred.'



def player_controls():
    return mc.create_actionrow(
        mc.create_button(
            style=ButtonStyle.gray,
            label="Prev",
            emoji="⏪️",
        ),
        mc.create_button(
            style=ButtonStyle.gray,
            label="Play/Pause",
            emoji="⏯️",
        ),
        mc.create_button(
            style=ButtonStyle.gray,
            label="Skip",
            emoji="⏩️",
        )
    )


pattern_url = re.compile(
    r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$')


def is_url(url: str) -> bool:
    return pattern_url.match(url) is not None


async def is_url_ok(url: str) -> int:
    def _request(_url: str):
        try:
            req = request.Request(_url, method='HEAD')
            res = request.urlopen(req)
            return True, res.code
        except HTTPError as err:
            return False, err.code

    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, _request, url)


async def youtube_extract_info(url: str):
    def _extract(_url: str):
        try:
            opts = {
                'extract_flat': True,
                'skip_download': True,
            }
            with YoutubeDL(opts) as ydl:
                return ydl.extract_info(_url, download=False, process=False)
        except:
            return None

    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, _extract, url)


class Song():
    def __init__(self, url, requester_id=None):
        self.url = url
        self.info = None
        self.info_expiry = 0
        self.is_valid = True
        self.requester_id = requester_id

    async def get_info(self):
        if self.info is None or time.time() > self.info_expiry:
            self.info = await youtube_extract_info(self.url)
            self.info_expiry = time.time() + (3 * 60 * 60)

        if self.info is None or \
                'duration' not in self.info or \
                'formats' not in self.info or \
                self.info['duration'] is None:
            self.is_valid = False
            return None

        return self.info

    async def get_title(self):
        if await self.get_info() is not None:
            return self.info['title']
        return '(error)'

    async def _get_audio_url(self):
        if await self.get_info() is not None:
            formats = self.info['formats']
            # Prefer opus
            for fmt in formats:
                if fmt['format_id'] == '251':
                    return fmt['url']
            # Fall back to any audio otherwise
            for fmt in formats:
                if fmt['acodec'] != 'none':
                    return fmt['url']
        return None

    async def get_audio_url(self):
        for _ in range(3):
            url = await self._get_audio_url()
            if url is None:
                return None

            # Check if URL is valid
            if await is_url_ok(url):
                return url
            else:
                # Force refetch info if URL isn't valid
                self.info_expiry = 0

        return None

    async def get_duration(self):
        if await self.get_info() is not None:
            return self.info['duration']
        return 0


class Playlist():
    def __init__(self):
        self.song_list = []
        self.current_index = 0

    def __len__(self):
        return len(self.song_list)

    def insert(self, song):
        self.song_list.append(song)

    def clear(self):
        self.song_list.clear()
        self.current_index = 0

    def shuffle(self):
        current_song = self.song_list.pop(self.current_index)
        random.shuffle(self.song_list)
        self.song_list.insert(0, current_song)
        self.current_index = 0

    def now_playing(self):
        if self.current_index >= len(self) or self.current_index < 0:
            return None
        return self.song_list[self.current_index]

    def get_list(self):
        return self.song_list

    def get_index(self):
        return self.current_index

    def jump(self, number, *, relative=True):
        new_index = number if not relative else self.current_index + number
        new_index = min(new_index, len(self) - 1)
        new_index = max(new_index, 0)
        self.current_index = new_index
        return self.now_playing()

    def remove(self, index):
        if index < self.current_index:
            self.current_index -= 1

        return self.song_list.pop(index)

    def has_next(self):
        return self.current_index + 1 < len(self)

    def has_prev(self):
        return self.current_index - 1 > 0

    def go_next(self):
        return self.jump(1)

    def go_prev(self):
        return self.jump(-1)


class PlayerInstance():
    LOOP_NONE = 'none'
    LOOP_SONG = 'song'
    LOOP_QUEUE = 'queue'

    def __init__(self, voice_client: discord.VoiceClient):
        self.voice_client = voice_client
        self.playlist = Playlist()
        self.skip_next_callback = False
        self.loop_mode = self.LOOP_NONE

    async def queue_url(self, url, requester_id=None):
        queued_songs = []

        # Check type of URL
        if 'youtu.be' in url or '/watch?v=' in url:
            # Force youtube-dl to extract video instead of playlist
            url = url.replace('&list=', '&_list=')
            song = Song(url, requester_id)
            queued_songs.append(song)
        elif 'youtube.com/playlist' in url:
            # Fetch playlist
            info = await youtube_extract_info(url)
            for entry in info['entries']:
                song = Song('https://youtu.be/{}'.format(entry['id']), requester_id)
                queued_songs.append(song)

        for song in queued_songs:
            self.playlist.insert(song)

        return queued_songs

    def is_playing(self):
        return self.voice_client.is_playing()

    async def play_next(self):
        if self.loop_mode == self.LOOP_SONG:
            return await self.play()

        if self.playlist.has_next():
            self.playlist.go_next()
        elif self.loop_mode == self.LOOP_QUEUE:
            self.playlist.jump(0, relative=False)
        else:
            return False

        return await self.play()

    async def play(self):
        song = self.playlist.now_playing()
        if song is None:
            return False

        url = await song.get_audio_url()
        if url is None:
            return await self.play_next()

        source = await discord.FFmpegOpusAudio.from_probe(
            executable=f"{os.getcwd()}/ffmpeg.exe",
            source=url,
            before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
        )

        self.skip_next_callback = True
        if self.voice_client.is_playing():
            self.voice_client.stop()

        loop = asyncio.get_running_loop()

        def handle_next(error):
            if self.skip_next_callback:
                self.skip_next_callback = False
                return
            asyncio.run_coroutine_threadsafe(self.play_next(), loop)

        self.voice_client.play(source, after=handle_next)
        await asyncio.sleep(1)
        self.skip_next_callback = False

        return True

    async def pause(self):
        self.voice_client.pause()

    async def resume(self):
        self.voice_client.resume()

    async def stop(self):
        if self.voice_client.is_playing():
            self.skip_next_callback = True
            self.voice_client.stop()


def format_duration(seconds: int) -> str:
    duration = str(datetime.timedelta(seconds=seconds))

    # Trim hour if 0
    if duration.startswith('0:'):
        duration = duration[2:]

    return duration


async def now_playing(player: PlayerInstance) -> discord.Embed:
    idx = player.playlist.get_index()
    np = player.playlist.now_playing()
    if np is None:
        return discord.Embed(
            description=ERR_NO_PLAYER
        )

    embed = discord.Embed(
        title=await np.get_title(),
        url=np.url,
    )
    embed.set_author(
        name=f'Now playing #{idx + 1}'
    )
    embed.add_field(
        name='Duration',
        value=format_duration(await np.get_duration())
    )
    embed.add_field(
        name='Requested by',
        value=f'<@{np.requester_id}>'
    )

    return embed


async def format_song(song: Song):
    title = await song.get_title()
    url = song.url
    requester = song.requester_id
    duration = format_duration(await song.get_duration())

    return f'[{title}]({url}) | {duration} | <@{requester}>'


async def queue(player: PlayerInstance) -> discord.Embed:
    current_index = player.playlist.get_index()
    slice_start = max(0, current_index - 5)
    slice_end = current_index + 5
    full_list = player.playlist.get_list()
    partial_list = full_list[slice_start:slice_end]
    partial_index = current_index - slice_start

    message = ''
    for idx, song in enumerate(partial_list):
        display_idx = slice_start + idx + 1
        song_str = await format_song(song)

        if idx == partial_index:
            message += '__Now playing:__\n**'
        message += f'{display_idx}. {song_str}'
        if idx == partial_index:
            message += '**'
        message += '\n'

    embed = discord.Embed(
        title='Queue',
        description=message,
    )
    embed.set_footer(text='{} songs in queue'.format(len(full_list)))
    return embed



class Music(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.players: dict[int, PlayerInstance] = {}

    async def connect_vc(self, ctx: SlashContext):
        voice_channel = ctx.author.voice.channel if ctx.author.voice is not None else None
        if voice_channel is None:
            return False

        if ctx.voice_client is not None and ctx.voice_client.is_connected():
            await ctx.voice_client.move_to(voice_channel)
        else:
            voice_client = await voice_channel.connect()
            self.players[voice_channel.id] = PlayerInstance(voice_client)
        return True

    def get_player(self, ctx: SlashContext):
        if ctx.voice_client is None:
            return None

        vc_id = ctx.voice_client.channel.id
        if vc_id in self.players:
            return self.players[vc_id]
        return None

    async def get_player_or_connect(self, ctx: SlashContext, *, reply=False):
        player = self.get_player(ctx)
        if player is None:
            if not await self.connect_vc(ctx):
                if reply:
                    await ctx.send(content=ERR_NOT_IN_VC)
                return None
            player = self.get_player(ctx)

        if player is None and reply:
            await ctx.send(content=ERR_UNKNOWN)

        return player

    @cog_ext.cog_component(use_callback_name=True)
    async def handle_component(self, ctx: ComponentContext):
        pass

    @cog_ext.cog_slash(
        name='join',
        description='Join the VC'
    )
    async def join(self, ctx: SlashContext):
        if not await self.connect_vc(ctx):
            return await ctx.send(content=ERR_NOT_IN_VC)

        await ctx.send(content='Hi!')

    @cog_ext.cog_slash(
        name='leave',
        description='Leave the VC'
    )
    async def leave(self, ctx: SlashContext):
        voice_channel = ctx.author.voice.channel if ctx.author.voice is not None else None
        if voice_channel is None:
            await ctx.send(content=ERR_NOT_IN_VC)
            return

        await ctx.voice_client.disconnect(force=True)
        self.players[voice_channel.id] = None

        await ctx.send(content='Bye!')

    @cog_ext.cog_slash(
        name='play',
        description='Add a song to the queue',
        options=[
            {
                'name': 'query',
                'description': 'YouTube video or playlist URL, search query, or queue number',
                'type': SlashCommandOptionType.STRING,
                'required': True
            }
        ]
    )
    async def play(self, ctx: SlashContext, etc=None, *, query):
        await ctx.defer()
        player = await self.get_player_or_connect(ctx, reply=True)
        if player is None:
            return

        requester_id = ctx.author_id
        queue_empty = len(player.playlist) == 0
        queue_ended = not player.playlist.has_next()

        # If query is a number, jump to that playlist index
        if query.isnumeric():
            player.playlist.jump(int(query) - 1, relative=False)

            if await player.play():
                await ctx.send(embed=await now_playing(player))
            else:
                await ctx.send(content='End of queue')
            return

        songs = []
        if is_url(query):
            # Query is a URL, queue it
            songs = await player.queue_url(query, requester_id)
        else:
            # Search YouTube and get first result
            search = await youtube_extract_info(f'ytsearch1:{query}')
            results = list(search['entries'])
            url = 'https://youtu.be/' + results[0]['id']
            songs = await player.queue_url(url, requester_id)

        if len(songs) > 1:
            await ctx.send(
                content='{} songs queued'.format(len(songs))
            )
        elif len(songs) == 1:
            song = await format_song(songs[0])
            await ctx.send(content=f'Queued: {song}')
        else:
            await ctx.send(content='No songs queued')

        # Don't disturb the player if it's already playing
        if player.is_playing():
            return

        # If the player is fresh, play
        if queue_empty:
            return await player.play()

        # If it isn't playing because it reached the end of the queue,
        # play the song that was just added to the queue
        if queue_ended:
            return await player.play_next()

        # Otherwise resume playback
        await player.resume()

    @cog_ext.cog_slash(
        name='queue',
        description='Show the current queue'
    )
    async def queue_list(self, ctx: SlashContext):
        player = self.get_player(ctx)
        if player is None:
            return await ctx.send(content=ERR_NO_PLAYER)

        await ctx.defer()

        embed = await queue(player)
        await ctx.send(embed=embed)

    @cog_ext.cog_slash(
        name='clear',
        description='Remove all songs from the current queue'
    )
    async def queue_clear(self, ctx: SlashContext):
        player = self.get_player(ctx)
        if player is None:
            return await ctx.send(content=ERR_NO_PLAYER)

        await player.stop()
        player.playlist.clear()

        await ctx.send(content='Queue cleared!')

    @cog_ext.cog_slash(
        name='shuffle',
        description='Shuffle the order of songs in the queue'
    )
    async def queue_shuffle(self, ctx: SlashContext):
        player = self.get_player(ctx)
        if player is None:
            return await ctx.send(content=ERR_NO_PLAYER)

        player.playlist.shuffle()
        await ctx.send(content='Queue shuffled!')

    @cog_ext.cog_slash(
        name='skip',
        description='Skip current song',
        options=[
            {
                'name': 'number',
                'description': 'How many songs to skip',
                'type': SlashCommandOptionType.INTEGER,
                'required': False
            }
        ]
    )
    async def skip(self, ctx: SlashContext, *, number=1):
        await ctx.defer()
        player = await self.get_player_or_connect(ctx, reply=True)
        if player is None:
            return

        player.playlist.jump(number)

        if await player.play():
            await ctx.send(embed=await now_playing(player))
        else:
            await ctx.send(content='End of queue')

    @cog_ext.cog_slash(
        name='np',
        description='Show the currently playing song'
    )
    async def now_playing(self, ctx: SlashContext):
        player = await self.get_player_or_connect(ctx, reply=True)
        if player is None:
            return

        await ctx.send(embed=await now_playing(player))

    @cog_ext.cog_slash(
        name='pause',
        description='Pause the current song'
    )
    async def pause(self, ctx: SlashContext):
        player = self.get_player(ctx)
        if player is None:
            return await ctx.send(content=ERR_NO_PLAYER)

        if player.is_playing():
            await player.pause()

        await ctx.send(content='Paused')

    @cog_ext.cog_slash(
        name='resume',
        description='Resume playback'
    )
    async def resume(self, ctx: SlashContext):
        player = self.get_player(ctx)
        if player is None:
            return await ctx.send(content=ERR_NO_PLAYER)

        if not player.is_playing():
            await player.resume()

        await ctx.send(embed=await now_playing(player))

    @cog_ext.cog_slash(
        name='loop',
        description='Enable/disable looping',
        options=[
            {
                'name': 'mode',
                'description': 'Loop this song or the whole queue?',
                'type': SlashCommandOptionType.STRING,
                'required': True,
                'choices': [
                    {'name': 'disable', 'value': PlayerInstance.LOOP_NONE},
                    {'name': 'song', 'value': PlayerInstance.LOOP_SONG},
                    {'name': 'queue', 'value': PlayerInstance.LOOP_QUEUE}
                ]
            }
        ]
    )
    async def loop(self, ctx: SlashContext, mode=PlayerInstance.LOOP_NONE):
        player = self.get_player(ctx)
        if player is None:
            return await ctx.send(content=ERR_NO_PLAYER)

        player.loop_mode = mode
        await ctx.send(content=f'Loop mode set to **{mode}**')

    @cog_ext.cog_slash(
        name='remove',
        description='Remove a song from the queue',
        options=[
            {
                'name': 'number',
                'description': 'The queue number of the song to remove',
                'type': SlashCommandOptionType.INTEGER,
                'required': True
            }
        ]
    )
    async def remove_song(self, ctx: SlashContext, number: int):
        player = self.get_player(ctx)
        if player is None:
            return await ctx.send(content=ERR_NO_PLAYER)

        song = player.playlist.remove(number - 1)
        title = await song.get_title()
        url = song.url
        await ctx.send(content=f'Removed #{number} [{title}]({url})')

        if len(player.playlist) == 0:
            return await player.stop()

        if number - 1 == player.playlist.get_index():
            await player.play()


def setup(bot):
    bot.add_cog(Music(bot))
