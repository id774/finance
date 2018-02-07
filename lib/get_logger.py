from datetime import datetime, timedelta, timezone

class Logger():

    def info(self, message):
        JST = timezone(timedelta(hours=+9), 'JST')
        now = datetime.now(JST).strftime("%Y-%m-%dT%H:%M:%S.%s+09:00")
        print(now, "[INFO]", message)

    def warn(self, message):
        JST = timezone(timedelta(hours=+9), 'JST')
        now = datetime.now(JST).strftime("%Y-%m-%dT%H:%M:%S.%s+09:00")
        print(now, "[WARN]", message)

    def error(self, message):
        JST = timezone(timedelta(hours=+9), 'JST')
        now = datetime.now(JST).strftime("%Y-%m-%dT%H:%M:%S.%s+09:00")
        print(now, "[ERROR]", message)
