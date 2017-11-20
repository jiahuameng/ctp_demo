# coding=utf-8
from threading import Thread, Condition
from Queue import Queue
import time
from ctp import ApiStruct
from trade_api import MyTraderApi
from md_api import MyMdApi


class TradeAgent(object):
    def __init__(self, td_front, broker_id, user_id, password):
        self.request_id = 1
        self.broker_id = broker_id
        self.user_id = user_id
        self.password = password
        self.callback = None

        self.qry_cond = Condition()
        self.rsp_qry_queue = Queue()
        self.cond = Condition()
        self.data_queue = Queue()
        self.qry_results = {}

        self.instrument_dict = {}
        self.position_dict = None
        self.trading_account = None
        self.trade_dict = None
        self.order_dict = None

        self.session_id = None
        self.front_id = None
        self.max_order_ref = None

        self.api = MyTraderApi(broker_id, user_id, password, self.rsp_qry_queue, self.data_queue)
        thread = Thread(target=self.init, args=(td_front,))
        thread.start()
        thread_rsp_qry = Thread(target=self.process_rsp_qry)
        thread_rsp_qry.start()
        thread_data = Thread(target=self.process_data)
        thread_data.start()

    def init(self, td_front):
        self.api.RegisterFront(td_front)
        self.api.SubscribePrivateTopic(2)
        self.api.SubscribePublicTopic(2)
        self.api.Init()
        self.api.Join()

    def process_rsp_qry(self):
        while 1:
            msg = self.rsp_qry_queue.get()
            if not isinstance(msg, tuple):
                continue
            request_id, result, is_last = msg
            self.qry_cond.acquire()
            if request_id not in self.qry_results:
                self.qry_results[request_id] = {
                    'results': [],
                    'status': False,
                }
            if result:
                self.qry_results[request_id]['results'].append(result)
            if is_last:
                self.qry_results[request_id]['status'] = True
                self.qry_cond.notifyAll()
            self.qry_cond.release()

    def process_data(self):
        while 1:
            data = self.data_queue.get()
            if isinstance(data, ApiStruct.Order) and data.ExchangeID and data.TraderID and data.OrderLocalID:
                self.order_dict[(data.ExchangeID, data.TraderID, data.OrderLocalID)] = data
            elif isinstance(data, ApiStruct.Trade) and data.ExchangeID and data.TradeID:
                self.trade_dict[(data.ExchangeID, data.TradeID)] = data
            if self.callback:
                self.callback(data)

    def ready(self, timeout=3):
        request_time = time.time()
        while not self.api.ready and time.time() < request_time + timeout:
            time.sleep(1)
        if self.api.ready and self.api.user_login:
            self.front_id = self.api.user_login.FrontID
            self.session_id = self.api.user_login.SessionID
            self.max_order_ref = int(self.api.user_login.MaxOrderRef)
            print 'trade agent initial succeed'
            return True
        else:
            print 'trade agent inital failed'
            return False

    def load_instruments(self, instrument_ids):
        for instrument_id in instrument_ids:
            self.query_instrument(instrument_id)
            time.sleep(1.1)

    def _get_results(self, timeout, request_id):
        self.qry_cond.acquire()
        self.qry_results[request_id] = {
            'results': [],
            'status': False,
        }
        request_time = time.time()
        while not self.qry_results[request_id]['status'] and request_time + timeout > time.time():
            self.qry_cond.wait(0.1)
        self.qry_cond.release()
        ret = self.qry_results.pop(request_id, {})
        if not ret.get('status'):
            return None
        return ret.get('results')

    def query_settlement_info(self, timeout=3):
        req = ApiStruct.QrySettlementInfo(BrokerID=self.broker_id, InvestorID=self.user_id)
        self.request_id += 1
        request_id = self.request_id
        ret = self.api.ReqQrySettlementInfo(req, request_id)
        if ret != 0:
            print 'query settlement info failed', ret
            return None
        results = self._get_results(timeout, request_id)
        return results

    def query_settlement_info_confirm(self, timeout=3):
        req = ApiStruct.QrySettlementInfoConfirm(BrokerID=self.broker_id, InvestorID=self.user_id)
        self.request_id += 1
        request_id = self.request_id
        ret = self.api.ReqQrySettlementInfoConfirm(req, request_id)
        if ret != 0:
            print 'query settlement info confirm failed', ret
            return None
        results = self._get_results(timeout, request_id)
        if results:
            print results[0]
            print 'settlement info already confirmed.'
        return results

    def query_order(self, timeout=3):
        req = ApiStruct.QryOrder(BrokerID=self.broker_id, InvestorID=self.user_id)
        self.request_id += 1
        request_id = self.request_id
        ret = self.api.ReqQryOrder(req, request_id)
        if ret != 0:
            print 'query order failed', ret
            return None
        results = self._get_results(timeout, request_id)
        if results is None:
            return None
        self.order_dict = {(result.ExchangeID, result.TraderID, result.OrderLocalID): result for result in results}
        return self.order_dict

    def query_trade(self, timeout=3):
        req = ApiStruct.QryTrade(BrokerID=self.broker_id, InvestorID=self.user_id)
        self.request_id += 1
        request_id = self.request_id
        ret = self.api.ReqQryTrade(req, request_id)
        if ret != 0:
            print 'query trade failed', ret
            return None
        results = self._get_results(timeout, request_id)
        if results is None:
            return None
        self.trade_dict = {(result.ExchangeID, result.TradeID): result for result in results}
        return self.trade_dict

    def query_position(self, instrument_id=None, timeout=3):
        req = ApiStruct.QryInvestorPosition(BrokerID=self.broker_id, InvestorID=self.user_id)
        if instrument_id:
            req.InstrumentID = instrument_id
        self.request_id += 1
        request_id = self.request_id
        ret = self.api.ReqQryInvestorPosition(req, request_id)
        if ret != 0:
            print 'query position failed', ret
            return None
        results = self._get_results(timeout, request_id)
        if results is None:
            return None
        self.position_dict = {}
        for result in results:
            if result.InstrumentID is None or result.PosiDirection is None or result.Position is None:
                continue
            if (result.InstrumentID, result.PosiDirection) not in self.position_dict:
                self.position_dict[(result.InstrumentID, result.PosiDirection)] = []
            self.position_dict[(result.InstrumentID, result.PosiDirection)].append(result)
        return self.position_dict

    def query_position_detail(self, timeout=3):
        req = ApiStruct.QryInvestorPositionDetail(BrokerID=self.broker_id, InvestorID=self.user_id)
        self.request_id += 1
        request_id = self.request_id
        ret = self.api.ReqQryInvestorPositionDetail(req, request_id)
        if ret != 0:
            print 'query position detail failed', ret
            return None
        results = self._get_results(timeout, request_id)
        return results

    def query_trading_account(self, timeout=3):
        req = ApiStruct.QryTradingAccount(BrokerID=self.broker_id, InvestorID=self.user_id)
        self.request_id += 1
        request_id = self.request_id
        ret = self.api.ReqQryTradingAccount(req, request_id)
        if ret != 0:
            print 'query trading account failed', ret
            return None
        results = self._get_results(timeout, request_id)
        if not results:
            return None
        self.trading_account = results[0]
        return self.trading_account

    def query_instrument(self, instrument_id, timeout=3):
        req = ApiStruct.QryInstrument(InstrumentID=instrument_id)
        self.request_id += 1
        request_id = self.request_id
        ret = self.api.ReqQryInstrument(req, request_id)
        if ret != 0:
            print 'query instrument {} failed'.format(instrument_id), ret
            return None
        results = self._get_results(timeout, request_id)
        if not results:
            return None
        self.instrument_dict[instrument_id] = results[0]
        print results[0]
        return results[0]

    def query_depth_market_data(self, instrument_id, timeout=3):
        req = ApiStruct.QryDepthMarketData(InstrumentID=instrument_id)
        self.request_id += 1
        request_id = self.request_id
        ret = self.api.ReqQryDepthMarketData(req, request_id)
        if ret != 0:
            print 'query {} depth market data failed'.format(instrument_id), ret
            return None
        results = self._get_results(timeout, request_id)
        if not results:
            return None
        return results[0]

    def settlement_info_confirm(self, timeout=3):
        req = ApiStruct.SettlementInfoConfirm(BrokerID=self.broker_id, InvestorID=self.user_id)
        self.request_id += 1
        request_id = self.request_id
        ret = self.api.ReqSettlementInfoConfirm(req, request_id)
        if ret != 0:
            print 'settlement info confirm failed', ret
            return False
        results = self._get_results(timeout, request_id)
        if results is None:
            return False
        print results[0]
        print 'settlement info confirm succeed.'
        return True

    def _make_order(self, instrument_id, direction, volume):
        self.max_order_ref += 1
        return ApiStruct.InputOrder(BrokerID=self.broker_id, InvestorID=self.user_id, InstrumentID=instrument_id,
                                     OrderRef=str(self.max_order_ref), Direction=direction, CombOffsetFlag=ApiStruct.OF_Open,
                                     CombHedgeFlag=ApiStruct.HF_Speculation, VolumeTotalOriginal=volume,
                                     ContingentCondition=ApiStruct.CC_Immediately, VolumeCondition=ApiStruct.VC_AV,
                                     MinVolume=1, ForceCloseReason=ApiStruct.FCC_NotForceClose,
                                     IsAutoSuspend=0, UserForceClose=0)

    def _set_price(self, order, direction, limit_price, time_condition, market_data):
        price = None
        if limit_price == 0:
            if market_data:
                if direction == ApiStruct.D_Buy:
                    # 取对手价
                    price = market_data.AskPrice1
                else:
                    # 取对手价
                    price = market_data.BidPrice1
                time_condition = ApiStruct.TC_IOC
        else:
            price = limit_price

        if price is None:
            return False

        order.LimitPrice = price
        order.TimeCondition = time_condition
        return True

    def buy(self, instrument_id, volume, limit_price=0, time_condition=ApiStruct.TC_GFD, market_data=None):
        direction = ApiStruct.D_Buy
        order = self._make_order(instrument_id, direction, volume)
        order.OrderPriceType = ApiStruct.OPT_LimitPrice
        if not self._set_price(order, direction, limit_price, time_condition, market_data):
            return None

        self.request_id += 1
        self.api.ReqOrderInsert(order, self.request_id)
        return order

    def sell(self, instrument_id, volume, limit_price=0, time_condition=ApiStruct.TC_GFD, market_data=None):
        direction = ApiStruct.D_Sell
        order = self._make_order(instrument_id, direction, volume)
        order.CombOffsetFlag = ApiStruct.OF_Close
        order.OrderPriceType = ApiStruct.OPT_LimitPrice
        if not self._set_price(order, direction, limit_price, time_condition, market_data):
            return None

        self.request_id += 1
        self.api.ReqOrderInsert(order, self.request_id)
        return order

    def sell_today(self, instrument_id, volume, limit_price=0, time_condition=ApiStruct.TC_GFD, market_data=None):
        direction = ApiStruct.D_Sell
        order = self._make_order(instrument_id, direction, volume)
        order.CombOffsetFlag = ApiStruct.OF_CloseToday
        order.OrderPriceType = ApiStruct.OPT_LimitPrice
        if not self._set_price(order, direction, limit_price, time_condition, market_data):
            return None

        self.request_id += 1
        self.api.ReqOrderInsert(order, self.request_id)
        return order

    def short(self, instrument_id, volume, limit_price=0, time_condition=ApiStruct.TC_GFD, market_data=None):
        direction = ApiStruct.D_Sell
        order = self._make_order(instrument_id, direction, volume)
        order.OrderPriceType = ApiStruct.OPT_LimitPrice
        if not self._set_price(order, direction, limit_price, time_condition, market_data):
            return None

        self.request_id += 1
        self.api.ReqOrderInsert(order, self.request_id)
        return order

    def cover(self, instrument_id, volume, limit_price=0, time_condition=ApiStruct.TC_GFD, market_data=None):
        direction = ApiStruct.D_Buy
        order = self._make_order(instrument_id, direction, volume)
        order.CombOffsetFlag = ApiStruct.OF_Close
        order.OrderPriceType = ApiStruct.OPT_LimitPrice
        if not self._set_price(order, direction, limit_price, time_condition, market_data):
            return None

        self.request_id += 1
        self.api.ReqOrderInsert(order, self.request_id)
        return order

    def cover_today(self, instrument_id, volume, limit_price=0, time_condition=ApiStruct.TC_GFD, market_data=None):
        direction = ApiStruct.D_Buy
        order = self._make_order(instrument_id, direction, volume)
        order.CombOffsetFlag = ApiStruct.OF_CloseToday
        order.OrderPriceType = ApiStruct.OPT_LimitPrice
        if not self._set_price(order, direction, limit_price, time_condition, market_data):
            return None

        self.request_id += 1
        self.api.ReqOrderInsert(order, self.request_id)
        return order

    def open(self, instrument_id, posi_direction, volume, limit_price=0, time_condition=ApiStruct.TC_GFD, market_data=None):
        if posi_direction == ApiStruct.PD_Long:
            return self.buy(instrument_id, volume, limit_price, time_condition, market_data)
        elif posi_direction == ApiStruct.PD_Short:
            return self.short(instrument_id, volume, limit_price, time_condition, market_data)

    def close(self, instrument_id, posi_direction, volume, limit_price=0, time_condition=ApiStruct.TC_GFD, market_data=None):
        if posi_direction == ApiStruct.PD_Long:
            return self.sell(instrument_id, volume, limit_price, time_condition, market_data)
        elif posi_direction == ApiStruct.PD_Short:
            return self.cover(instrument_id, volume, limit_price, time_condition, market_data)

    def close_today(self, instrument_id, posi_direction, volume, limit_price=0, time_condition=ApiStruct.TC_GFD, market_data=None):
        if posi_direction == ApiStruct.PD_Long:
            return self.sell_today(instrument_id, volume, limit_price, time_condition, market_data)
        elif posi_direction == ApiStruct.PD_Short:
            return self.cover_today(instrument_id, volume, limit_price, time_condition, market_data)

    def refer(self, instrument_id, exchange_id, order_sys_id):
        order_action = ApiStruct.InputOrderAction(BrokerID=self.broker_id, InvestorID=self.user_id, InstrumentID=instrument_id,
                                                  ActionFlag=ApiStruct.AF_Delete, ExchangeID=exchange_id, OrderSysID=order_sys_id)
        self.request_id += 1
        return self.api.ReqOrderAction(order_action, self.request_id) == 0

    def refer_local(self, instrument_id, order_ref):
        order_action = ApiStruct.InputOrderAction(BrokerID=self.broker_id, InvestorID=self.user_id, InstrumentID=instrument_id,
                                                  ActionFlag=ApiStruct.AF_Delete, FrontID=self.front_id, SessionID=self.session_id,
                                                  OrderRef=order_ref)
        self.request_id += 1
        return self.api.ReqOrderAction(order_action, self.request_id) == 0


