from .frame import DownloaderFrame

class DownloaderProcessChapters( DownloaderFrame ):

    async def ProcessChapters( self ) -> None:

        base_part = self.temp.last_chapter
        suffix = ''
        
        _total = self.temp.chapters_total
        _valid = self.temp.chapters_valid

        if _valid > 1:
            base_part = f'По: "{base_part}"'

        if _total > 0:
            _start = int( self.request.start )
            _end = int( self.request.end )

            if _start != 0 and _end != 0:
                suffix = f'{_start} - {_end}'

            elif _start != 0 and _end == 0:

                if _start > 0:
                    _end = _start + _total
                    suffix = f'{_start} - {_end}'

            elif _start == 0 and _end != 0:
                suffix = f'1 - {_total}'
        
        if _valid < _total:
            if suffix:
                suffix += f' / {_total}'
            else:
                suffix += f'{_valid} / {_total}'

        if suffix:
            suffix = f' [{suffix}]'

        self.temp.chapters = f'{base_part}{suffix}'