import re
import ujson
from typing import Dict, Any

from .frame import DownloaderFrame

class DownloaderProcessJSON(DownloaderFrame):

    async def ProcessJSON( self ) -> None:

        with open( self.temp.json, "r" ) as f:
            _raw: str = f.read()
            try:
                _json: Dict[ str, Any ] = ujson.loads( _raw )
            except:
                return

            if 'Title' in _json and _json[ 'Title' ]:
                book_title: str = _json[ 'Title' ]
                book_title = book_title.replace( '\n', ' ' )
                book_title = re.sub( r'\s+', ' ', book_title )
                self.temp.book_title = book_title

            if 'Url' in _json and _json[ 'Url' ]:
                self.temp.book_url = _json[ 'Url' ]

            if 'Author' in _json:
                author = _json[ 'Author' ]

                if 'Name' in author:
                    author_name: str = author[ 'Name' ]
                    author_name = author_name.replace( '\n', ' ' )
                    author_name = re.sub( r'\s+', ' ', author_name )

                    self.temp.book_author = author_name

                    self.temp.hashtags.append( author_name )

                    if 'Url' in author:
                        author_url: str = author[ 'Url' ]
                        self.temp.authors.append( f'<a href="{author_url}">{author_name}</a>' )
                    else:
                        self.temp.authors.append( author_name )
                    

            if 'CoAuthors' in _json and _json[ 'CoAuthors' ]:

                for author in _json[ 'CoAuthors' ]:

                    if 'Name' in author:
                        author_name: str = author[ 'Name' ]
                        author_name = author_name.replace( '\n',' ' )
                        author_name = re.sub( r'\s+', ' ', author_name )

                        self.temp.hashtags.append( author_name )

                        if 'Url' in author:
                            coauthor_url: str = author[ 'Url' ]
                            self.temp.authors.append( f'<a href="{coauthor_url}">{author_name}</a>' )
                        else:
                            self.temp.authors.append( author_name )

            if 'Seria' in _json and _json[ 'Seria' ]:
                seria = _json[ 'Seria' ]

                if 'Name' in seria:
                    seria_name: str = seria[ 'Name' ]
                    seria_name = seria_name.replace( '\n', ' ' )
                    seria_name = re.sub( r'\s+', ' ', seria_name )

                    self.temp.seria_name = seria_name

                    self.temp.hashtags.append( seria_name )

                    if 'Number' in seria:
                        self.temp.seria_number = str( seria[ 'Number' ] )

                    if 'Url' in seria:
                        self.temp.seria_url = seria[ 'Url' ]

            if 'Chapters' in _json and _json[ 'Chapters' ]:
                chapters = _json[ 'Chapters' ]

                if len( chapters ) > 0:

                    for chapter in chapters:

                        if chapter[ 'Title' ]:
                            self.temp.chapters_total += 1

                            if chapter[ 'IsValid' ]:
                                self.temp.chapters_valid += 1

                                chapter_name: str = chapter[ 'Title' ]
                                chapter_name = chapter_name.replace('\n',' ')

                                if not self.temp.first_chapter:
                                    self.temp.first_chapter = chapter_name
                                
                                self.temp.last_chapter = chapter_name

        self.temp.first_chapter = re.sub( r'\s+', ' ', self.temp.first_chapter )
        if len( self.temp.first_chapter ) > 200:
            self.temp.first_chapter = self.temp.first_chapter[:197] + '...'

        self.temp.last_chapter = re.sub( r'\s+', ' ', self.temp.last_chapter )
        if len( self.temp.last_chapter ) > 200:
            self.temp.last_chapter = self.temp.last_chapter[:197] + '...'