class MdAgent(object):
    def __init__(self, md_front, broker_id, user_id, password):
        self.request_id = 0
        self.broker_id = broker_id
        self.user_id = user_id
        self.password = password

        self.listener_list = []

        self.data_queue = Queue()
        self.market_data_dict = {}
        self.api = MyMdApi(broker_id, user_id, password, self.data_queue)
        thread = Thread(target=self.init, args=(md_front,))
        thread.start()
        thread_data = Thread(target=self.process_data)
        thread_data.start()

    def init(self, md_front):
        self.api.RegisterFront(md_front)
        self.api.Init()
        self.api.Join()

    def process_data(self):
        while 1:
            market_data = self.data_queue.get()
            instrument_id = market_data.InstrumentID
            self.market_data_dict[instrument_id] = market_data
            if self.listener_list:
                for listener in self.listener_list:
                    listener(market_data)

    def ready(self, timeout=3):
        request_time = time.time()
        while not self.api.ready and time.time() < request_time + timeout:
            time.sleep(1)
        if self.api.ready:
            print 'market data agent initialized.'
            return True
        else:
            print 'market data agent initial faield'
            return False

    def subscribe_market_data(self, instrument_ids):
        self.api.SubscribeMarketData(instrument_ids)

    def add_listener(self, listener):
        self.listener_list.append(listener)

    def del_listener(self, listener):
        self.listener_list.remove(listener)

