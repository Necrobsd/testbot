import logging
import re

from django.core.mail import send_mail
from django_telegrambot.apps import DjangoTelegramBot
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (CommandHandler, MessageHandler, RegexHandler,
                          Filters, ConversationHandler)

from testbot.settings import EMAIL_HOST_USER
from .models import Project, ReferralUser, Settings


logger = logging.getLogger(__name__)

main_keyboard = ReplyKeyboardMarkup([
    [KeyboardButton('Как зарабатывать в интернете')],
    [KeyboardButton('Приглашенные друзья')],
    [KeyboardButton('Заказать')],
])

go_back_keyboard = ReplyKeyboardMarkup([
    [KeyboardButton('Назад')]
], resize_keyboard=True)

get_phone_keyboard = ReplyKeyboardMarkup([
    [KeyboardButton('Отправить свой номер телефона', request_contact=True)]
], resize_keyboard=True, one_time_keyboard=True)

orders = {}


def start(bot, update):
    """
    Функция для регистрации новых пользователей
    """
    name = update.message.chat.first_name
    if update.message.chat.last_name:
        name += ' {}'.format(update.message.chat.last_name)
    username = update.message.chat.username
    text = 'Добро пожаловать!'
    try:
        referral_code = update.message.text.split(' ')[1]
    except IndexError:
        referral_code = None
    parent = None
    if referral_code is not None:
        try:
            parent = ReferralUser.objects.get(refer_code=referral_code)
        except ReferralUser.DoesNotExist:
            pass

    try:
        ReferralUser.objects.get(chat_id=update.message.chat_id)
    except ReferralUser.DoesNotExist:
        user = ReferralUser.objects.create(
            chat_id=update.message.chat_id,
            name=name,
            username=username if username is not None else '',
            parent=parent
        )
        if parent is not None:
            increase_balance(user.id)
    update.message.reply_text(text=text, reply_markup=main_keyboard)


def increase_balance(user_id):
    """
    Функция увеличивает баланс у родителей за привлеченного пользователя
    """
    user = ReferralUser.objects.get(id=user_id)
    for parent in user.get_ancestors(ascending=True)[:3]:
        parent.balance += 100
        parent.save()


def home(bot, update):
    """
    Функция отправки пользователя в главное меню
    """
    update.message.reply_text('Выберите действие', reply_markup=main_keyboard)


def projects_list(bot, update):
    """
    Функция отображения списка проектов по заработку в интернете
    """
    text = 'Проекты еще не добавлены'
    keyboard = main_keyboard
    projects = Project.objects.all()
    if projects.exists():
        text = 'Проекты по заработку в интернете:'
        keyboard = ReplyKeyboardMarkup([
            [KeyboardButton(project.title)] for project in projects
        ])
    update.message.reply_text(text, reply_markup=keyboard)


def show_project(bot, update):
    """
    Функция вывода детальной информации по проекту
    """
    text = update.message.text
    try:
        project = Project.objects.get(title=text)
    except Project.DoesNotExist:
        project = None
    if project:
        reply_text = '<b>{title}</b>\n<i>{description}</i>\n'.format(
            title=project.title,
            description=project.description
        )
        if project.image:
            reply_text += '<a href="https://rutests.com{}">&#8205;</a>\n'.format(
                project.image.url
            )
        if project.link:
            reply_text += '<a href="{}">Ссылка на сайт проекта</a>\n'.format(
                project.link
            )

        bot.sendMessage(update.message.chat_id,
                        reply_text,
                        reply_markup=go_back_keyboard,
                        parse_mode='HTML')


def friends_menu(bot, update):
    """
    Функция отображения меню для работы с приглашенными друзьями
    """
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton('Ссылка для приглашения')],
        [KeyboardButton('Список приглашенных')],
        [KeyboardButton('Баланс')],
        [KeyboardButton('Описание')],
        [KeyboardButton('Назад')],
    ])
    update.message.reply_text('Выберите действие', reply_markup=keyboard)


def get_referral_link(bot, update):
    """
    Функция для получения своей реферральной ссылки
    """
    user = ReferralUser.objects.get(chat_id=update.message.chat_id)
    text = 'https://t.me/{bot_name}?start={refer_code}'.format(
        bot_name=bot.username,
        refer_code=user.refer_code
    )
    update.message.reply_text(text)


