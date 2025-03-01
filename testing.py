import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import aiofiles  # For async file I/O
from collections import defaultdict, deque
import os
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import logging


# Mock external functions (replace with actual implementations)
def track_spot_price(index): return 100.0  # Example


def track_option_data(token): return 10000  # Example (returns price * 100)


def track_premium_by_token(token): return 10000  # Example (returns price * 100)


def get_ini_details(file_path): return {
    'strat1': {'start_time': '09:15:00', 'end_time': '15:30:00', 'entry_gap': '15'}}  # Example


# Setup logging for performance monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContractProcessor:
    _cache = None

    def __init__(self, contract_file):
        self.contract_file = contract_file

    async def process(self):
        """Process contract file efficiently with caching."""
        if ContractProcessor._cache is None:
            dtypes = {
                'FinInstrmId': 'int64', 'UndrlygFinInstrmId': 'int64', 'FinInstrmNm': 'category',
                'TckrSymb': 'category', 'XpryDt': 'float64', 'StrkPric': 'float64', 'OptnTp': 'category',
                'StockNm': 'category'
            }
            df = pd.read_csv(self.contract_file, usecols=dtypes.keys(), dtype=dtypes)
            df = df[df['OptnTp'].isin(['CE', 'PE'])]
            base_date = pd.Timestamp('1980-01-01')
            df['XpryDt'] = (base_date + pd.to_timedelta(df['XpryDt'] / (60 * 60 * 24), unit='D')).dt.strftime(
                '%d-%b-%y')
            ContractProcessor._cache = df
        return ContractProcessor._cache


class StopLossTarget:
    def __init__(self, contract_df):
        self.contract_df = contract_df
        self.trades = deque()  # Faster than list for popping
        self.pnl_data = []  # List instead of DataFrame for speed
        self.expiry_date = '23-Jan-25'
        self.write_buffer = []  # Buffer for batched file writes

    async def append_sl_tgt(self, trade_book):
        """Append trade asynchronously."""
        await self._rule_of_strategy(trade_book)

    async def track_live_price(self, token):
        return int(track_option_data(int(token))) / 100

    async def track_curr_time(self):
        return datetime.now().strftime('%H:%M:%S')

    async def _rule_of_strategy(self, trade_book):
        """Optimized trading rule logic."""
        symbol = trade_book.get('symbol', 'NIFTY')
        strike_selection = int(trade_book.get('strike_selection', '0'))
        ce_token, pe_token, _, _ = await self._strike_selection(strike_selection, symbol)
        ce_price = await self.track_live_price(ce_token)
        pe_price = await self.track_live_price(pe_token)

        strategy_id = trade_book['strategy_id']
        trade_number = trade_book['trade_number']
        sl_pct = float(trade_book.get('sl_pct_or_point', '2'))
        tgt_pct = float(trade_book.get('tgt_pct_or_point', '2'))
        exit_time = trade_book['exit_time']

        ce_sl = ce_price * (1 + sl_pct / 100)
        pe_sl = pe_price * (1 + sl_pct / 100)
        ce_tgt = ce_price * (1 - tgt_pct / 100)
        pe_tgt = pe_price * (1 - tgt_pct / 100)

        ce_dict = {'token': ce_token, 'entry_price': ce_price, 'stoploss': ce_sl, 'target': ce_tgt,
                   'exit_time': exit_time, 'strategy_id': strategy_id, 'trade_number': trade_number, 'type': 'Normal'}
        pe_dict = {'token': pe_token, 'entry_price': pe_price, 'stoploss': pe_sl, 'target': pe_tgt,
                   'exit_time': exit_time, 'strategy_id': strategy_id, 'trade_number': trade_number, 'type': 'Normal'}

        self.pnl_data.extend([
            {'Trade_Strategy': strategy_id, 'trade_number': trade_number, 'token_number': ce_token, 'option': 'ce',
             'entry_price': ce_price, 'curr_price_or_price': None},
            {'Trade_Strategy': strategy_id, 'trade_number': trade_number, 'token_number': pe_token, 'option': 'pe',
             'entry_price': pe_price, 'curr_price_or_price': None}
        ])
        self.trades.extend([ce_dict, pe_dict])

    async def _strike_selection(self, strike_selection, symbol):
        if strike_selection == 0:
            curr_price = float(track_spot_price('Nifty 50' if symbol.lower() == 'nifty' else symbol))
            strike_price = int(round(curr_price / 50) * 50)
            ce_strike = strike_price + 50
            pe_strike = strike_price - 50
            ce_token = await self._get_token_number(ce_strike, 'CE')
            pe_token = await self._get_token_number(pe_strike, 'PE')
            return str(ce_token), str(pe_token), ce_strike, pe_strike
        # Add other strike_selection logic if needed

    async def _get_token_number(self, strike_price, option):
        df = self.contract_df
        token = df[(df['XpryDt'] == self.expiry_date) & (df['TckrSymb'] == 'NIFTY') &
                   (df['StrkPric'] == strike_price) & (df['OptnTp'] == option)]['FinInstrmId'].iloc[0]
        return token

    async def track_live_trade(self):
        """Async live trade tracking with minimal latency."""
        while self.trades:
            tasks = [self._process_trade(trade) for trade in self.trades]
            results = await asyncio.gather(*tasks)
            self.trades = deque(trade for trade, keep in zip(self.trades, results) if keep)
            if len(self.write_buffer) > 100:  # Batch write every 100 trades
                await self._flush_write_buffer()
            await asyncio.sleep(0.001)  # Minimal polling delay

    async def _process_trade(self, trade):
        curr_price = await self.track_live_price(trade['token'])
        curr_time = await self.track_curr_time()
        for entry in self.pnl_data:
            if entry['trade_number'] == trade['trade_number'] and entry['token_number'] == trade['token']:
                entry['curr_price_or_price'] = curr_price
                break

        if curr_price >= trade['stoploss']:
            trade['Exit Price'] = curr_price
            trade['Trade Exit'] = curr_time
            trade['Type'] = 'Stoploss'
            self.write_buffer.append(trade)
            return False
        elif curr_price <= trade['target']:
            trade['Exit Price'] = curr_price
            trade['Trade Exit'] = curr_time
            trade['Type'] = 'Target'
            self.write_buffer.append(trade)
            return False
        elif curr_time >= trade['exit_time']:
            trade['Exit Price'] = curr_price
            trade['Trade Exit'] = curr_time
            trade['Type'] = 'Time'
            self.write_buffer.append(trade)
            return False
        return True

    async def _flush_write_buffer(self):
        """Batch write to CSV asynchronously."""
        if not self.write_buffer:
            return
        file_path = f'{datetime.now().strftime("%Y-%m-%d")}_data.csv'
        async with aiofiles.open(file_path, 'a') as f:
            if not os.path.exists(file_path):
                await f.write(','.join(self.write_buffer[0].keys()) + '\n')
            for trade in self.write_buffer:
                await f.write(','.join(str(trade.get(k, '')) for k in trade) + '\n')
        self.write_buffer.clear()