if __name__ == '__main__':
    broker_id = '9999'
    # user_id = '081458'
    # password = '8210213146'
    user_id = '081471'
    password = '135246'
    instrument_ids = ['ag1702']
    md_front = 'tcp://180.168.146.187:10010'
    td_front = 'tcp://180.168.146.187:10001'

    # agent = TradeAgent(td_front, broker_id, user_id, password)
    # agent.ready()
    # time.sleep(2)
    agent = MdAgent(md_front, broker_id, user_id, password)
    agent.ready()

#
#     if not agent.query_settlement_info_confirm():
#         agent.settlement_info_confirm()

    #
    # agent.load_instruments(instrument_ids)
    # print agent.instrument_dict
    #
    # agent.sell('ag1702', 2)
    # agent.short('ag1702', 4)
    #
    # time.sleep(2)
    # print agent.query_position('ag1702')

    # print trd_opr.query_instrument('ag1701')
    # print trd_opr.query_depth_market_data('a1701')
    # trd_opr.order_open('a1701', ApiStruct.D_Buy, 0, 2)
    # trd_opr.order_close('ag1702', ApiStruct.D_Sell, 2)

    # print trd_opr.query_settlement_info()
    # time.sleep(1)
    # print trd_opr.query_settlement_info_confirm()
    # time.sleep(1)
    # # # trd_opr.settlement_info_confirm()
    # # time.sleep(1)
    # # trd_opr.query_position()
    # # time.sleep(1)
    # print trd_opr.query_position_detail()
    # time.sleep(1)
    # # # trd_opr.new_order('ag1702', ApiStruct.D_Buy, 4058, 2)
    # # time.sleep(1)
    # # time.sleep(2)
    # # trd_opr.query_trading_account()