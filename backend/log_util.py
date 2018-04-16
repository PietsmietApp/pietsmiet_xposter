import time


def log(*args):
    level = "INFO"
    if len(args) == 1 and isinstance(args[0], str):
        text = args[0]
    elif len(args) == 2 and isinstance(args[1], str):
        level = args[0]
        text = args[1]
    else:
        level = "CRTICAL ERROR"
        text = "Not logging!! Parameter 1 should be a string and parameter 2 should be a string or omitted entirely"

    localtime = time.strftime('%d.%m. %H:%M:%S', time.localtime(time.time()))
    try:
        print(
            ("[" + localtime + "|" + level.upper() + "]: " + text).encode('unicode_escape').decode('latin-1', 'ignore'))
    except Exception as e:
        print("You can't even log a text, wow. Exception is " + format(e))
