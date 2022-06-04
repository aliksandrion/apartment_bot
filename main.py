from settings import BOT_TOKEN, HEADERS, CITY_CODE

import telebot
from telebot import types
from telebot.types import InputMediaPhoto

from bs4 import BeautifulSoup as b
import requests
import re
from time import sleep

bot = telebot.TeleBot(BOT_TOKEN)
url = 'https://www.'
count_of_ad = 0  # number of messages sent
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
                                      "\n\nFirst, choose the country 🛫", reply_markup=buttons)


# responsible for all callbacks
@bot.callback_query_handler(func=lambda callback: callback.data)
def check_callback_data(callback):
    global url
    if callback.data == 'geo':
        url += 'myhome.ge/en/s/Apartment-for-rent-'
        geo_buttons = types.InlineKeyboardMarkup(row_width=2)
        tbilisi = types.InlineKeyboardButton(text='Tbilisi 🍷', callback_data='tbilisi')
        batumi = types.InlineKeyboardButton(text='Batumi 🏖️', callback_data='batumi')
        geo_buttons.add(tbilisi, batumi)
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              text='Press /restart to start over\n\nWhich Georgian city?',
                              message_id=callback.message.id, reply_markup=geo_buttons)

    elif callback.data == 'arm':
        url += 'list.am/en/category/56?pfreq=1&po=1'
        arm_buttons = types.InlineKeyboardMarkup(row_width=2)
        yerevan = types.InlineKeyboardButton(text='Yerevan 🏛️', callback_data='yerevan')
        gyumri = types.InlineKeyboardButton(text='Gyumri ⛰️', callback_data='gyumri')
        arm_buttons.add(yerevan, gyumri)
        bot.edit_message_text(chat_id=callback.message.chat.id,
                              text='Press /restart to start over\n\nWhich Armenian city?',
                              message_id=callback.message.id, reply_markup=arm_buttons)

    elif callback.data in CITY_CODE:
        url += CITY_CODE.get(callback.data)
        msg = bot.edit_message_text(chat_id=callback.message.chat.id,
                                    text='Press /restart to start over\n\nHow many rooms do you consider?',
                                    message_id=callback.message.id)
        bot.register_next_step_handler(msg, number_of_rooms)

    elif callback.data == 'more':
        if 'myhome.ge' in url:
            geo_ad(callback)
        elif 'list.am' in url:
            arm_ad(callback)


# if a user makes a typo when choosing the options
@bot.message_handler(content_types=['text'])
def typo(message):
    typo_msg = bot.send_message(message.chat.id, 'Choose option higher')
    sleep(2)
    bot.delete_message(message.chat.id, typo_msg.message_id)
    bot.delete_message(message.chat.id, message.message_id)


# a user enters a number of rooms
def number_of_rooms(message):
    global url
    numb_of_rooms = message.text
    # that block works if the user enters any other symbols except digits from 1 to 4
    if numb_of_rooms not in ['1', '2', '3', '4']:
        room_amount = bot.send_message(message.chat.id, 'Enter the number of rooms from 1 to 4')
        sleep(2)
        bot.delete_message(message.chat.id, room_amount.message_id)  # deletes incorrect messages
        bot.delete_message(message.chat.id, message.message_id)  # deletes notifications about wrong inputs
        bot.register_next_step_handler(room_amount, number_of_rooms)
    else:
        msg_rooms = bot.send_message(message.chat.id, 'Enter the max cost per month:')
        if 'myhome.ge' in url:  # adds to url the parameter depending on the country
            url += f'&RoomNums={numb_of_rooms}'
        elif 'list.am' in url:
            url += f'&_a4={numb_of_rooms}'
        bot.register_next_step_handler(msg_rooms, cost)


def cost(message):
    global url
    max_price = message.text
    if not max_price.isdigit():  # that block works if a user enters any other messages except digits
        cost_amount = bot.send_message(message.chat.id, 'Enter a numeric value\ne.g.: 300')
        sleep(2)
        bot.delete_message(message.chat.id, cost_amount.message_id)  # deletes incorrect messages
        bot.delete_message(message.chat.id, message.message_id)  # deletes notifications about wrong inputs
        bot.register_next_step_handler(cost_amount, cost)
    else:
        output = bot.send_message(message.chat.id, "Looking for suitable options...🔎")
        if 'myhome.ge' in url:  # adds to url the parameter depending on the country
            url += f'&FCurrencyID=1&FPriceTo={max_price}'
            geo_ad(output)
        elif 'list.am' in url:
            url += f'&price2={int(max_price) // dollar_to_dram()}&crc=0'
            arm_ad(output)


# searches the Georgian website with a list of ads
def geo_parser():
    request = requests.get(url, headers=HEADERS)
    soup = b(request.text, 'html.parser')
    items = soup.find_all('a', class_='card-container')
    return items