def show_user_referrals(bot, update):
    """
    Функция для вывода списка приглашенных друзей (реферралов)
    """
    user = None
    try:
        user = ReferralUser.objects.get(chat_id=update.message.chat_id)
    except ReferralUser.DoesNotExist:
        pass
    if user is not None:
        text = 'Ваш список приглашенных пуст'
        referrals_level_1 = user.get_descendants().filter(level=user.level + 1)
        if referrals_level_1.exists():
            text = 'Первый уровень:\n'
            text += '\n'.join('- {}'.format(r.name) for r in referrals_level_1)
        referrals_level_2 = user.get_descendants().filter(level=user.level + 2)
        if referrals_level_2.exists():
            text += '\nВторой уровень:\n'
            text += '\n'.join('- {}'.format(r.name) for r in referrals_level_2)
        referrals_level_3 = user.get_descendants().filter(level=user.level + 3)
        if referrals_level_3.exists():
            text += '\nТретий уровень:\n'
            text += '\n'.join('- {}'.format(r.name) for r in referrals_level_3)
        update.message.reply_text(text)


def get_balance(bot, update):
    """
    Функция для отображения баланса пользователя
    """
    user = None
    try:
        user = ReferralUser.objects.get(chat_id=update.message.chat_id)
    except ReferralUser.DoesNotExist:
        pass
    if user is not None:
        update.message.reply_text('Ваш баланс: {}'.format(user.balance))


def show_description(bot, update):
    """
    Функция выводит описание на странице с приглашенными пользователями
    """
    description = 'Описание пока не добавлено'
    if Settings.objects.exists():
        if Settings.objects.first().referrals_description:
            description = Settings.objects.first().referrals_description
    update.message.reply_text(description)


def show_order_notification(bot, update):
    """
    Функция выводит текст описания при нажании на кнопку Заказать
    """
    text = 'Текст еще не добавлен'
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton('Сделать заказ')]
    ], resize_keyboard=True)
    if Settings.objects.exists():
        if Settings.objects.first().order_text:
            text = Settings.objects.first().order_text
    update.message.reply_text(text, reply_markup=keyboard)


def text_processing(bot, update):
    """
    Функция обработки ответов пользователя
    """
    projects = [project.title for project in Project.objects.all()]
    text = update.message.text
    if text == 'Как зарабатывать в интернете':
        projects_list(bot, update)
    elif text == 'Назад':
        home(bot, update)
    elif text == 'Приглашенные друзья':
        friends_menu(bot, update)
    elif text == 'Список приглашенных':
        show_user_referrals(bot, update)
    elif text == 'Ссылка для приглашения':
        get_referral_link(bot, update)
    elif text == 'Баланс':
        get_balance(bot, update)
    elif text == 'Описание':
        show_description(bot, update)
    elif text in projects:
        show_project(bot, update)
    elif text == 'Заказать':
        show_order_notification(bot, update)


# Диалог с пользователем для создания заказа
CONFIRM_NAME, GET_NAME, PHONE, EMAIL = range(4)


def cancel(bot, update):
    """
    Функция для отмены заказа
    """
    order = orders.get(update.message.chat_id, None)
    if order is not None:
        del orders[update.message.chat_id]
    update.message.reply_text('Заказ отменен')
    home(bot, update)
    return ConversationHandler.END


def start_conversation(bot, update):
    """
    Функция начала диалога
    """
    user = update.message.from_user
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton('Да'), KeyboardButton('Нет')]
    ], resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text('Ваше имя {}?'.format(user.first_name),
                              reply_markup=keyboard)
    return CONFIRM_NAME


def confirm_name(bot, update):
    """
    Функция для подтверждения имени клиента, полученного автоматически
    """
    user = update.message.from_user
    text = update.message.text
    if text == 'Да':
        orders[update.message.chat_id] = {'name': user.first_name}
        if user.username:
            orders[update.message.chat_id].update(
                {'username': '@{}'.format(user.username)}
            )
        update.message.reply_text('Пришлите Ваш номер телефона, или отправьте '
                                  '/cancel для отмены заказа',
                                  reply_markup=get_phone_keyboard)
        return PHONE
    elif text == 'Нет':
        keyboard = ReplyKeyboardRemove()
        update.message.reply_text('Введите Ваше имя, или отправьте /cancel для'
                                  ' отмены заказа',
                                  reply_markup=keyboard)
        return GET_NAME


