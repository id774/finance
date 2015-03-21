class TechnicalIndicators():

    def get_macd(self, ema_12, ema_26):
        return (float(ema_12) - float(ema_26))

    def get_macd_ema(self, stock_prices_array, idx, period, previous_macd_ema):
        smoothing_constant = 2.0 / (period + 1)
        ma_array = []
        if (idx == (period - 1)):
            start_ma_array = idx - (period - 1)
            end_ma_array = start_ma_array + period
            ma_array = stock_prices_array[start_ma_array:end_ma_array]
            ma = (sum(x.macd_12_26 for x in ma_array) / period)
            return ma
        elif (idx > (period - 1) and previous_macd_ema != None):
            current_macd = stock_prices_array[idx].macd_12_26
            ema = ((smoothing_constant * (current_macd - previous_macd_ema)) +
                   previous_macd_ema)
            return ema
        else:
            return 0

    def get_macd_histogram(self, macd, ema_9):
        return (float(macd) - float(ema_9))


# This is the StockPrice object in the method above, for reference
class StockPrice:
    id = 0
    symbol = ""
    volume = 0
    opening_price = 0
    closing_price = 0
    adj_closing_price = 0
    low_price = 0
    high_price = 0
    macd_12_26 = 0