# parses the ads according to the parameters
def geo_ad(message):
    global count_of_ad, url, page_counter
    list_of_geo_ad = geo_parser()
    for i in list_of_geo_ad[count_of_ad:count_of_ad + 5]:
        # parses the parameters from the card in the list of ads
        price = i.find('b', class_='item-price-usd').text
        room = i.find('div', {'data-tooltip': "Number of rooms"}).text.strip('Room ')
        square = i.find('div', class_='item-size').text
        floor = i.find('div', class_='options-texts').text.strip('Floor ')
        # opens the ad and parses photos
        link = i.get('href')
        request = requests.get(link, headers=HEADERS)
        soup = b(request.text, 'html.parser')
        img = soup.find('div', class_='swiper-wrapper')
        img = img.findChildren('img')[0:5]
        img = [InputMediaPhoto(item['data-src']) for item in img]
        # text for output bot`s messages
        text = f"Price: {price}$ pcm\nRooms: {room}\nSquare: {square}\nFloor: {floor}\n<a href='{link}'>🔗 LINK 🔗</a>"

    # sends the info and photos from ads to the user:
        if count_of_ad == 0 and '&Page=' not in url:  # chat_id works for 5 first messages
            chat_id = message.chat.id
        else:  # each other 5 ads come from the callback
            chat_id = message.from_user.id

        try:
            bot.send_media_group(chat_id, media=img)
        except telebot.apihelper.ApiTelegramException:  # some photos from ads can`t be parsed - for that case use this:
            bot.send_message(chat_id, 'No photo 🚫\n\n' + text, parse_mode='html', disable_web_page_preview=True)
        else:
            bot.send_message(chat_id, text, parse_mode='html', disable_web_page_preview=True)

        # limits the number of messages sent per time
        try:
            if i == list_of_geo_ad[count_of_ad + 4]:
                count_of_ad += 5
                show_more_ad(message)
        except IndexError:  # if there are fewer than 5 ads in the end
            if i == list_of_geo_ad[count_of_ad]:
                continue
            else:
                count_of_ad = 0
                page_counter += 1
                url += f'&Page={page_counter}'
                show_more_ad(message)


# searches the Armenian website with a list of ads
def arm_parser():
    request = requests.get(url, headers=HEADERS)
    soup = b(request.text, 'html.parser')
    items = soup.find('div', {'id': 'contentr'}).find_all('a')[1:]
    return items


# parses the ads according to the parameters
def arm_ad(message):
    global count_of_ad, url, page_counter
    list_of_arm_ad = arm_parser()
    for i in list_of_arm_ad[count_of_ad:count_of_ad + 5]:
        # parses the parameters from the card in the list of ads
        price = i.find('div', class_='p').text.strip(' ֏ monthly').replace(',', '')
        info_flat = i.find('div', class_='at').text.split(',')
        rooms = info_flat[1].strip(' rm.')
        square = info_flat[2]
        floor = info_flat[3].strip(' floor')
        # opens the ad and parses photos
        link = 'https://www.list.am/' + i.get('href')
        request = requests.get(link, headers={'user-agent': 'Mozilla/5.0'})
        img = re.findall(r'img:\["//(.*)"]', request.text)
        img = [i.split('","//') for i in img]
        img = [InputMediaPhoto(item) for item in img[0][0:5]]
        # text for output bot`s messages
        text = f"Price: {round(int(int(price) * dollar_to_dram()), -1)}$ pcm\nRooms: {rooms}\nSquare:{square}\n" \
               f"Floor: {floor}\n<a href='{link}'>🔗 LINK 🔗</a>"

    # sends the info and photos from ads to the user:
        if count_of_ad == 0:  # chat_id takes from message for first 5 ads
            chat_id = message.chat.id
        else:  # each other 5 ads come from the callback
            chat_id = message.from_user.id

        try:
            bot.send_media_group(chat_id, media=img)
        except telebot.apihelper.ApiTelegramException:  # some photos from ads can`t be parsed - for that case use this:
            bot.send_message(chat_id, 'No photo 🚫\n\n' + text, parse_mode='html',
                             disable_web_page_preview=True)
        else:
            bot.send_message(chat_id, text, parse_mode='html', disable_web_page_preview=True)

        # limits the number of messages sent per time
        try:
            if i == list_of_arm_ad[count_of_ad + 4]:
                count_of_ad += 5
                show_more_ad(message)
        except IndexError:  # if there are fewer than 5 ads in the end
            if i == list_of_arm_ad[count_of_ad]:
                continue
            else:
                count_of_ad = 0
                page_counter += 1
                url += f'&Page={page_counter}'
                show_more_ad(message)


# currency transfers from the Armenian dram to the U.S. dollar (the website can not do that)
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
