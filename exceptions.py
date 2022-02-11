class NoResponseError(Exception):
    """ Ошибка получения ответа """
    pass


class VerdictError(Exception):
    """Неизвестный вердикт"""
    pass