from app import variables

from .frame import DownloaderFrame

class DownloaderTools( DownloaderFrame ):

    async def ProcessError(
        self,
        err: Exception
    ) -> None:
    
        if self.__is_status__( variables.DownloaderStatus.CANCELLED ):
            return

        self.SetStatus( variables.DownloaderStatus.ERROR )

        message = 'Произошла ошибка'

        extended_log = True

        if 'с ошибкой' in self.dbg_log:
            if 'Получен бан. Попробуйте позже' in self.dbg_log:
                message += ': Получен бан. Попробуйте позднее.'
                extended_log = False
            elif 'Не удалось авторизоваться.' in self.dbg_log:
                message += ': Не удалось авторизоваться. Проверьте сохраненные доступы.'
                extended_log = False
            elif 'due to the configured HttpClient.Timeout' in self.dbg_log:
                message += ': Сайт не отвечает. Попробуйте позднее.'
                extended_log = False

        if extended_log:
            err_msg = str( err )
            if err_msg:
                message += '\n<pre>\n'+ self.escapeErrorText( err_msg )[ :2000 ] +'\n</pre>'
        
        self.result.caption = message
        self.result.cover = ''
        self.result.files = []

    def escapeErrorText(
        self,
        text: str
    ) -> str:
        text = text.translate(
            str.maketrans(
                {
                    '<': '&lt;',
                    '>': '&rt;',
                    '&': '&amp;',
                    '\'': '&quot;',
                    '\"': '&quot;',
                }
            )
        )
        return text