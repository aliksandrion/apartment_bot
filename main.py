from settings import BOT_TOKEN, HEADERS, CITY_CODE

from pyTelegramBotAPI import telebot
from telebot import types
from telebot.types import InputMediaPhoto

from bs4 import BeautifulSoup as b
import requests
import re
from time import sleep

bot = telebot.TeleBot(BOT_TOKEN)
url = 'https://www.'
count_of_ad = 0  # counter for sending 5 messages
page_counter = 1


@bot.message_handler(commands=['start', 'restart'])
def start(message):
    global url, count_of_ad, page_counter
    url = 'https://www.'
    count_of_ad = 0
    page_counter = 1

    buttons = types.InlineKeyboardMarkup(row_width=2)
    geo = types.InlineKeyboardButton(text='Georgia 🇬🇪', callback_data='geo')
    arm = types.InlineKeyboardButton(text='Armenia 🇦🇲', callback_data='arm')
    buttons.add(geo, arm)
    bot.send_message(message.chat.id, "Hey! I'm your assistant for searching apartments in Georgia and Armenia🏠"
                                      "\n\nFirst, choose a country 🛫", reply_markup=buttons)


# responds for all callbacks in the bot
@bot.callback_query_handler(func=lambda callback: callback.data)
def check_callback_data(callback):
    global url
    if callback.data == 'geo':
        url += 'myhome.ge/en/s/Apartment-for-rent-'
        geo_buttons = types.InlineKeyboardMarkup(row_width=2)
        tbilisi = types.InlineKeyboardButton(text='Tbilisi 🍷', callback_data='tbilisi')
        batumi = types.InlineKeyboardButton(text='Батуми 🏖️', callback_data='batumi')
        geo_buttons.add(tbilisi, batumi)
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              text='Press /restart to start over\n\nWhich georgian city?',
                              message_id=callback.message.id, reply_markup=geo_buttons)

    elif callback.data == 'arm':
        url += 'list.am/en/category/56?pfreq=1&po=1'
        arm_buttons = types.InlineKeyboardMarkup(row_width=2)
        yerevan = types.InlineKeyboardButton(text='Yerevan 🏛️', callback_data='yerevan')
        gyumri = types.InlineKeyboardButton(text='Gyumri ⛰️', callback_data='gyumri')
        arm_buttons.add(yerevan, gyumri)
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              text='Press /restart to start over\n\nWhich armenian city?',
                              message_id=callback.message.id, reply_markup=arm_buttons)

    elif callback.data in CITY_CODE:
        url += CITY_CODE.get(callback.data)
        msg = bot.edit_message_text(chat_id=callback.message.chat.id,
                                    text='Press /restart to start over\n\nHow many rooms do you need?',
                                    message_id=callback.message.id)
        bot.register_next_step_handler(msg, number_of_rooms)

    elif callback.data == 'more':
        if 'myhome.ge' in url:
            geo_ad(callback)
        elif 'list.am' in url:
            arm_ad(callback)


# if user made a typo when typing a value of cost or a number of rooms
@bot.message_handler(content_types=['text'])
def typo(message):
    typo_msg = bot.send_message(message.chat.id, 'Choose option higher')
    sleep(2)
    bot.delete_message(message.chat.id, typo_msg.message_id)
    bot.delete_message(message.chat.id, message.message_id)


# user enters a number of rooms
def number_of_rooms(message):
    global url
    numb_of_rooms = message.text
    # that block works if user enters any other message except digits from 1 to 4
    if numb_of_rooms not in ['1', '2', '3', '4']:
        room_amount = bot.send_message(message.chat.id, 'Enter the number of rooms from 1 to 4')
        sleep(2)
        bot.delete_message(message.chat.id, room_amount.message_id)  # delete incorrect message from user
        bot.delete_message(message.chat.id, message.message_id)  # delete notification about wrong input
        bot.register_next_step_handler(room_amount, number_of_rooms)
    else:
        msg_rooms = bot.send_message(message.chat.id, 'Enter the max cost per month:')
        if 'myhome.ge' in url:  # add to url params depend on country
            url += f'&RoomNums={numb_of_rooms}'
        elif 'list.am' in url:
            url += f'&_a4={numb_of_rooms}'
        bot.register_next_step_handler(msg_rooms, cost)


def cost(message):
    global url
    max_price = message.text
    if not max_price.isdigit():  # that block works if user enters any other messages except digits
        cost_amount = bot.send_message(message.chat.id, 'Enter a numeric value\ne.g.: 300')
        sleep(2)
        bot.delete_message(message.chat.id, cost_amount.message_id)  # delete incorrect message from user
        bot.delete_message(message.chat.id, message.message_id)  # delete notification about wrong input
        bot.register_next_step_handler(cost_amount, cost)
    else:
        output = bot.send_message(message.chat.id, "Looking for suitable options...🔎")
        if 'myhome.ge' in url:  # add to url params depend on country
            url += f'&FCurrencyID=1&FPriceTo={max_price}'
            geo_ad(output)
        elif 'list.am' in url:
            url += f'&price2={int(max_price) // dollar_to_dram()}&crc=0'
            arm_ad(output)


# searches the georgian website with a list of ad
def geo_parser():
    request = requests.get(url, headers=HEADERS)
    soup = b(request.text, 'html.parser')
    items = soup.find_all('a', class_='card-container')
    return items


