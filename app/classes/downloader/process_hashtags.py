import re
from typing import List

from .frame import DownloaderFrame

class DownloaderProcessHashtags( DownloaderFrame ):

    async def ProcessHashtags( self ) -> None:
        hashtags_format = self.request.hashtags

        if hashtags_format == 'bf':
            self.temp.hashtags = await self.processHashtagsBF()

        elif hashtags_format == 'gf':
            self.temp.hashtags = await self.processHashtagsGF()

        else:
            self.temp.hashtags = []


    async def processHashtagsBF( self ) -> List[ str ]:
        hashtags = []
        for hashtag in self.temp.hashtags:
            hashtag = re.sub( r'[^A-Za-z0-9А-Яа-яёЁ]', ' ', hashtag ).strip()
            hashtag = re.sub( r'\s+', '_', hashtag )
            hashtags.append( f'#{hashtag}' )
        return hashtags


    async def processHashtagsGF( self ) -> List[ str ]:
        hashtags = []
        for hashtag in self.temp.hashtags:
            hashtag = re.sub( r'[^A-Za-z0-9А-Яа-яёЁ]', '', hashtag ).lower()
            hashtags.append( f'#{hashtag}' )
        return hashtags