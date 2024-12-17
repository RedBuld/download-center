from .frame import DownloaderFrame

class DownloaderProcessCaption( DownloaderFrame ):

    async def ProcessCaption( self ) -> None:

        if self.temp.book_title and self.temp.book_url:
            self.result.caption += f'<a href="{self.temp.book_url}">{self.temp.book_title}</a>\n'

        elif self.temp.book_title:
            self.result.caption += f'{self.temp.book_title}\n'
        
        if len( self.temp.authors ) > 0:
            authors: str = ', '.join( self.temp.authors )
            if len( authors ) > 1:
                self.result.caption += f'Авторы: {authors}\n'
            else:
                self.result.caption += f'Автор: {authors}\n'
        
        if self.temp.seria_name and self.temp.seria_url:
            self.result.caption += f'Серия: <a href="{self.temp.seria_url}">{self.temp.seria_name}</a>\n'
        elif self.temp.seria_name:
            self.result.caption += f'Серия: {self.temp.seria_name}\n'
        
        if self.temp.chapters:
            self.result.caption += f'\n{self.temp.chapters}\n'

        if len( self.temp.hashtags ) > 0:
            hashtags = ' '.join( self.temp.hashtags )
            self.result.caption += f'\n{hashtags}'
