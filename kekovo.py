#!/usr/bin/env python
# -*- coding: utf-8 -*-

import telebot
import vk
from telebot import types
import feedparser
import html
from threading import Thread
import time
from datetime import datetime


#костыли для демки
rss_list = {}
pubs = {}
posts = {}
n = 0


#авторизация бота
tele_token = '906268583:AAHIGqA1LHF1kQj1WIr60ufl1_mLSrsM2ao'
bot = telebot.TeleBot(token = tele_token)


#авторизация вк
vk_token = 'c7f20537bcb704864b258eca9f08be0dd854512728470d2df54dd349277cea86914d7901fd69b129358de' #бот пока только со мной работает
vk_session = vk.Session(vk_token)
vk_api = vk.API(vk_session, v = '5.103')


#функция работающая с рсс лентами
def rss():

    #проверяю сколько постов появилось с прошлого запроса, проверяя на каком месте стоит последний пост прошлого запроса
    def check_last_post(p, last):
        n = 0
        #перевод http хэдера времени в юникстайм
        try:
            while datetime.strptime(p['entries'][n]['published'][:-5]+'GMT', "%a, %d %b %Y %X %Z").strftime("%s") != last:
                n += 1
        except:
            pass
        return n


    while True:
        for url in rss_list:
            p = feedparser.parse(url)
            kek = check_last_post(p, rss_list[url][0])
            for i in range(kek):
                send_post(p['entries'][i], rss_list[url][1])
                time.sleep(5)
            p = feedparser.parse(url)
            #перевод http хэдера времени в юникстайм
            rss_list[url][0] = datetime.strptime(p['entries'][0]['published'][:-5]+'GMT', "%a, %d %b %Y %X %Z").strftime("%s")
        time.sleep(180)


def post_normalization(text):
    n = 0
    if '<' in text:
        temp = ''
        j = 0
        x = len(text)
        #вычищаю вставки html кода по типу картинок
        #да это говнокод
        while True:
            if j == x:
                break
            if text[j] == '<':
                while text[j] != '>':
                    j += 1
            else:
                temp += text[j]
            j += 1
    else:
        temp = text
    #преобразование html символов в человеческий аскии 
    return html.unescape(temp)


# я на этом учился работать с апи ботов
# @bot.message_handler(commands=["start"])
# def repeat_all_messages(message):
#     msg = bot.send_message(user, text = 'Что будем писать?')
#     bot.register_next_step_handler(msg, get_text)


# def get_text(message):
#     global n
#     posts[str(n)] = message
#     keyboard = types.InlineKeyboardMarkup()
#     for i in pubs):
#         keyboard.add(types.InlineKeyboardButton(text = pubs[i], callback_data=str(n)+"_"+str(i)))
#     n+=1
#     msg = bot.send_message(message.chat.id, text = '', reply_markup=keyboard)

#не знаю почему так работает, код кнопки из инета
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.message:
        #я уже забыл что это делает, но работает же
        temp = ''
        for i in call.data:
            if i == '_':
                break
            else:
                temp += i
        vk_api.wall.post(owner_id = -1 * int(call.data[len(temp)+1:]), from_group = 1, message = post_normalization(posts[temp]['summary']), attachments = posts[temp]['links'][0]['href'])

#узнаём урлу рсс фида
@bot.message_handler(commands = ['add_url'])
def ask_url(message):
    msg = bot.send_message(message.chat.id, text = 'Пришлите ссылку на rss ленту')
    bot.register_next_step_handler(msg, add_url)

#пробуем добавить рсс фид 
def add_url(message):
    p = feedparser.parse(message.text)
    try:
        if rss_list.get(message.text) == None:
            rss_list[message.text] = [datetime.strptime(p['entries'][0]['published'][:-5]+'GMT', "%a, %d %b %Y %X %Z").strftime("%s"),[]]
        rss_list[message.text][1].append(message.chat.id)
        bot.send_message(message.chat.id, text = 'Лента успешно добавлена!')
    except:
        bot.send_message(message.chat.id, text = 'Я хз как, но ты выпал в exception')

#узнаём айди группы 
@bot.message_handler(commands=['add_group'])
def ask_group(message):
    msg = bot.send_message(message.chat.id, text = 'Пришли всё что находится правее "vk.cоm/" в адресе твоей группы')
    bot.register_next_step_handler(msg, check_admin)


#проверяем есть ли у нас админский доступ к группе
def check_admin(message):
    try:
        global gid
        gid = vk_api.groups.getById(group_id = message.text)[0]['id']
        try:
            check = vk_api.groups.getBanned(group_id = gid)
            msg = bot.send_message(message.chat.id, text = 'Как назвать группу?')
            bot.register_next_step_handler(msg,name_group)
        except:
            # bot.send_message(message.chat.id, text = 'ты быдло и это не твой паблик')
            bot.send_message(message.chat.id, text = 'У вас нету доступа к управлению этой группой')
    except:
        # bot.send_message(message.chat.id, text = 'ты криворукий дебил прислал мне левую хрень')
        bot.send_message(message.chat.id, text = 'Айди введён некорректно')

#называем группу (костыль, из-за отсутствия нормальной бд любой человек может переименовать паблик у всех остальных)
def name_group(message):
    global gid
    pubs[gid] = message.text
    bot.send_message(message.chat.id, text = 'Группа успешно добавлена!') 

#просто вывод всей инфы которая в данный момент есть у бота
@bot.message_handler(commands = ['debug'])
def debug(message):
    bot.send_message(message.chat.id, text ='урлы: ' + str(rss_list) + '; группы: ' + str(pubs))

#кусок кода, присылает всем подписанным на данную ленту новые посты
#бд нет поэтому он работает нормально только с одним человеком за раз, демка же блинб
def send_post(p,users):
    global n
    posts[str(n)] = p
    keyboard = types.InlineKeyboardMarkup()
    for i in (pubs):
        keyboard.add(types.InlineKeyboardButton(text = pubs[i], callback_data = str(n) + "_" + str(i)))
    n += 1
    for user in users:
        # try:
        #     оказалоьсь ненужным тк фотка появляется по ссылке, а две фотки нафиг не нужно        
        #     bot.send_photo(user, p['links'][1]['href'])
        # except:
        #     pass
        msg = bot.send_message(user, text = (post_normalization(p['summary']) + ' ' + p['links'][0]['href']), reply_markup = keyboard)


def polling():
    bot.polling(none_stop=True)


polling_thread = Thread(target = polling)
rss_thread = Thread(target = rss)

polling_thread.start()
rss_thread.start()