class StopLossTargetOptionEntryTrack:
    def __init__(self, contract_df):
        self.contract_df = contract_df
        self.trade_queue = deque()
        self.trades_by_time = defaultdict(list)
        self.sl_tg_obj = StopLossTarget(contract_df)

    def _append_in_queue(self, key, trade_book):
        trade_book['strategy_id'] = key
        self.trade_queue.append(trade_book)

    async def mapping_the_trade(self):
        """Map trades to time efficiently."""
        for trade in self.trade_queue:
            start_time = trade['start_time']
            end_time = trade['end_time']
            gap_minutes = int(trade['entry_gap'].rstrip('Min'))
            times = await self._generate_trade_times(start_time, end_time, gap_minutes)
            trade_number = len(self.trades_by_time) + 1
            trade['trade_number'] = trade_number
            for t in times:
                self.trades_by_time[t].append(dict(trade))  # Shallow copy

    async def _generate_trade_times(self, start, end, gap_minutes):
        start_dt = datetime.strptime(start, '%H:%M:%S')
        end_dt = datetime.strptime(end, '%H:%M:%S')
        times = []
        curr = start_dt
        while curr <= end_dt:
            times.append(curr.strftime('%H:%M:%S'))
            curr += timedelta(minutes=gap_minutes)
        return times

    async def manage_run(self):
        """Run trade tracking and live monitoring concurrently."""
        await asyncio.gather(self._track_entries(), self.sl_tg_obj.track_live_trade())

    async def _track_entries(self):
        sorted_times = sorted(self.trades_by_time.keys())
        while sorted_times:
            curr_time = await self.sl_tg_obj.track_curr_time()
            if curr_time in self.trades_by_time:
                for trade in self.trades_by_time[curr_time]:
                    await self.sl_tg_obj.append_sl_tgt(trade)
                del self.trades_by_time[curr_time]
                sorted_times = [t for t in sorted_times if t > curr_time]
            await asyncio.sleep(0.001)


class TradeTake:
    CONTRACT_FILE_PATH = r"C:\Users\Administrator\Desktop\contract_file_update\NSE_FO_contract_24012025.csv"

    def __init__(self, trade_setting_file_path):
        self.config_file = trade_setting_file_path
        self.processor = ContractProcessor(self.CONTRACT_FILE_PATH)
        self.config_dict = self._load_config()

    @lru_cache(maxsize=1)
    def _load_config(self):
        return get_ini_details(self.config_file)

    async def load_strategy(self):
        contract_df = await self.processor.process()
        tracker = StopLossTargetOptionEntryTrack(contract_df)
        with ThreadPoolExecutor() as executor:
            executor.map(lambda kv: tracker._append_in_queue(kv[0], kv[1]), self.config_dict.items())
        await tracker.mapping_the_trade()
        await tracker.manage_run()


async def main():
    trade = TradeTake('config.ini')
    await trade.load_strategy()


if __name__ == '__main__':
    asyncio.run(main())