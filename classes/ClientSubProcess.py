import ClientObject
import argparse
import asyncio


#{'api_id': 24209092, 'api_hash': '822ed15f01ee35ae8a50d750d3e8451d', 'session_name': 'session_name'}
def get_args():
    parser = argparse.ArgumentParser(description='Telegram bot')
    parser.add_argument('-t', '--token', type=str, help='Bot token')
    parser.add_argument('-a', '--api_id', type=int, help='Api id')
    parser.add_argument('-ah', '--api_hash', type=str, help='Api hash')
    parser.add_argument('-s', '--session_name', type=str, help='Session name')
    parser.add_argument('-pi', '--proxyip', type=str, help='Proxy ip')
    parser.add_argument('-pp', '--proxyport', type=str, help='Proxy port')
    parser.add_argument('-pt', '--proxytype', type=str, help='proxy type')
    parser.add_argument('-pl', '--proxylogin', type=str, help='proxy login')
    parser.add_argument('-ppass', '--proxypassword', type=str, help='proxy password')
    parser.add_argument('-m', '--message_text', type=str, help='Message text')
    parser.add_argument('-time', '--time_to_answer', type=str, help='Time in seconds')
    return parser.parse_args()

loop = asyncio.get_event_loop()
arg = get_args()
proxy = None
if arg.proxyip:
    if arg.proxylogin == ".":
        proxy = {'proxy_ip': arg.proxyip,
                 'proxy_port': arg.proxyport,
                 'proxy_type': arg.proxytype}
    else:
        proxy = {'proxy_ip': arg.proxyip,
                     'proxy_port': arg.proxyport,
                     'proxy_type': arg.proxytype,
                     'proxy_login': arg.proxylogin,
                     'proxy_password': arg.proxypassword}
bot = ClientObject.ClientObject(arg.api_id,
                                    arg.api_hash,
                                    arg.session_name,
                                    proxy,
                                    arg.message_text,
                                arg.time_to_answer)
loop.create_task(bot.start())
loop.run_forever()