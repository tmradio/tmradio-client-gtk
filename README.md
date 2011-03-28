Функции
=======

- Проигрывание потока.
- Перезапуск проигрывания при обрыве связи.
- Настраиваемый адрес потока.
- Доступ к покдастам.  Пока выводится простой список с возможностью открыть
  страницу эпизода и скачать файл.  В будущем планируется добавить проигрывание
  прямо из программы.


Благодарности
=============

- hakimovis
- iconshock.com (иконка)


Как работает jabber
===================

Для максимальной эффективности работа вынесена в отдельный тред.
Взаимодействовать с интерфейсом должен только один поток, поэтому
взаимодействие джаббера и интерфейса минимизировано.  Входящие события, о
которых сообщает jabber, бывают следующими:

- Стала известна новая информация о текущей дорожке.
- Пришло сообщение в чат.

Исходящие сообщения:

- Сообщение в чат.
- Голосование за дорожку.
- Редактирование свойств дорожки.

Всё исходящее — это обычные текстовые сообщения.  Они однотипные, достаточно
простой очереди, защищённой блокировками.  Входящие сообщения чата — примерно
то же самое, только в обратном направлении.

Информация о дорожках может выдаваться как очередь пар ключ-значение, то есть в
интерфейсный поток будет приходить набор примерно таких данных:

    ("track_id", "3892")
    ("artist", "Mobil")
    ("title", "The Winter's Story")
    ("labels", "calm electronic instrumental music")

Для надёжности (атомарности) можно передавать полученные данные сразу списком,
чтобы исключить не очень вероятную, но возможную ситуацию, когда пользователь
отправляет изменённое название дорожки, в этот момент меняется свойство
track_id, заголовок устанавливается для другой дорожки.


Материал для внеклассного чтения
================================

- [Переменные окружения Питона](http://docs.python.org/using/cmdline.html#environment-variables)
- [Writing the Setup Script](http://docs.python.org/distutils/setupscript.html)