def get_name(bot, update):
    """
    Функция для получения имени клиента, указанного вручную
    """
    text = update.message.text
    user = update.message.from_user
    orders[update.message.chat_id] = {'name': text}
    if user.username:
        orders[update.message.chat_id].update(
            {'username': '@{}'.format(user.username)}
        )
    update.message.reply_text('Спасибо, {}! '
                              'Пришлите Ваш номер телефона, или отправьте '
                              '/cancel для отмены заказа'.format(text),
                              reply_markup=get_phone_keyboard)
    return PHONE


def get_phone(bot, update):
    """
    Функция для получения номера телефона клиента
    """
    phone_number = update.message.contact.phone_number
    orders[update.message.chat_id].update({'phone': phone_number})
    update.message.reply_text('Спасибо! Теперь укажите Ваш E-mail, или '
                              'отправьте /cancel для отмены заказа',
                              reply_markup=ReplyKeyboardRemove())

    return EMAIL


def get_email(bot, update):
    """
    Функция для получения E-mail адреса клиента
    """
    email = update.message.text
    regex_email = re.compile(
        r'^[a-z0-9](\.?[a-z0-9_-]){0,}@[a-z0-9-]+\.([a-z]{1,6}\.)?[a-z]{2,6}$'
    )
    if regex_email.match(email):
        orders[update.message.chat_id].update({'email': email})
        update.message.reply_text('Ваши данные приняты. Ожидайте '
                                  'с Вами свяжутся в ближайшее время',
                                  reply_markup=ReplyKeyboardRemove())
        message = create_message(orders.get(update.message.chat_id))
        send_message(bot, message)
        send_email_message(message)
        del orders[update.message.chat_id]
        home(bot, update)

        return ConversationHandler.END
    else:
        update.message.reply_text('Введен некорректный Email: {}\n'
                                  'укажите правильный E-mail, или отправьте '
                                  '/cancel для отмены заказа'.format(email),
                                  reply_markup=ReplyKeyboardRemove())
        return EMAIL



def create_message(order_info):
    """
    Создание сообщения
    """
    text = ('Новый заказ!\n'
            'Имя клиента: {name},\n'
            'Ник телеграм: {username},\n'
            'Телефон: {phone},\n'
            'E-mail: {email}'.format(name=order_info.get('name'),
                                     username=order_info.get('username', 'Нет'),
                                     phone=order_info.get('phone'),
                                     email=order_info.get('email')))
    return text


def send_message(bot, message):
    """
    Функция отправки сообщения о заказе в телеграмм
    """

    if Settings.objects.exists():
        if Settings.objects.first().telegram:
            telegram_id = Settings.objects.first().telegram.chat_id
            bot.sendMessage(telegram_id, message)
    else:
        logger.info('Отсутствует Telegram ID для отправки информации о заказах')


def send_email_message(message):
    """
    Отправка сообщения о новом заказе на Email
    """
    email = None
    if Settings.objects.exists():
        if Settings.objects.first().email:
            email = Settings.objects.first().email
    if email is not None:
        try:
            send_mail(subject='Новый заказ',
                      message=message,
                      from_email=EMAIL_HOST_USER,
                      recipient_list=[email],
                      fail_silently=False)
        except Exception as e:
            logger.error('Ошибка отправки E-mail: {}'.format(e))
    else:
        logger.info('Отсутствует Email для отправки информации о заказах')


conv_handler = ConversationHandler(
    entry_points=[RegexHandler('^Сделать заказ$', start_conversation)],
    states={
        CONFIRM_NAME: [RegexHandler('^(Да|Нет)$', confirm_name)],
        GET_NAME: [MessageHandler(Filters.text, get_name)],
        PHONE: [MessageHandler(Filters.contact, get_phone)],
        EMAIL: [MessageHandler(Filters.text, get_email)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.error('Update "%s" caused error "%s"', update, error)


def main():
    dp = DjangoTelegramBot.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(conv_handler)
    dp.add_handler(MessageHandler(Filters.text, text_processing))
    dp.add_error_handler(error)
