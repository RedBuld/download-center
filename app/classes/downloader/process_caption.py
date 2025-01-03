from .frame import DownloaderFrame

class DownloaderProcessCaption( DownloaderFrame ):

    async def ProcessCaption( self ) -> None:

        if self.temp.book_title and self.temp.book_url:
            self.result.caption += f'<b><a href="{self.temp.book_url}">{self.temp.book_title}</a></b>\n'

        elif self.temp.book_title:
            self.result.caption += f'<b>{self.temp.book_title}</b>\n'
        
        if len( self.temp.authors ) > 0:
            authors: str = ', '.join( self.temp.authors )
            if len( self.temp.authors ) > 1:
                self.result.caption += f'Авторы: {authors}\n'
            else:
                self.result.caption += f'Автор: {authors}\n'
        
        seria = self.temp.seria_name
        if self.temp.seria_number:
            seria = f'{seria} #{self.temp.seria_number}'
        
        if seria and self.temp.seria_url:
            self.result.caption += f'Серия: <a href="{self.temp.seria_url}">{seria}</a>\n'
        elif seria:
            self.result.caption += f'Серия: {seria}\n'
        
        if self.temp.chapters:
            self.result.caption += f'\n{self.temp.chapters}\n'

        if len( self.temp.hashtags ) > 0:
            hashtags = ' '.join( self.temp.hashtags )
            self.result.caption += f'\n{hashtags}'
