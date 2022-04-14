import requests
API_link = 'https://api.telegram.org/bot5131345127:AAHyS8vPIt7e24EPBbajSt2EsPXtdeFjYsc'
updates = requests.get(API_link + '/getUpdates').json()

print(updates)



# from settings import bot_token

# for i in range(5):
#     requests.get(f'https://api.telegram.org/bot{bot_token}/sendMesage', params={'chat_id': 849467226, 'text': 'hey'})
