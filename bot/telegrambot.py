from django_telegrambot.apps import DjangoTelegramBot
from telegram import KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, Filters

from .models import Project, ReferralUser

main_keyboard = ReplyKeyboardMarkup([
    [KeyboardButton('Как зарабатывать в интернете')],
    [KeyboardButton('Приглашенные друзья')],
    [KeyboardButton('Заказать')],
])

go_back_keyboard = ReplyKeyboardMarkup([
    [KeyboardButton('Назад')]
], resize_keyboard=True)


def start(bot, update):
    """
    Функция для регистрации новых пользователей
    """
    name = update.message.chat.first_name
    if update.message.chat.last_name:
        name += ' {}'.format(update.message.chat.last_name)
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
        user = None
    except ReferralUser.DoesNotExist:
        user = ReferralUser.objects.create(
            chat_id=update.message.chat_id,
            name=name,
            parent=parent
        )
        if parent is not None:
            update_balance(user.id)
    update.message.reply_text(text=text, reply_markup=main_keyboard)


def update_balance(user_id):
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
    projects = Project.objects.all()
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton(project.title)] for project in projects
    ])
    update.message.reply_text('Проекты по заработку в интернете:',
                              reply_markup=keyboard)


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
    update.message.reply_text('Приглашенные друзья', reply_markup=keyboard)


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
    elif text in projects:
        show_project(bot, update)


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
        reply_text = '{}\n{}\n'.format(project.title, project.description)
        if project.link:
            reply_text += 'Ссылка: {}'.format(project.link)
        if project.image:
            bot.sendPhoto(update.message.chat_id,
                          photo=open(project.image.path, 'rb'),
                          caption=reply_text,
                          reply_markup=go_back_keyboard)
        else:
            bot.sendMessage(update.message.chat_id,
                            reply_text,
                            reply_markup=go_back_keyboard)


def main():

    # Default dispatcher (this is related to the first bot in settings.DJANGO_TELEGRAMBOT['BOTS'])
    dp = DjangoTelegramBot.dispatcher
    # To get Dispatcher related to a specific bot
    # dp = DjangoTelegramBot.getDispatcher('BOT_n_token')     #get by bot token
    # dp = DjangoTelegramBot.getDispatcher('BOT_n_username')  #get by bot username

    # on different commands - answer in Telegram

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text, text_processing))