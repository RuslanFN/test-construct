import logging
file_handler = logging.FileHandler('logs/logs.txt', mode='a', encoding='utf-8')
stream_handler = logging.StreamHandler()
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        file_handler,
        stream_handler
    ])