# parse each georgian ad and finds the necessary parameters
def geo_ad(message):
    global count_of_ad, url, page_counter
    list_of_geo_ad = geo_parser()
    for i in list_of_geo_ad[count_of_ad:count_of_ad + 5]:
        # parse params from cards of ads
        price = i.find('b', class_='item-price-usd').text
        room = i.find('div', {'data-tooltip': "Number of rooms"}).text.strip('Room ')
        square = i.find('div', class_='item-size').text
        floor = i.find('div', class_='options-texts').text.strip('Floor ')
        # parse photo in each card of ads
        link = i.get('href')
        request = requests.get(link, headers=HEADERS)
        soup = b(request.text, 'html.parser')
        img = soup.find('div', class_='swiper-wrapper')
        img = img.findChildren('img')[0:5]
        img = [InputMediaPhoto(item['data-src']) for item in img]
        # text for output in the bot`s messages
        text = f"Price: {price}$ pcm\nRooms: {room}\nSquare: {square}\nFloor: {floor}\n<a href='{link}'>🔗 LINK 🔗</a>"

    # send an info and photos of ads to user:
        if count_of_ad == 0 and '&Page=' not in url:  # chat_id takes from message for first 5 ads
            chat_id = message.chat.id
        else:  # another 5 ads will take from callback
            chat_id = message.from_user.id

        try:
            bot.send_media_group(chat_id, media=img)
        except telebot.apihelper.ApiTelegramException:  # some photos of ads can`t parsed - for that's cases use this
            bot.send_message(chat_id, 'No photo 🚫\n\n' + text, parse_mode='html', disable_web_page_preview=True)
        else:
            bot.send_message(chat_id, text, parse_mode='html', disable_web_page_preview=True)

        # count_of_ad helps show by 5 ads
        try:
            if i == list_of_geo_ad[count_of_ad + 4]:
                count_of_ad += 5
                show_more_ad(message)
        except IndexError:  # that`s condition works if groups of 5 ads were showed from site`s page
            if i == list_of_geo_ad[count_of_ad]:
                continue
            else:
                count_of_ad = 0
                page_counter += 1
                url += f'&Page={page_counter}'
                show_more_ad(message)


# searches the armenian website with a list of ad
def arm_parser():
    request = requests.get(url, headers=HEADERS)
    soup = b(request.text, 'html.parser')
    items = soup.find('div', {'id': 'contentr'}).find_all('a')[1:]
    return items


# parse each armenian ad and finds the necessary parameters
def arm_ad(message):
    global count_of_ad, url, page_counter
    list_of_arm_ad = arm_parser()
    for i in list_of_arm_ad[count_of_ad:count_of_ad + 5]:
        # parse params from cards of ads
        price = i.find('div', class_='p').text.strip(' ֏ monthly').replace(',', '')
        info_flat = i.find('div', class_='at').text.split(',')
        rooms = info_flat[1].strip(' rm.')
        square = info_flat[2]
        floor = info_flat[3].strip(' floor')
        # parse photo in each card of ads
        link = 'https://www.list.am/' + i.get('href')
        request = requests.get(link, headers={'user-agent': 'Mozilla/5.0'})
        img = re.findall(r'img:\["//(.*)"]', request.text)
        img = [i.split('","//') for i in img]
        img = [InputMediaPhoto(item) for item in img[0][0:5]]
        # text for output in the bot`s messages
        text = f"Price: {round(int(int(price) * dollar_to_dram()), -1)}$ pcm\nRooms: {rooms}\nSquare:{square}\n" \
               f"Floor: {floor}\n<a href='{link}'>🔗 LINK 🔗</a>"

    # send an info and photos of ads to user:
        if count_of_ad == 0:  # chat_id takes from message for first 5 ads
            chat_id = message.chat.id
        else:  # another 5 ads will take from callback
            chat_id = message.from_user.id

        try:
            bot.send_media_group(chat_id, media=img)
        except telebot.apihelper.ApiTelegramException:  # some photos of ads can`t parsed - for that's cases use this
            bot.send_message(chat_id, 'No photo 🚫\n\n' + text, parse_mode='html',
                             disable_web_page_preview=True)
        else:
            bot.send_message(chat_id, text, parse_mode='html', disable_web_page_preview=True)

        # count_of_ad helps show by 5 ads
        try:
            if i == list_of_arm_ad[count_of_ad + 4]:
                count_of_ad += 5
                show_more_ad(message)
        except IndexError:  # that`s condition works if groups of 5 ads were showed from site`s page
            if i == list_of_arm_ad[count_of_ad]:
                continue
            else:
                count_of_ad = 0
                page_counter += 1
                url += f'&Page={page_counter}'
                show_more_ad(message)


# func for currency transfer from armenian dram to dollar (site can`t do that)
def dollar_to_dram():
    google_request = requests.get('https://www.google.com/search?q=1+dram+in+usd', headers=HEADERS)
    soup = b(google_request.text, 'html.parser')
    convert = soup.find('span', class_='DFlfde SwHCTb')
    return float(convert['data-value'])


# inline button for showing another 5 ads
@bot.message_handler(func=lambda m: True)
def show_more_ad(message):
    button = types.InlineKeyboardMarkup()
    more = types.InlineKeyboardButton(text='More', callback_data='more')
    button.add(more)
    text_more = "Press /restart to start over...\n\nor tap to show more ad 😉"
    try:
        bot.send_message(message.chat.id, text_more, reply_markup=button)
    except AttributeError:
        bot.send_message(message.from_user.id, text_more, reply_markup=button)


if __name__ == '__main__':
    bot.polling(none_stop=True)
