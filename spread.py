# coding=utf-8
import sys
import traceback
import uuid
from operator import attrgetter

import datetime
import ConfigParser
from threading import Thread

from ctp import ApiStruct

import wx
import wx.dataview as dv
import time
from agent import TradeAgent, MdAgent
import common


cp = ConfigParser.SafeConfigParser()
cp.read('ctp.conf')

default_md_front = cp.get('user', 'md_front')  
default_td_front = cp.get('user', 'td_front')  
default_broker_id = cp.get('user', 'broker_id')  
default_user_id = cp.get('user', 'user_id')  
default_password = cp.get('user', 'password')  
default_instrument_ids = cp.get('user', 'instrument_ids') 

volume_threshold = 5  # 最小成交数量
order_life_time = 4  # 合约等待撤单时间(4个行情时间 = 2s)

direction_list = [(ApiStruct.D_Buy, u'买入'), (ApiStruct.D_Sell, u'卖出')]
offset_list = [(ApiStruct.OF_Open, u'开仓'), (ApiStruct.OF_CloseToday, u'平今'), (ApiStruct.OF_Close, u'平仓')]
direction_dict = {key: value for key, value in direction_list}
offset_dict = {key: value for key, value in offset_list}


class LoginDialog(wx.Dialog):
    def __init__(self, parent, id, title, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.DEFAULT_DIALOG_STYLE):
        pre = wx.PreDialog()
        pre.SetExtraStyle(wx.DIALOG_EX_CONTEXTHELP)
        pre.Create(parent, id, title, pos, size, style)

        self.PostCreate(pre)

        sizer = wx.BoxSizer(wx.VERTICAL)

        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, u'交易地址:', size=(80, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.t_td_front = wx.TextCtrl(self, -1, default_td_front, size=(200, -1))
        box.Add(self.t_td_front, 1, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, u'行情地址:', size=(80, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.t_md_front = wx.TextCtrl(self, -1, default_md_front, size=(200, -1))
        box.Add(self.t_md_front, 1, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, u'经纪公司:', size=(80, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.t_broker_id = wx.TextCtrl(self, -1, default_broker_id, size=(200, -1))
        box.Add(self.t_broker_id, 1, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, u'用户名:', size=(80, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.t_user_id = wx.TextCtrl(self, -1, default_user_id, size=(200, -1))
        box.Add(self.t_user_id, 1, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, u'密码:', size=(80, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.t_password = wx.TextCtrl(self, -1, default_password, size=(200, -1), style=wx.TE_PASSWORD)
        box.Add(self.t_password, 1, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, u'合约:', size=(80, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.t_instrument_ids = wx.TextCtrl(self, -1, default_instrument_ids, size=(200, 80),
                                            style=wx.TE_MULTILINE|wx.TE_PROCESS_ENTER)
        box.Add(self.t_instrument_ids, 1, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        line = wx.StaticLine(self, -1, size=(20, -1), style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT | wx.TOP, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)

        self.b_save = btn = wx.Button(self, -1, U'保存')
        box.Add(btn, 0, wx.ALIGN_CENTRE | wx.ALL, 5)

        self.b_login = btn = wx.Button(self, -1, U'登录')
        btn.SetDefault()
        box.Add(btn, 0, wx.ALIGN_CENTRE | wx.ALL, 5)

        btn = wx.Button(self, wx.ID_CANCEL, u'取消')
        box.Add(btn, 0, wx.ALIGN_CENTRE | wx.ALL, 5)

        sizer.Add(box, 0, wx.ALIGN_CENTER_VERTICAL | wx.CENTER | wx.ALL, 5)

        self.message = tc = wx.TextCtrl(self, -1, '', size=(400, 100), style=wx.TE_MULTILINE|wx.TE_PROCESS_ENTER|wx.TE_READONLY)
        tc.SetInsertionPoint(0)
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(tc, 1, wx.EXPAND)

        sizer.Add(box, 0, wx.ALIGN_CENTER_VERTICAL | wx.CENTER | wx.ALL, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Bind(wx.EVT_BUTTON, self.on_login, self.b_login)
        self.Bind(wx.EVT_BUTTON, self.on_save, self.b_save)

    def on_login(self, evt):
        td_front = self.t_td_front.GetValue()
        md_front = self.t_md_front.GetValue()
        broker_id = self.t_broker_id.GetValue()
        user_id = self.t_user_id.GetValue()
        password = self.t_password.GetValue()
        instrument_ids = self.t_instrument_ids.GetValue().split(',')
        instrument_ids = [inst_id.strip() for inst_id in instrument_ids]
        print td_front, md_front, broker_id, user_id, password, instrument_ids

        self.user_id = user_id
        self.broker_id = broker_id
        self.instrument_ids = instrument_ids
        self.trade_agent = TradeAgent(td_front, broker_id, user_id, password)
        self.md_agent = MdAgent(md_front, broker_id, user_id, password)

        if self.load_data(instrument_ids):
            self.EndModal(wx.ID_OK)
        else:
            msg_error = '连接服务器失败'
            wx.MessageBox(msg_error, 'Error', wx.OK | wx.ICON_ERROR)

    def load_data(self, instrument_ids):
        if self.trade_agent.ready():
            self.write_message(u'交易服务连接成功.')
        else:
            self.write_message(u'交易服务连接失败')
            return False

        if self.md_agent.ready():
            self.write_message(u'行情服务连接成功')
        else:
            self.write_message(u'行情服务连接失败')
        self.write_message(u'数据加载中...')
        self.md_agent.subscribe_market_data(instrument_ids)
        time.sleep(1.1)
        if not self.trade_agent.query_settlement_info_confirm():
            self.trade_agent.settlement_info_confirm()
        time.sleep(1.1)
        self.trade_agent.load_instruments(instrument_ids)

        self.trade_agent.query_order()
        time.sleep(1.1)
        self.trade_agent.query_trade()

        self.write_message(u'数据加载完成')
        return True

    def on_save(self, evt):
        cp.set('user', 'td_front', self.t_td_front.GetValue())
        cp.set('user', 'md_front', self.t_md_front.GetValue())
        cp.set('user', 'broker_id', self.t_broker_id.GetValue())
        cp.set('user', 'user_id', self.t_user_id.GetValue())
        cp.set('user', 'password', self.t_password.GetValue())
        cp.set('user', 'instrument_ids', self.t_instrument_ids.GetValue())
        cp.write(open('ctp.conf', 'w'))

    def write_message(self, msg):
        self.message.SetInsertionPoint(-1)
        self.message.WriteText(datetime.datetime.now().strftime('%H:%M:%S') + ' ' + msg)
        self.message.WriteText('\n')


class SpreadDialog(wx.Dialog):
    def __init__(self, parent, id, title, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.DEFAULT_DIALOG_STYLE):
        pre = wx.PreDialog()
        pre.SetExtraStyle(wx.DIALOG_EX_CONTEXTHELP)
        pre.Create(parent, id, title, pos, size, style)

        self.PostCreate(pre)

        self.market_data_dict = {}  # 合约实时行情
        self.spread_orders = []  # 套利单

        self.file = open('trade.csv', 'a')

    #
    # 初始化界面
    def init_layout(self, broker_id, user_id, instrument_ids):
        self.current_item = None

        sizer = wx.BoxSizer(wx.VERTICAL)

        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, u'经纪公司:', size=(60, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        label = wx.StaticText(self, -1, broker_id, size=(50, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        label = wx.StaticText(self, -1, u'用户名:', size=(50, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        label = wx.StaticText(self, -1, user_id, size=(50, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        line = wx.StaticLine(self, -1, size=(20, -1), style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT | wx.TOP, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)
        box1 = wx.BoxSizer(wx.VERTICAL)
        self.init_panel(box1, instrument_ids)
        box.Add(box1, 0, wx.ALIGN_CENTRE | wx.ALL, 10)
        box1 = wx.StaticBox(self, -1, u'下单')
        bsizer1 = wx.StaticBoxSizer(box1, wx.VERTICAL)
        # self.order_dvlc = self.init_order_dvlc()
        self.order_list = self.init_order_list()
        bsizer1.Add(self.order_list, 1, wx.EXPAND)
        box.Add(bsizer1, 0, wx.ALIGN_CENTRE | wx.ALL, 10)
        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.message = tc = wx.TextCtrl(self, -1, '', size=(400, 100), style=wx.TE_MULTILINE|wx.TE_PROCESS_ENTER|wx.TE_READONLY)
        tc.SetInsertionPoint(0)
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(tc, 1, wx.EXPAND)

        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Bind(wx.EVT_CLOSE, self.on_dialog_close)

    def init_order_list(self):
        order_list = wx.ListCtrl(self, size=(500, 200), style=wx.LC_REPORT)

        order_list.InsertColumn(0, u'合约名称', width=100)
        order_list.InsertColumn(1, u'买卖', width=60)
        order_list.InsertColumn(2, u'开平', width=60)
        order_list.InsertColumn(3, u'挂单数量', width=80)
        order_list.InsertColumn(4, u'未成交数量', width=80)
        order_list.InsertColumn(5, u'挂单价格', width=60)


        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected, order_list)
        order_list.Bind(wx.EVT_LEFT_DCLICK, self.on_double_click)

        return order_list

    def init_panel(self, sizer, instrument_ids):
        #
        # 合约
        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, u'合约名称:', (40, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 10)
        # This combobox is created with a preset list of values.
        self.instrument_id_1 = cb = wx.ComboBox(self, -1, u'', (50, -1),
                                             (100, -1), instrument_ids,
                                             wx.CB_DROPDOWN
                                             #| wx.TE_PROCESS_ENTER
                                             #| wx.CB_SORT
                                             )
        box.Add(cb, 0, wx.ALIGN_CENTRE | wx.ALL, 0)
        label = wx.StaticText(self, -1, u'-', size=(10, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 10)
        # This combobox is created with a preset list of values.
        self.instrument_id_2 = cb = wx.ComboBox(self, -1, u'', (50, -1),
                                             (100, -1), instrument_ids,
                                             wx.CB_DROPDOWN
                                             #| wx.TE_PROCESS_ENTER
                                             #| wx.CB_SORT
                                             )
        box.Add(cb, 0, wx.ALIGN_CENTRE | wx.ALL, 0)
        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        #
        # 多空 开平
        box = wx.BoxSizer(wx.HORIZONTAL)
        self.rb_direction = rb = wx.RadioBox(self, -1, u"", wx.DefaultPosition, wx.DefaultSize, [e[1] for e in direction_list])
        box.Add(rb, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.rb_offset = rb = wx.RadioBox(self, -1, u"", wx.DefaultPosition, wx.DefaultSize, [e[1] for e in offset_list])
        box.Add(rb, 0, wx.ALIGN_CENTRE | wx.ALL, 0)
        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)
        #
        # 手数 价格
        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, u'手数:', size=(40, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 0)
        self.t_volume = wx.TextCtrl(self, -1, '1', size=(40, -1))
        box.Add(self.t_volume, 0, wx.ALIGN_CENTRE | wx.ALL, 10)
        label = wx.StaticText(self, -1, u'限价:', size=(40, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 0)
        self.t_limit_price = wx.TextCtrl(self, -1, '', size=(40, -1))
        box.Add(self.t_limit_price, 0, wx.ALIGN_CENTRE | wx.ALL, 2)

        # spread买卖价
        box1 = wx.BoxSizer(wx.VERTICAL)
        # 卖
        box2 = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, u'卖:', size=(40, -1))
        box2.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 0)
        self.s_ask_price = label = wx.StaticText(self, -1, '', size=(80, -1))
        box2.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 0)
        box1.Add(box2, 0, wx.ALIGN_CENTRE | wx.ALL, 0)
        # 买
        box2 = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, u'买:', size=(40, -1))
        box2.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 0)
        self.s_bid_price = label = wx.StaticText(self, -1, '', size=(80, -1))
        box2.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 0)
        box1.Add(box2, 0, wx.ALIGN_CENTRE | wx.ALL, 0)
        box.Add(box1, 0, wx.ALIGN_CENTRE | wx.ALL, 10)
        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)

        # 下单按钮
        box = wx.BoxSizer(wx.HORIZONTAL)
        b_make_order = wx.Button(self, -1, u'下单', (50, -1))
        box.Add(b_make_order, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.EXPAND, 5)
        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)

        self.Bind(wx.EVT_BUTTON, self.on_make_spread_order, b_make_order)

    #
    # 初始化数据
    def init(self, trade_agent, md_agent):
        self.trade_agent = trade_agent
        self.md_agent = md_agent
        self.trade_agent.callback = self.process_trade_agent_data
        self.md_agent.add_listener(self.process_market_data)

        # self.init_timer()

    # #
    # # 定时器初始化及执行方法
    # def init_timer(self):
    #     self.Bind(wx.EVT_TIMER, self.on_timer)
    #     self.t1 = wx.Timer(self, id=1)
    #     self.t1.Start(250)

    # def on_timer(self, evt):
    #     id = evt.GetTimer().GetId()
    #     if id == 1:
    #         self.process_market_data(self.md_agent.market_data_dict)

    #
    # 事件处理方法
    def on_make_spread_order(self, evt):
        try:
            uid = uuid.uuid1().hex
            instrument_id_1 = self.instrument_id_1.GetValue()
            instrument_id_2 = self.instrument_id_2.GetValue()
            direction = direction_list[self.rb_direction.GetSelection()][0]
            offset = offset_list[self.rb_offset.GetSelection()][0]
            if not self.t_volume.GetValue() or not self.t_limit_price.GetValue():
                return
            volume = int(self.t_volume.GetValue())
            # volume_multiplier = 1
            total_volume = volume
            limit_price = int(self.t_limit_price.GetValue())
            if not instrument_id_1 or not instrument_id_2 or not volume:
                return
            self.spread_orders.append({
                'direction': direction,
                'offset': offset,
                'limit_price': limit_price,
                # 'volume_multiplier': volume_multiplier,  # 手数比
                'running': False,  # 是否正在成交中
                'instrument_1': {  # 合约1
                    'instrument_id': instrument_id_1,  # 合约代码
                    'order_status': None,  # 合约报单状态，初始无报单为None
                    'total_volume': total_volume,  # 合约总挂单数量
                    'volume': total_volume,  # 合约未成交数量
                },
                'instrument_2': {  # 合约2
                    'instrument_id': instrument_id_2,  # 合约代码
                    'order_status': None,  # 合约报单状态，初始无报单为None
                    'total_volume': total_volume ,  # 合约总挂单数量
                    'volume': total_volume,  # 合约未成交数量
                }
            })
            self.show_order_list()
        except:
            print traceback.format_exc()

    def on_item_selected(self, evt):
        self.current_item = evt.m_itemIndex
        evt.Skip()

    def on_double_click(self, evt):
        if self.current_item is not None:
            self.spread_orders.pop(self.current_item)
            self.show_order_list()
        evt.Skip()

    def on_dialog_close(self, evt):
        self.md_agent.del_listener(self.process_market_data)
        if self.file:
            self.file.close()
        self.Destroy()

    #
    # 回调消息处理方法
    def process_trade_agent_data(self, data):
        if isinstance(data, ApiStruct.Order):
            if data.SessionID == self.trade_agent.session_id and data.FrontID == self.trade_agent.front_id:
                self.process_order(data)
                self.write_message(data.StatusMsg)
        elif isinstance(data, ApiStruct.Trade):
            self.process_trade(data)

    # 处理成交回报
    def process_trade(self, trade):
        instrument = None
        for spread_order in self.spread_orders:
            if not spread_order.get('running'):
                continue
            instrument_1 = spread_order.get('instrument_1')
            instrument_2 = spread_order.get('instrument_2')
            if not instrument_1 or not instrument_2:
                continue
            instrument_id_1 = instrument_1.get('instrument_id')
            instrument_id_2 = instrument_2.get('instrument_id')
            order_sys_id_1 = instrument_1.get('order_sys_id')
            order_sys_id_2 = instrument_2.get('order_sys_id')

            if instrument_id_1 == trade.InstrumentID and order_sys_id_1 == trade.OrderSysID:
                instrument = instrument_1
                break
            elif instrument_id_2 == trade.InstrumentID and order_sys_id_2 == trade.OrderSysID:
                instrument = instrument_2
                break

        if instrument and instrument.get('order_status') != ApiStruct.OST_AllTraded and instrument.get('volume') > 0:
            instrument['order_status'] = ApiStruct.OST_AllTraded
            instrument['volume'] -= 1
            instrument['price'] = trade.Price
            instrument.pop('order_ref', None)
            instrument.pop('order_sys_id', None)
            self.write_message(u'开仓: {} 方向: {} 数量: {} 价格: {}'.format(
                trade.InstrumentID, common.desc_direction(trade.Direction, trade.OffsetFlag), trade.Volume, trade.Price))
            self.update_running_spread_orders()
            self.show_order_list()

    # 处理撤单消息
    def process_order(self, order):
        instrument = None
        for spread_order in self.spread_orders:
            if not spread_order.get('running'):
                continue
            instrument_1 = spread_order.get('instrument_1')
            instrument_2 = spread_order.get('instrument_2')
            if not instrument_1 or not instrument_2:
                continue
            instrument_id_1 = instrument_1.get('instrument_id')
            instrument_id_2 = instrument_2.get('instrument_id')
            order_ref_1 = instrument_1.get('order_ref')
            order_ref_2 = instrument_2.get('order_ref')

            if instrument_id_1 == order.InstrumentID and order_ref_1 == order.OrderRef:
                instrument = instrument_1
                break
            elif instrument_id_2 == order.InstrumentID and order_ref_2 == order.OrderRef:
                instrument = instrument_2
                break

        if instrument:
            if order.OrderSysID:
                instrument['order_sys_id'] = order.OrderSysID

            if order.OrderStatus == ApiStruct.OST_Canceled:
                instrument['order_status'] = ApiStruct.OST_Canceled
                instrument.pop('order_ref', None)
                instrument.pop('order_sys_id', None)
                self.update_running_spread_orders()

    # 处理行情消息
    def process_market_data(self, market_data):
        instrument_id = market_data.InstrumentID
        self.market_data_dict[instrument_id] = market_data
        # # 更新合约实时行情数据
        # self.market_data_dict = market_data_dict
        # 超时撤单
        self.refer_spread_orders()
        # 判断并执行下单
        self.execute_spread_orders()
        # 更新ui
        self.update_ui()

    # 更新正在买卖挂单状态
    def update_running_spread_orders(self):
        print 'update_running_spread_orders'
        for order in self.spread_orders:
            if not order.get('running'):
                continue
            instrument_1 = order.get('instrument_1')
            instrument_2 = order.get('instrument_2')
            if not instrument_1 or not instrument_2:
                continue

            order_status_1 = instrument_1.get('order_status')
            order_status_2 = instrument_2.get('order_status')
            if order_status_1 is None or order_status_2 is None:
                continue

            instrument_id_1 = instrument_1.get('instrument_id')
            instrument_id_2 = instrument_2.get('instrument_id')
            name = '{}&{}'.format(instrument_id_1, instrument_id_2)
            direction = order.get('direction')
            offset = order.get('offset')
            limit_price = order.get('limit_price')
            if order_status_1 == ApiStruct.OST_AllTraded and order_status_2 == ApiStruct.OST_AllTraded:  # 双边均成交
                price_1 = instrument_1.get('price')
                price_2 = instrument_2.get('price')
                price = '{}/{}'.format(price_1, price_2)
                spread = price_1 - price_2
                slip_point = spread - limit_price if direction == ApiStruct.D_Buy else limit_price - spread
                self.file.write('{},{},{},{},{},{},{},{}\n'.format(
                    name, direction, offset, limit_price, price, spread, slip_point,
                    datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                order['running'] = False
                self.execute_spread_orders()
            elif order_status_1 == ApiStruct.OST_Canceled and order_status_2 == ApiStruct.OST_Canceled:  # 双边均撤单
                order['running'] = False
            elif order_status_1 == ApiStruct.OST_AllTraded and order_status_2 == ApiStruct.OST_Canceled:  # 合约1成交，合约2撤单
                # 合约2追单
                order['order_2'] = True
            elif order_status_1 == ApiStruct.OST_Canceled and order_status_2 == ApiStruct.OST_AllTraded:  # 合约1撤单，合约2成交
                # 合约1追单
                order['order_1'] = True

    # 超时撤单
    def refer_spread_orders(self):
        for order in self.spread_orders:
            if not order.get('running'):
                continue
            instrument_1 = order.get('instrument_1')
            instrument_2 = order.get('instrument_2')
            if instrument_1:
                self.refer_order(instrument_1)
            if instrument_2:
                self.refer_order(instrument_2)

    # 判断并执行下单
    def execute_spread_orders(self):
        for order in self.spread_orders:
            instrument_1 = order.get('instrument_1')
            instrument_2 = order.get('instrument_2')
            if not instrument_1 or not instrument_2:
                continue
            instrument_id_1 = instrument_1.get('instrument_id')
            instrument_id_2 = instrument_2.get('instrument_id')
            volume1 = instrument_1.get('volume')
            volume2 = instrument_2.get('volume')
            limit_price = order.get('limit_price')
            direction = order.get('direction')
            offset = order.get('offset')
            # volume_multiplier = order.get('volume_multiplier', 1)
            if not instrument_id_1 or not instrument_id_2 or (volume1 <= 0 and volume2 <= 0) or limit_price is None:
                continue
            if instrument_id_1 not in self.market_data_dict or instrument_id_2 not in self.market_data_dict:
                continue
            if direction not in [ApiStruct.D_Buy, ApiStruct.D_Sell]:
                continue
            if offset not in [ApiStruct.OF_Open, ApiStruct.OF_CloseToday, ApiStruct.OF_Close]:
                continue
            market_data_1 = self.market_data_dict[instrument_id_1]
            market_data_2 = self.market_data_dict[instrument_id_2]

            if order.get('running'):  # 已在执行买卖
                if order.get('order_1'):  # 需合约1追单
                    order.pop('order_1', None)
                    if volume1 > 0:
                        o = self.order_1(instrument_id_1, market_data_1, direction, offset)
                        instrument_1['order_ref'] = o.OrderRef
                        instrument_1['order_status'] = ApiStruct.OST_Unknown
                        instrument_1['life_time'] = order_life_time
                elif order.get('order_2'):
                    order.pop('order_2', None)
                    if volume2 > 0:
                        o = self.order_2(instrument_id_2, market_data_2, direction, offset)
                        instrument_2['order_ref'] = o.OrderRef
                        instrument_2['order_status'] = ApiStruct.OST_Unknown
                        instrument_2['life_time'] = order_life_time
                continue

            ask_price_spread = market_data_1.AskPrice1 - market_data_2.BidPrice1
            ask_price_volume = min(market_data_1.AskVolume1, market_data_2.BidVolume1)
            bid_price_spread = market_data_1.BidPrice1 - market_data_2.AskPrice1
            bid_price_volume = min(market_data_1.BidVolume1, market_data_2.AskVolume1)
            if (direction == ApiStruct.D_Buy and ask_price_spread <= limit_price and ask_price_volume >= volume_threshold) or \
                    (direction == ApiStruct.D_Sell and bid_price_spread >= limit_price and bid_price_volume >= volume_threshold):  # 满足买入条件
                if volume1 > 0:
                    o = self.order_1(instrument_id_1, market_data_1, direction, offset)
                    instrument_1['order_ref'] = o.OrderRef
                    instrument_1['order_status'] = ApiStruct.OST_Unknown
                    instrument_1['life_time'] = order_life_time
                if volume2 > 0:
                    o = self.order_2(instrument_id_2, market_data_2, direction, offset)
                    instrument_2['order_ref'] = o.OrderRef
                    instrument_2['order_status'] = ApiStruct.OST_Unknown
                    instrument_2['life_time'] = order_life_time
                order['running'] = True

    # 合约1下单
    def order_1(self, instrument_id, market_data, direction, offset):
        if direction == ApiStruct.D_Buy:
            if offset == ApiStruct.OF_Open:
                return self.trade_agent.buy(instrument_id, 1, market_data.AskPrice1-1, ApiStruct.TC_GFD)  # 买开仓合约1
            elif offset == ApiStruct.OF_CloseToday:
                return self.trade_agent.cover_today(instrument_id, 1, market_data.AskPrice1, ApiStruct.TC_GFD)  # 买平今合约1
            else:  # offset == ApiStruct.OF_Close:
                return self.trade_agent.cover(instrument_id, 1, market_data.AskPrice1, ApiStruct.TC_GFD)  # 买平仓合约1
        else:  # direction == ApiStruct.D_Sell
            if offset == ApiStruct.OF_Open:
                return self.trade_agent.short(instrument_id, 1, market_data.BidPrice1, ApiStruct.TC_GFD)  # 卖开仓合约1
            elif offset == ApiStruct.OF_CloseToday:
                return self.trade_agent.sell_today(instrument_id, 1, market_data.BidPrice1, ApiStruct.TC_GFD)  # 卖平今合约1
            else:  # offset == ApiStruct.OF_Close:
                return self.trade_agent.sell(instrument_id, 1, market_data.BidPrice1, ApiStruct.TC_GFD)  # 卖平仓合约1

    # 合约2下单
    def order_2(self, instrument_id, market_data, direction, offset):
        if direction == ApiStruct.D_Buy:
            if offset == ApiStruct.OF_Open:
                return self.trade_agent.short(instrument_id, 1, market_data.BidPrice1, ApiStruct.TC_GFD)  # 卖开仓合约2
            elif offset == ApiStruct.OF_CloseToday:
                return self.trade_agent.sell_today(instrument_id, 1, market_data.BidPrice1, ApiStruct.TC_GFD)  # 卖平今合约2
            else:  # offset == ApiStruct.OF_Close:
                return self.trade_agent.sell(instrument_id, 1, market_data.BidPrice1, ApiStruct.TC_GFD)  # 卖平仓合约2
        else:  # direction == ApiStruct.D_Sell
            if offset == ApiStruct.OF_Open:
                return self.trade_agent.buy(instrument_id, 1, market_data.AskPrice1, ApiStruct.TC_GFD)  # 买开仓合约2
            elif offset == ApiStruct.OF_CloseToday:
                return self.trade_agent.cover_today(instrument_id, 1, market_data.AskPrice1, ApiStruct.TC_GFD)  # 买平今合约2
            else:  # offset == ApiStruct.OF_Close:
                return self.trade_agent.cover(instrument_id, 1, market_data.AskPrice1, ApiStruct.TC_GFD)  # 买平仓合约2

    # 合约撤单
    def refer_order(self, instrument):
        instrument_id = instrument.get('instrument_id')
        order_status = instrument.get('order_status')
        order_ref = instrument.get('order_ref')
        life_time = instrument.get('life_time')
        if instrument_id and order_status == ApiStruct.OST_Unknown and order_ref and life_time > 0:
            life_time -= 1
            if life_time <= 0:
                self.trade_agent.refer_local(instrument_id, order_ref)
            else:
                instrument['life_time'] = life_time

    def show_order_list(self):
        self.order_list.DeleteAllItems()
        for order in self.spread_orders:
            instrument_1 = order.get('instrument_1')
            instrument_2 = order.get('instrument_2')
            if not instrument_1 or not instrument_2:
                continue
            instrument_id_1 = instrument_1.get('instrument_id')
            instrument_id_2 = instrument_2.get('instrument_id')
            name = '{}&{}'.format(instrument_id_1, instrument_id_2)
            volume1 = instrument_1.get('volume')
            volume2 = instrument_2.get('volume')
            total_volume1 = instrument_1.get('total_volume')
            total_volume2 = instrument_2.get('total_volume')
            volume = '{}/{}'.format(volume1, volume2)
            total_volume = '{}/{}'.format(total_volume1, total_volume2)
            index = self.order_list.InsertStringItem(sys.maxint, name)
            self.order_list.SetStringItem(index, 1, direction_dict.get(order.get('direction')))
            self.order_list.SetStringItem(index, 2, offset_dict.get(order.get('offset')))
            self.order_list.SetStringItem(index, 3, total_volume)
            self.order_list.SetStringItem(index, 4, volume)
            self.order_list.SetStringItem(index, 5, str(order.get('limit_price')))

    def update_ui(self):
        instrument_id_1 = self.instrument_id_1.GetValue()
        instrument_id_2 = self.instrument_id_2.GetValue()
        if instrument_id_1 in self.market_data_dict and instrument_id_2 in self.market_data_dict:
            market_data_1 = self.market_data_dict[instrument_id_1]
            market_data_2 = self.market_data_dict[instrument_id_2]
            if market_data_1.AskVolume1 and market_data_2.BidVolume1:
                ask_price_spread = market_data_1.AskPrice1 - market_data_2.BidPrice1
                ask_price_volume = min(market_data_1.AskVolume1, market_data_2.BidVolume1)
                self.s_ask_price.SetLabelText('{} / {}'.format(ask_price_spread, ask_price_volume))
            else:
                self.s_ask_price.SetLabelText('')
            if market_data_1.BidVolume1 and market_data_2.AskVolume1:
                bid_price_spread = market_data_1.BidPrice1 - market_data_2.AskPrice1
                bid_price_volume = min(market_data_1.BidVolume1, market_data_2.AskVolume1)
                self.s_bid_price.SetLabelText('{} / {}'.format(bid_price_spread, bid_price_volume))
            else:
                self.s_bid_price.SetLabelText('')

    def write_message(self, msg):
        self.message.SetInsertionPoint(-1)
        self.message.WriteText(datetime.datetime.now().strftime('%H:%M:%S') + ' ' + msg)
        self.message.WriteText('\n')


class TraderApp(wx.App):
    def __init__(self, redirect=False, filename=None):
        wx.App.__init__(self, redirect, filename)
        self.login_dlg = LoginDialog(None, -1, u'登录', size=(600, 300))
        # self.frame = wx.Frame(None, wx.ID_ANY, title='Main', size=(400, 300), style=wx.DEFAULT_FRAME_STYLE)
        # self.panel = TraderPanel(self.frame)

if __name__ == '__main__':
    app = TraderApp()
    app.login_dlg.CenterOnScreen()
    # this does not return until the dialog is closed.
    val = app.login_dlg.ShowModal()
    if val == wx.ID_OK:
        # td_front = app.login_dlg.t_td_front.GetValue()
        # md_front = app.login_dlg.t_md_front.GetValue()
        # broker_id = app.login_dlg.t_broker_id.GetValue()
        # user_id = app.login_dlg.t_user_id.GetValue()
        # password = app.login_dlg.t_password.GetValue()
        # instrument_ids = app.login_dlg.t_instrument_ids.GetValue().split(',')
        # instrument_ids = [inst_id.strip() for inst_id in instrument_ids]
        # print td_front, md_front, broker_id, user_id, password, instrument_ids

        broker_id = app.login_dlg.broker_id
        user_id = app.login_dlg.user_id
        instrument_ids = app.login_dlg.instrument_ids
        trade_agent = app.login_dlg.trade_agent
        md_agent = app.login_dlg.md_agent
        app.spread_dlg = SpreadDialog(None, -1, u'套利', size=(600, -1))
        app.spread_dlg.init_layout(broker_id, user_id, instrument_ids)
        app.spread_dlg.init(trade_agent, md_agent)
        app.spread_dlg.ShowModal()

        # app.panel.init_layout(broker_id, user_id, instrument_ids)
        # app.frame.Show()
        # app.panel.init(td_front, md_front, broker_id, user_id, password, instrument_ids)
        # app.MainLoop()

    # agent = TradeAgent(td_front, broker_id, user_id, password)
    # agent.ready()
    # agent.login()
    # time.sleep(2)
    # #
    # agent.load_instruments(instrument_ids)
    # print agent.instrument_dict
    #
    # agent.sell('ag1702', 2)
    # agent.short('ag1702', 4)
    #
    # time.sleep(2)
    # print agent.query_position('ag1702')


