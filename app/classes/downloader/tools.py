from app import variables

from .frame import DownloaderFrame

class DownloaderTools( DownloaderFrame ):

    async def ProcessError(
        self,
        err: Exception
    ) -> None:
    
        if self.__is_step__( variables.DownloaderStep.CANCELLED ):
            return

        self.SetStep( variables.DownloaderStep.ERROR )

        message = 'Произошла ошибка: '

        if 'с ошибкой' in self.dbg_log:
            if 'Получен бан. Попробуйте позже' in self.dbg_log:
                message += 'Получен бан. Попробуйте позднее.'
            elif 'Не удалось авторизоваться.' in self.dbg_log:
                message += 'Не удалось авторизоваться. Проверьте сохраненные доступы.'
            elif 'due to the configured HttpClient.Timeout' in self.dbg_log:
                message += 'Сайт не отвечает. Попробуйте позднее.'
        else:
            message += '\n<pre>\n'+ self.escapeErrorText( str( err ) )[ :2000 ] +'\n</pre>'
        
        return message

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