# coding=utf-8
from operator import attrgetter

import datetime
import ConfigParser
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

default_open_price_type = 1  # 默认开仓报价类型 0 - 对手价; 1 - 排队价+1; 2 - 排队价
default_open_time_condition = 0  # 默认开仓报价时效 0 - 当天有效; 1 - IOC
default_close_price_type = 2  # 默认平仓报价类型 0 - 对手价; 1 - 排队价+1; 2 - 排队价
# default_stop_loss = False  # 默认是否开启止损退出 True - 开启; False - 关闭
# default_stop_loss_ticks = 5  # 默认止损price ticks
# default_stop_back = False  # 默认是否开启回撤退出 True - 开启; False - 关闭
# default_stop_back_threshold = 5  # 默认回撤激活price ticks, 开仓价 + ticks
# default_stop_back_ticks = 2  # 默认回撤触发price ticks, 最高价 - ticks


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

        btn = wx.Button(self, wx.ID_OK, U'登录')
        btn.SetDefault()
        box.Add(btn, 0, wx.ALIGN_CENTRE | wx.ALL, 5)

        btn = wx.Button(self, wx.ID_CANCEL, u'取消')
        box.Add(btn, 0, wx.ALIGN_CENTRE | wx.ALL, 5)

        sizer.Add(box, 0, wx.ALIGN_CENTER_VERTICAL | wx.CENTER | wx.ALL, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Bind(wx.EVT_BUTTON, self.on_save, self.b_save)

    def on_save(self, evt):
        cp.set('user', 'td_front', self.t_td_front.GetValue())
        cp.set('user', 'md_front', self.t_md_front.GetValue())
        cp.set('user', 'broker_id', self.t_broker_id.GetValue())
        cp.set('user', 'user_id', self.t_user_id.GetValue())
        cp.set('user', 'password', self.t_password.GetValue())
        cp.set('user', 'instrument_ids', self.t_instrument_ids.GetValue())
        cp.write(open('ctp.conf', 'w'))


class TacticsDialog(wx.Dialog):
    def __init__(self, parent, id, title, broker_id, user_id, instrument, panel, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.DEFAULT_DIALOG_STYLE):
        pre = wx.PreDialog()
        pre.SetExtraStyle(wx.DIALOG_EX_CONTEXTHELP)
        pre.Create(parent, id, title, pos, size, style)

        self.PostCreate(pre)

        self.panel = panel
        self.trade_agent = panel.trade_agent
        self.md_agent = panel.md_agent

        self.instrument_id = instrument.InstrumentID if instrument else ''
        self.instrument_name = instrument.InstrumentName if instrument else ''
        self.volume_multiple = instrument.VolumeMultiple if instrument else None
        self.price_tick = instrument.PriceTick if instrument else None

        self.last_price = None
        self.bid_price = None
        self.bid_volume = None
        self.ask_price = None
        self.ask_volume = None
        self.order_dict = {}
        self.long_position = 0
        self.short_position = 0
        # self.reset()

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
        box2 = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, u'合约:', size=(50, -1))
        box2.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        label = wx.StaticText(self, -1, '{} ({})'.format(self.instrument_id, self.instrument_name), size=(120, -1))
        box2.Add(label, 0, wx.ALIGN_LEFT | wx.ALL, 5)
        box1.Add(box2, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        box2 = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, u'最新价:', size=(50, -1))
        box2.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.s_last_price = label = wx.StaticText(self, -1, '', size=(120, -1))
        box2.Add(label, 0, wx.ALIGN_LEFT | wx.ALL, 5)
        box1.Add(box2, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        box.Add(box1, 0, wx.ALIGN_CENTRE | wx.ALL, 5)

        box1 = wx.BoxSizer(wx.VERTICAL)
        box2 = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, u'买一:', size=(50, -1))
        box2.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.s_bid_price = label = wx.StaticText(self, -1, '', size=(50, -1))
        box2.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        label = wx.StaticText(self, -1, u'量:', size=(50, -1))
        box2.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.s_bid_volume = label = wx.StaticText(self, -1, '', size=(50, -1))
        box2.Add(label, 0, wx.ALIGN_LEFT | wx.ALL, 5)
        box1.Add(box2, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        box2 = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, u'卖一:', size=(50, -1))
        box2.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.s_ask_price = label = wx.StaticText(self, -1, '', size=(50, -1))
        box2.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        label = wx.StaticText(self, -1, u'量:', size=(50, -1))
        box2.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.s_ask_volume = label = wx.StaticText(self, -1, '', size=(50, -1))
        box2.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        box1.Add(box2, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        box.Add(box1, 1, wx.ALIGN_CENTRE | wx.ALL, 5)

        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        line = wx.StaticLine(self, -1, size=(20, -1), style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT | wx.TOP, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, u'多头:', size=(60, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.s_long_position = label = wx.StaticText(self, -1, '', size=(60, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        label = wx.StaticText(self, -1, u'空头:', size=(60, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.s_short_position = label = wx.StaticText(self, -1, '', size=(60, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        label = wx.StaticText(self, -1, u'开单:', size=(60, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.s_order_open = label = wx.StaticText(self, -1, '', size=(60, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        label = wx.StaticText(self, -1, u'平单:', size=(60, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.s_order_close = label = wx.StaticText(self, -1, '', size=(60, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        line = wx.StaticLine(self, -1, size=(20, -1), style=wx.LI_HORIZONTAL)
        sizer.Add(line, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.RIGHT | wx.TOP, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)
        self.b_open_long = wx.Button(self, -1, u'开多', (50, -1))
        self.b_open_short = wx.Button(self, -1, u'开空', (50, -1))
        box.Add(self.b_open_long, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        box.Add(self.b_open_short, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        label = wx.StaticText(self, -1, u'数量:', size=(40, -1))
        box.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.t_volume = wx.TextCtrl(self, -1, '1', size=(40, -1))
        box.Add(self.t_volume, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        self.b_volume_add_1 = wx.Button(self, -1, u'+1', (40, -1))
        self.b_volume_sub_1 = wx.Button(self, -1, u'-1', (40, -1))
        box.Add(self.b_volume_add_1, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        box.Add(self.b_volume_sub_1, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)
        self.b_order_ref = wx.Button(self, -1, u'撤单', (50, -1))
        self.b_quick_close = wx.Button(self, -1, u'一键快平', (50, -1))
        box.Add(self.b_order_ref, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        box.Add(self.b_quick_close, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)

        box1 = wx.BoxSizer(wx.HORIZONTAL)
        price_types = [u'对手价', u'排队价+1', u'排队价']
        self.rb_open_price_type = rb = wx.RadioBox(self, -1, u"开仓价格类型", wx.DefaultPosition, wx.DefaultSize, price_types)
        box1.Add(rb, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        price_types = [u'今日有效', u'IOC']
        self.rb_open_time_condition = rb = wx.RadioBox(self, -1, u"开仓报价时效", wx.DefaultPosition, wx.DefaultSize, price_types)
        box1.Add(rb, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        # price_types = [u'对手价', u'排队价+1', u'排队价']
        # self.rb_close_price_type = rb = wx.RadioBox(self, -1, u"平仓价格类型", wx.DefaultPosition, wx.DefaultSize, price_types)
        # box1.Add(rb, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        box.Add(box1, 0, wx.ALIGN_CENTRE | wx.ALL)

        # sbox = wx.StaticBox(self, -1, u'自动退出')
        # bsizer = wx.StaticBoxSizer(sbox, wx.VERTICAL)
        # box1 = wx.BoxSizer(wx.HORIZONTAL)
        # self.cb_stop_loss = cb = wx.CheckBox(self, -1, u"止损退出")
        # box1.Add(cb, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        # label = wx.StaticText(self, -1, u'ticks:', size=(40, -1))
        # box1.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        # self.t_stop_loss_ticks = wx.TextCtrl(self, -1, str(default_stop_loss_ticks), size=(40, -1))
        # box1.Add(self.t_stop_loss_ticks, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        # bsizer.Add(box1, 0, wx.ALIGN_CENTRE | wx.ALL)
        #
        # box1 = wx.BoxSizer(wx.HORIZONTAL)
        # self.cb_stop_back = cb = wx.CheckBox(self, -1, u"回撤退出")
        # box1.Add(cb, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        # label = wx.StaticText(self, -1, u'ticks:', size=(40, -1))
        # box1.Add(label, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        # self.t_stop_back_threshold = wx.TextCtrl(self, -1, str(default_stop_back_threshold), size=(40, -1))
        # box1.Add(self.t_stop_back_threshold, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        # self.t_stop_back_ticks = wx.TextCtrl(self, -1, str(default_stop_back_ticks), size=(40, -1))
        # box1.Add(self.t_stop_back_ticks, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        # bsizer.Add(box1, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        # box.Add(bsizer, 0, wx.ALIGN_CENTRE | wx.ALL)

        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.message = tc = wx.TextCtrl(self, -1, '', size=(400, 100), style=wx.TE_MULTILINE|wx.TE_PROCESS_ENTER|wx.TE_READONLY)
        tc.SetInsertionPoint(0)
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(tc, 1, wx.EXPAND)

        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Bind(wx.EVT_BUTTON, self.on_volume_add_1, self.b_volume_add_1)
        self.Bind(wx.EVT_BUTTON, self.on_volume_sub_1, self.b_volume_sub_1)
        self.Bind(wx.EVT_BUTTON, self.on_open_long, self.b_open_long)
        self.Bind(wx.EVT_BUTTON, self.on_open_short, self.b_open_short)
        # self.Bind(wx.EVT_BUTTON, self.on_order_5, self.b_order_5)
        # self.Bind(wx.EVT_BUTTON, self.on_order_10, self.b_order_10)
        # self.Bind(wx.EVT_BUTTON, self.on_close, self.b_close)
        self.Bind(wx.EVT_BUTTON, self.on_order_ref, self.b_order_ref)
        self.Bind(wx.EVT_BUTTON, self.on_quick_close, self.b_quick_close)
        self.Bind(wx.EVT_CLOSE, self.on_dialog_close)

        self.rb_open_price_type.SetSelection(default_open_price_type)
        self.rb_open_time_condition.SetSelection(default_open_time_condition)
        # self.rb_close_price_type.SetSelection(default_close_price_type)
        # self.cb_stop_loss.SetValue(default_stop_loss)
        # self.cb_stop_back.SetValue(default_stop_back)
        # self.enable_order_buttons(False)
        self.enable_refer_buttons(False)
        self.enable_close_buttons(False)

    # def reset(self):
    #     self.open_price = None
    #     self.open_volume = None
    #     self.open_time = None
    #     self.open_direction = None
    #     self.close_order = None
    #     self.close_price = None
    #     self.highest_price = None
    #     self.stop_loss_price = None
    #     self.stop_back_price = None
    #     self.pnl = None

    def on_volume_add_1(self, evt):
        volume = int(self.t_volume.GetValue())
        volume += 1
        self.t_volume.SetValue(str(volume))

    def on_volume_sub_1(self, evt):
        volume = int(self.t_volume.GetValue())
        volume -= 1
        if volume <= 0:
            volume = 1
        self.t_volume.SetValue(str(volume))

    def on_open_long(self, evt):
        self.open_position(ApiStruct.PD_Long)

    def on_open_short(self, evt):
        self.open_position(ApiStruct.PD_Short)

    def open_position(self, posi_position):
        # self.reset()
        volume = int(self.t_volume.GetValue())
        price_type = self.rb_open_price_type.GetSelection()
        tc_type = self.rb_open_time_condition.GetSelection()
        market_data = self.md_agent.market_data_dict.get(self.instrument_id)
        if not market_data:
            self.panel.write_message(u'该合约行情数据未加载，不支持此类型报价方式')
            return

        if posi_position == ApiStruct.PD_Long:
            if price_type == 2:  # 排队价
                limit_price = market_data.BidPrice1
            elif price_type == 1:  # 排队价 +1 tick
                limit_price = market_data.BidPrice1 + self.price_tick
            else:  # 对手价
                limit_price = market_data.AskPrice1
        else:  # ApiStruct.PD_Short
            if price_type == 2:  # 排队价
                limit_price = market_data.AskPrice1
            elif price_type == 1:  # 排队价 +1 tick
                limit_price = market_data.AskPrice1 - self.price_tick
            else:  # 对手价
                limit_price = market_data.BidPrice1
        if tc_type == 0:
            time_condition = ApiStruct.TC_GFD
        else:
            time_condition = ApiStruct.TC_IOC
        self.trade_agent.open(self.instrument_id, posi_position, volume, limit_price, time_condition)

    def make_order(self, trade, limit_price=0):
        if trade.Volume <= 0:
            return
        position_direction = ApiStruct.PD_Long if trade.Direction == ApiStruct.D_Buy else ApiStruct.PD_Short
        self.trade_agent.close_today(self.instrument_id, position_direction, trade.Volume, limit_price)

    def close_position(self):
        # 撤单
        self.on_order_ref(None)

        market_data = self.md_agent.market_data_dict.get(self.instrument_id)
        if not market_data:
            self.panel.write_message(u'该合约行情数据未加载，不支持此类型报价方式')
            return

        if self.long_position > 0:
            self.trade_agent.close_today(self.instrument_id, ApiStruct.PD_Long, self.long_position, limit_price=0,
                                         market_data=market_data)
        if self.short_position > 0:
            self.trade_agent.close_today(self.instrument_id, ApiStruct.PD_Short, self.short_position, limit_price=0,
                                         market_data=market_data)

    def order(self, trade, ticks):
        market_data = self.md_agent.market_data_dict.get(self.instrument_id)
        if not market_data:
            self.panel.write_message(u'该合约行情数据未加载，不支持此类型报价方式')
            return

        if trade.Direction == ApiStruct.D_Buy:  # 多
            limit_price = trade.Price + ticks * self.price_tick
            if limit_price > market_data.UpperLimitPrice:
                limit_price = market_data.UpperLimitPrice
        else:  # 空
            limit_price = trade.Price - ticks * self.price_tick
            if limit_price < market_data.LowerLimitPrice:
                limit_price = market_data.LowerLimitPrice
        return self.make_order(trade, limit_price)

    def on_order_ref(self, evt):
        for order in self.order_dict.itervalues():
            self.trade_agent.refer(self.instrument_id, order.ExchangeID, order.OrderSysID)
        time.sleep(0.1)

    def on_quick_close(self, evt):
        self.close_position()

    def on_dialog_close(self, evt):
        self.Hide()

    def process_trade(self, trade):
        if self._is_open_trade(trade):  # 开
            if trade.Direction == ApiStruct.D_Buy:  # 多
                self.long_position += trade.Volume
            else:  # 空
                self.short_position += trade.Volume

            position_direction = ApiStruct.PD_Long if trade.Direction == ApiStruct.D_Buy else ApiStruct.PD_Short
            # self.open_price = trade.Price
            # self.highest_price = self.open_price
            # if self.open_volume is None:
            #     self.open_volume = trade.Volume
            # else:
            #     self.open_volume += trade.Volume
            # self.open_time = trade.TradeDate + ' ' + trade.TradeTime
            # self.open_direction = position_direction
            # self._set_stop_values()
            # self.enable_open_buttons(False)
            # self.enable_order_buttons(True)
            # self.enable_close_buttons(True)
            self.update_ui()
            self.write_message(u'开仓: {} 方向: {} 数量: {} 价格: {}'.format(
                self.instrument_id, common.desc_posi_direction(position_direction), trade.Volume, trade.Price))
            self.order(trade, 1)
        elif self._is_close_trade(trade):  # 平
            ansi_position_direction = ApiStruct.PD_Short if trade.Direction == ApiStruct.D_Buy else ApiStruct.PD_Long
            if trade.Direction == ApiStruct.D_Sell and trade.Volume <= self.long_position:  # 卖平仓，减少多头仓位
                self.long_position -= trade.Volume
                self.update_ui()
                self.write_message(u'平仓: {} 方向: {} 数量: {} 价格: {}'.format(
                    self.instrument_id, common.desc_posi_direction(ansi_position_direction), trade.Volume, trade.Price))
            elif trade.Direction == ApiStruct.D_Buy and trade.Volume <= self.short_position:  # 买平仓，减少空头仓位
                self.short_position -= trade.Volume
                self.update_ui()
                self.write_message(u'平仓: {} 方向: {} 数量: {} 价格: {}'.format(
                    self.instrument_id, common.desc_posi_direction(ansi_position_direction), trade.Volume, trade.Price))

    def process_order(self, order):
        if order.TimeCondition == ApiStruct.TC_GFD:
            key = (order.ExchangeID, order.TraderID, order.OrderLocalID)
            if order.OrderStatus in [ApiStruct.OST_NoTradeQueueing, ApiStruct.OST_NoTradeNotQueueing]:
                if key not in self.order_dict:
                    self.order_dict[key] = order
            else:
                if key in self.order_dict:
                    self.order_dict.pop(key, None)

        # if self.close_order is None:
        #     if self._is_close_order(order):
        #         ansi_position_direction = ApiStruct.PD_Short if order.Direction == ApiStruct.D_Buy else ApiStruct.PD_Long
        #         if ansi_position_direction == self.open_direction and order.VolumeTotal <= self.open_volume:
        #             self.close_order = order
        #             self.enable_order_buttons(False)
        #             self.enable_refer_buttons(True)
        #             self.update_ui()
        # elif self._check_order(self.close_order, order):
        #     if order.OrderStatus not in [ApiStruct.OST_NoTradeQueueing, ApiStruct.OST_NoTradeNotQueueing]:
        #         self.close_order = None
        #         self.enable_order_buttons(True)
        #         self.enable_refer_buttons(False)

    def process_market_data(self, market_data):
        if market_data:
            self.last_price = market_data.LastPrice
            self.bid_price = market_data.BidPrice1
            self.bid_volume = market_data.BidVolume1
            self.ask_price = market_data.AskPrice1
            self.ask_volume = market_data.AskVolume1
            # if market_data.LastPrice is not None and self.open_price is not None and self.open_volume:
            #     self.pnl = (self.last_price - self.open_price) * self.open_volume * self.volume_multiple * \
            #                 (1 if self.open_direction == ApiStruct.PD_Long else -1)
            #     if self.highest_price is None:
            #         self.highest_price = market_data.LastPrice
            #     if self.open_direction == ApiStruct.PD_Long and market_data.LastPrice > self.highest_price:
            #         self.highest_price = market_data.LastPrice
            #     elif self.open_direction == ApiStruct.PD_Short and market_data.LastPrice < self.highest_price:
            #         self.highest_price = market_data.LastPrice
            #     self._set_stop_values()
            #     self._check_stop_condition(market_data.LastPrice)
            self.update_ui()

    def update_ui(self):
        self.s_long_position.SetLabelText(str(self.long_position))
        self.s_short_position.SetLabelText(str(self.short_position))
        order_open = len([order for order in self.order_dict.values() if order.CombOffsetFlag == ApiStruct.OF_Open])
        order_close = len(self.order_dict) - order_open
        self.s_order_open.SetLabelText(str(order_open))
        self.s_order_close.SetLabelText(str(order_close))
        if self.last_price is not None:
            self.s_last_price.SetLabelText(str(self.last_price))
        else:
            self.s_last_price.SetLabelText('')
        if self.bid_price is not None:
            self.s_bid_price.SetLabelText(str(self.bid_price))
        else:
            self.s_bid_price.SetLabelText('')
        if self.ask_price is not None:
            self.s_ask_price.SetLabelText(str(self.ask_price))
        else:
            self.s_ask_price.SetLabelText('')
        if self.bid_volume is not None:
            self.s_bid_volume.SetLabelText(str(self.bid_volume))
        else:
            self.s_bid_volume.SetLabelText('')
        if self.ask_volume is not None:
            self.s_ask_volume.SetLabelText(str(self.ask_volume))
        else:
            self.s_ask_volume.SetLabelText('')

        if self.order_dict:
            self.enable_refer_buttons(True)
        else:
            self.enable_refer_buttons(False)
        if self.long_position or self.short_position:
            self.enable_close_buttons(True)
        else:
            self.enable_close_buttons(False)

    def enable_open_buttons(self, enable=True):
        self.b_open_long.Enable(enable)
        self.b_open_short.Enable(enable)

    # def enable_order_buttons(self, enable=True):
    #     self.b_order_5.Enable(enable)
    #     self.b_order_10.Enable(enable)
    #     self.b_close.Enable(enable)

    def enable_refer_buttons(self, enable=True):
        self.b_order_ref.Enable(enable)

    def enable_close_buttons(self, enable=True):
        self.b_quick_close.Enable(enable)

    def _is_open_trade(self, t):
        return t.OffsetFlag == ApiStruct.OF_Open and t.Volume > 0

    def _is_close_trade(self, t):
        return t.OffsetFlag in [ApiStruct.OF_Close, ApiStruct.OF_CloseYesterday, ApiStruct.OF_CloseToday] \
               and t.Volume > 0

    def _is_close_order(self, o):
        return o.CombOffsetFlag in [ApiStruct.OF_Close, ApiStruct.OF_CloseYesterday, ApiStruct.OF_CloseToday] \
               and o.TimeCondition == ApiStruct.TC_GFD \
               and o.OrderStatus in [ApiStruct.OST_NoTradeQueueing, ApiStruct.OST_NoTradeNotQueueing]

    def _is_order(self, o):
        return o.TimeCondition == ApiStruct.TC_GFD \
               and o.OrderStatus in [ApiStruct.OST_NoTradeQueueing, ApiStruct.OST_NoTradeNotQueueing]

    def _check_order(self, o1, o2):
        return o1.ExchangeID == o2.ExchangeID and o1.TraderID == o2.TraderID and o1.OrderLocalID == o2.OrderLocalID

    # def _set_stop_values(self):
    #     stop_loss_ticks = int(self.t_stop_loss_ticks.GetValue())
    #     if stop_loss_ticks > 0:
    #         if self.open_direction == ApiStruct.PD_Long:
    #             self.stop_loss_price = self.open_price - stop_loss_ticks * self.price_tick
    #         else:
    #             self.stop_loss_price = self.open_price + stop_loss_ticks * self.price_tick
    #
    #     stop_back_threshold = int(self.t_stop_back_threshold.GetValue())
    #     stop_back_ticks = int(self.t_stop_back_ticks.GetValue())
    #     if stop_back_threshold > 0 and stop_back_ticks > 0:
    #         if self.open_direction == ApiStruct.PD_Long:
    #             if self.highest_price >= self.open_price + stop_back_threshold * self.price_tick:
    #                 self.stop_back_price = self.highest_price - stop_back_ticks * self.price_tick
    #         else:
    #             if self.highest_price <= self.open_price - stop_back_threshold * self.price_tick:
    #                 self.stop_back_price = self.highest_price + stop_back_ticks * self.price_tick
    #
    # def _check_stop_condition(self, last_price):
    #     if self.cb_stop_loss.GetValue():
    #         if self.open_direction == ApiStruct.PD_Long and self.stop_loss_price is not None and last_price <= self.stop_loss_price:
    #             self.write_message(u'触发止损退出, 止损价格: {}'.format(self.stop_loss_price))
    #             self.close_position()
    #         elif self.open_direction == ApiStruct.PD_Short and self.stop_loss_price is not None and last_price >= self.stop_loss_price:
    #             self.write_message(u'触发止损退出, 止损价格: {}'.format(self.stop_loss_price))
    #             self.close_position()
    #     if self.cb_stop_back.GetValue():
    #         if self.open_direction == ApiStruct.PD_Long and self.stop_back_price is not None and last_price <= self.stop_back_price:
    #             self.write_message(u'触发回撤退出, 回撤价格: {}'.format(self.stop_back_price))
    #             self.close_position()
    #         elif self.open_direction == ApiStruct.PD_Short and self.stop_back_price is not None and last_price >= self.stop_back_price:
    #             self.write_message(u'触发回撤退出, 回撤价格: {}'.format(self.stop_back_price))
    #             self.close_position()

    def write_message(self, msg):
        self.message.SetInsertionPoint(-1)
        self.message.WriteText(datetime.datetime.now().strftime('%H:%M:%S') + ' ' + msg)
        self.message.WriteText('\n')


class MarketDataDialog(wx.Dialog):
    def __init__(self, parent, id, title, broker_id, user_id, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.DEFAULT_DIALOG_STYLE):
        pre = wx.PreDialog()
        pre.SetExtraStyle(wx.DIALOG_EX_CONTEXTHELP)
        pre.Create(parent, id, title, pos, size, style)

        self.PostCreate(pre)

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

        t = wx.StaticBox(self, -1, u'行情')
        box = wx.StaticBoxSizer(t, wx.VERTICAL)
        self.market_data_dvlc = self.init_market_data_dvlc()
        box.Add(self.market_data_dvlc, 1, wx.EXPAND)
        sizer.Add(box, 0, wx.EXPAND, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Bind(wx.EVT_CLOSE, self.on_dialog_close)

    def init_market_data_dvlc(self):
        dvlc = dv.DataViewListCtrl(self, size=(400, 300), style=wx.BORDER_THEME
                                   | dv.DV_ROW_LINES
                                   #| dv.DV_HORIZ_RULES
                                   | dv.DV_VERT_RULES
                                   | dv.DV_MULTIPLE
                                   )
        dvlc.AppendTextColumn(u'合约', width=80)
        dvlc.AppendTextColumn(u'最新价', width=80)
        dvlc.AppendTextColumn(u'买一', width=80)
        dvlc.AppendTextColumn(u'卖一', width=80)
        return dvlc

    def on_dialog_close(self, evt):
        self.Hide()


class PositionDialog(wx.Dialog):
    def __init__(self, parent, id, title, broker_id, user_id, panel, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.DEFAULT_DIALOG_STYLE):
        pre = wx.PreDialog()
        pre.SetExtraStyle(wx.DIALOG_EX_CONTEXTHELP)
        pre.Create(parent, id, title, pos, size, style)

        self.PostCreate(pre)

        self.panel = panel
        self.trade_agent = panel.trade_agent
        self.md_agent = panel.md_agent

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
        self.b_close_all = wx.Button(self, -1, u'全部清仓', (50, -1))
        box.Add(self.b_close_all, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        b1 = wx.StaticBox(self, -1, u'资金')
        bsizer1 = wx.StaticBoxSizer(b1, wx.VERTICAL)
        self.account_dvlc = self.init_account_dvlc()
        bsizer1.Add(self.account_dvlc, 1, wx.EXPAND)

        b2 = wx.StaticBox(self, -1, u'持仓')
        bsizer2 = wx.StaticBoxSizer(b2, wx.VERTICAL)
        self.position_dvlc = self.init_position_dvlc()
        bsizer2.Add(self.position_dvlc, 1, wx.EXPAND)

        sizer.Add(bsizer1, 0, wx.EXPAND)
        sizer.Add(bsizer2, 1, wx.EXPAND)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Bind(wx.EVT_BUTTON, self.on_close_all, self.b_close_all)
        self.Bind(wx.EVT_CLOSE, self.on_dialog_close)

    def init_account_dvlc(self):
        dvlc = dv.DataViewListCtrl(self, size=(600, 60))
        dvlc.AppendTextColumn(u'昨日权益', width=80)
        dvlc.AppendTextColumn(u'权益', width=80)
        dvlc.AppendTextColumn(u'可用资金', width=80)
        dvlc.AppendTextColumn(u'保证金', width=80)
        dvlc.AppendTextColumn(u'持仓盈亏', width=80)
        dvlc.AppendTextColumn(u'平仓盈亏', width=80)
        dvlc.AppendTextColumn(u'手续费', width=80)
        return dvlc

    def init_position_dvlc(self):
        dvlc = dv.DataViewListCtrl(self, size=(600, 200), style=wx.BORDER_THEME
                                   | dv.DV_ROW_LINES
                                   #| dv.DV_HORIZ_RULES
                                   | dv.DV_VERT_RULES
                                   | dv.DV_MULTIPLE
                                   )
        dvlc.AppendTextColumn(u'合约', width=80)
        dvlc.AppendTextColumn(u'方向', width=80)
        dvlc.AppendTextColumn(u'持仓', width=60)
        dvlc.AppendTextColumn(u'今持', width=60)
        dvlc.AppendTextColumn(u'今开', width=60)
        dvlc.AppendTextColumn(u'今平', width=60)
        dvlc.AppendTextColumn(u'持仓盈亏', width=80)
        dvlc.AppendTextColumn(u'平仓盈亏', width=80)
        return dvlc

    def close_one(self, instrument_id, position_list, market_data):
        posi_direction = position_list[0].PosiDirection
        position_today = sum(position.TodayPosition for position in position_list)
        position = sum(position.Position for position in position_list)
        position_yesterday = position - position_today
        if position_today > 0:
            self.trade_agent.close_today(instrument_id, posi_direction, position_today, limit_price=0,
                                         market_data=market_data)
        if position_yesterday > 0:
            self.trade_agent.close(instrument_id, posi_direction, position_yesterday, limit_price=0,
                                   market_data=market_data)

    def on_close_all(self, evt):
        # 全部撤单
        for order in sorted(self.trade_agent.order_dict.values(), key=attrgetter('InsertDate', 'InsertTime'), reverse=True):
            if order.OrderStatus not in [ApiStruct.OST_NoTradeQueueing, ApiStruct.OST_NoTradeNotQueueing]:
                continue
            self.trade_agent.refer(order.InstrumentID, order.ExchangeID, order.OrderSysID)
        time.sleep(0.1)

        # 全部清仓
        query_list = []
        for (instrument_id, posi_direction), position_list in self.trade_agent.position_dict.iteritems():
            if not position_list:
                continue
            market_data = self.md_agent.market_data_dict.get(instrument_id)
            if not market_data:
                query_list.append(((instrument_id, posi_direction), position_list))
                continue
            self.close_one(instrument_id, position_list, market_data)
        for (instrument_id, posi_direction), position_list in query_list:
            market_data = self.trade_agent.query_depth_market_data(instrument_id)
            if not market_data:
                continue
            self.close_one(instrument_id, position_list, market_data)
            time.sleep(1.1)

    def on_dialog_close(self, evt):
        self.Hide()


class TradeDialog(wx.Dialog):
    def __init__(self, parent, id, title, broker_id, user_id, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.DEFAULT_DIALOG_STYLE):
        pre = wx.PreDialog()
        pre.SetExtraStyle(wx.DIALOG_EX_CONTEXTHELP)
        pre.Create(parent, id, title, pos, size, style)

        self.PostCreate(pre)

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

        b4 = wx.StaticBox(self, -1, u'成交')
        bsizer4 = wx.StaticBoxSizer(b4, wx.VERTICAL)
        self.trade_dvlc = self.init_trade_dvlc()
        bsizer4.Add(self.trade_dvlc, 1, wx.EXPAND)

        sizer.Add(bsizer4, 1, wx.EXPAND)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Bind(wx.EVT_CLOSE, self.on_dialog_close)

    def init_trade_dvlc(self):
        dvlc = dv.DataViewListCtrl(self, size=(600, 400), style=wx.BORDER_THEME
                                   | dv.DV_ROW_LINES
                                   #| dv.DV_HORIZ_RULES
                                   | dv.DV_VERT_RULES
                                   | dv.DV_MULTIPLE
                                   )
        dvlc.AppendTextColumn(u'合约', width=60)
        dvlc.AppendTextColumn(u'开平', width=60)
        dvlc.AppendTextColumn(u'成交价格', width=60)
        dvlc.AppendTextColumn(u'成交手数', width=60)
        dvlc.AppendTextColumn(u'成交时间', width=120)
        dvlc.AppendTextColumn(u'成交编号', width=80)
        dvlc.AppendTextColumn(u'报单编号', width=80)
        return dvlc

    def on_dialog_close(self, evt):
        self.Hide()


class OrderDialog(wx.Dialog):
    def __init__(self, parent, id, title, broker_id, user_id, panel, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.DEFAULT_DIALOG_STYLE):
        pre = wx.PreDialog()
        pre.SetExtraStyle(wx.DIALOG_EX_CONTEXTHELP)
        pre.Create(parent, id, title, pos, size, style)

        self.PostCreate(pre)

        self.panel = panel
        self.trade_agent = panel.trade_agent
        self.md_agent = panel.md_agent

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
        self.b_refer_all = wx.Button(self, -1, u'全部撤单', (50, -1))
        box.Add(self.b_refer_all, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.GROW | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        b3 = wx.StaticBox(self, -1, u'报单')
        bsizer3 = wx.StaticBoxSizer(b3, wx.VERTICAL)
        self.order_dvlc = self.init_order_dvlc()
        bsizer3.Add(self.order_dvlc, 1, wx.EXPAND)

        sizer.Add(bsizer3, 1, wx.EXPAND)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Bind(wx.EVT_BUTTON, self.on_refer_all, self.b_refer_all)
        self.Bind(wx.EVT_CLOSE, self.on_dialog_close)

    def init_order_dvlc(self):
        dvlc = dv.DataViewListCtrl(self, size=(600, 400), style=wx.BORDER_THEME
                                   | dv.DV_ROW_LINES
                                   #| dv.DV_HORIZ_RULES
                                   | dv.DV_VERT_RULES
                                   | dv.DV_MULTIPLE
                                   )
        dvlc.AppendTextColumn(u'合约', width=60)
        dvlc.AppendTextColumn(u'开平', width=60)
        dvlc.AppendTextColumn(u'报单价格', width=60)
        dvlc.AppendTextColumn(u'报单手数', width=60)
        dvlc.AppendTextColumn(u'未成交数', width=60)
        dvlc.AppendTextColumn(u'报单时间', width=120)
        dvlc.AppendTextColumn(u'报单状态', width=60)
        dvlc.AppendTextColumn(u'报单编号', width=80)
        return dvlc

    def on_refer_all(self, evt):
        for order in sorted(self.trade_agent.order_dict.values(), key=attrgetter('InsertDate', 'InsertTime'), reverse=True):
            if order.OrderStatus not in [ApiStruct.OST_NoTradeQueueing, ApiStruct.OST_NoTradeNotQueueing]:
                continue
            self.trade_agent.refer(order.InstrumentID, order.ExchangeID, order.OrderSysID)

    def on_dialog_close(self, evt):
        self.Hide()


class TraderPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.broker_id = ''
        self.user_id = ''
        self.market_data_dlg = None
        self.position_dlg = None
        self.trade_dlg = None
        self.order_dlg = None
        self.tactics_dlg_dict = {}

    def init_layout(self, broker_id, user_id, instrument_ids):
        self.broker_id = broker_id
        self.user_id = user_id

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

        box = wx.BoxSizer(wx.HORIZONTAL)
        b_market_data = wx.Button(self, -1, u'行情', (50, -1))
        b_position = wx.Button(self, -1, u'持仓', (50, -1))
        b_trade = wx.Button(self, -1, u'成交', (50, -1))
        b_order = wx.Button(self, -1, u'报单', (50, -1))
        box.Add(b_market_data, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        box.Add(b_position, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        box.Add(b_trade, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        box.Add(b_order, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.EXPAND, 5)

        box = wx.BoxSizer(wx.HORIZONTAL)
        l1 = wx.StaticText(self, -1, u'合约:', (40, -1))
        # This combobox is created with a preset list of values.
        self.instrument_id = cb = wx.ComboBox(self, -1, u'', (50, -1),
                                             (100, -1), instrument_ids,
                                             wx.CB_DROPDOWN
                                             #| wx.TE_PROCESS_ENTER
                                             #| wx.CB_SORT
                                             )
        b_statics = wx.Button(self, -1, u'策略', (50, -1))
        box.Add(l1, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        box.Add(cb, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        box.Add(b_statics, 0, wx.ALIGN_CENTRE | wx.ALL, 5)
        sizer.Add(box, 0, wx.EXPAND, 5)

        self.message = tc = wx.TextCtrl(self, -1, '', size=(400, 100), style=wx.TE_MULTILINE|wx.TE_PROCESS_ENTER|wx.TE_READONLY)
        # lp = self.t5.GetLastPosition()
        tc.SetInsertionPoint(0)

        bbox = wx.BoxSizer(wx.HORIZONTAL)
        bbox.Add(tc, 1, wx.EXPAND)

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(sizer, 0, wx.EXPAND)
        self.Sizer.Add(bbox, 1, wx.EXPAND)

        self.Bind(wx.EVT_BUTTON, self.on_market_data, b_market_data)
        self.Bind(wx.EVT_BUTTON, self.on_position, b_position)
        self.Bind(wx.EVT_BUTTON, self.on_trade, b_trade)
        self.Bind(wx.EVT_BUTTON, self.on_order, b_order)
        self.Bind(wx.EVT_BUTTON, self.on_statics, b_statics)

    def init(self, td_front, md_front, broker_id, user_id, password, instrument_ids):
        self.trade_agent = TradeAgent(td_front, broker_id, user_id, password)
        self.md_agent = MdAgent(md_front, broker_id, user_id, password)
        self.trade_agent.callback = self.process_trade_agent_data

        self.market_data_dlg = MarketDataDialog(None, -1, u'行情', broker_id, user_id, size=(600, -1))
        self.position_dlg = PositionDialog(None, -1, u'持仓', broker_id, user_id, self, size=(600, -1))
        self.trade_dlg = TradeDialog(None, -1, u'成交', broker_id, user_id, size=(600, -1))
        self.order_dlg = OrderDialog(None, -1, u'报单', broker_id, user_id, self, size=(600, -1))

        self.load_data(instrument_ids)
        self.init_timer()
        # thread = Thread(target=self.thread_load_data, args=(instrument_ids,))
        # thread.start()

    def load_data(self, instrument_ids):
        if self.trade_agent.ready():
            self.write_message(u'交易服务连接成功.')
        else:
            self.write_message(u'交易服务连接失败')
            return

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

        self.set_data()
        self.write_message(u'数据加载完成')

    def init_timer(self):
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.t1 = wx.Timer(self, id=1)
        self.t1.Start(500)
        self.t2 = wx.Timer(self, id=2)
        self.t2.Start(5000)
        self.t3 = wx.Timer(self, id=3)
        wx.CallLater(2000, lambda: self.t3.Start(5000))

    def on_timer(self, evt):
        id = evt.GetTimer().GetId()
        if id == 1:
            self.set_market_data(self.md_agent.market_data_dict)
        elif id == 2:
            self.trade_agent.query_position()
            self.set_position(self.trade_agent.position_dict)

        elif id == 3:
            self.trade_agent.query_trading_account()
            self.set_account(self.trade_agent.trading_account)

    def get_self_position(self):
        self_position_dict = {}
        for (instrument_id, posi_direction), position_list in self.trade_agent.position_dict.iteritems():
            if position_list:
                self_position_dict[(instrument_id, posi_direction)] = {
                    'instrument_id': position_list[0].InstrumentID,
                    'posi_direction': position_list[0].PosiDirection,
                    'position': sum(position.Position for position in position_list),
                    'today_position': sum(position.TodayPosition for position in position_list),
                    'open_volume': sum(position.OpenVolume for position in position_list),
                    'close_volume': sum(position.CloseVolume for position in position_list),
                    'position_profit': sum(position.PositionProfit for position in position_list),
                    'close_profit': sum(position.CloseProfit for position in position_list),
                }
        return self_position_dict

    def set_data(self):
        self.set_account(self.trade_agent.trading_account)
        self.set_position(self.trade_agent.position_dict)
        self.set_order(self.trade_agent.order_dict)
        self.set_trade(self.trade_agent.trade_dict)

    def set_market_data(self, market_data_dict):
        if market_data_dict is not None and self.market_data_dlg:
            self._set_market_data(self.market_data_dlg.market_data_dvlc, market_data_dict)
        for instrument_id, market_data in market_data_dict.iteritems():
            if instrument_id in self.tactics_dlg_dict:
                self.tactics_dlg_dict[instrument_id].process_market_data(market_data)

    def set_account(self, trading_account):
        if trading_account is not None and self.position_dlg:
            self._set_account(self.position_dlg.account_dvlc, trading_account)

    def set_position(self, position_dict):
        if position_dict is not None and self.position_dlg:
            self._set_position(self.position_dlg.position_dvlc, position_dict)

    def set_trade(self, trade_dict):
        if trade_dict is not None and self.trade_dlg:
            self._set_trade(self.trade_dlg.trade_dvlc, trade_dict)

    def set_order(self, order_dict):
        if order_dict is not None and self.order_dlg:
            self._set_order(self.order_dlg.order_dvlc, order_dict, no_trade=True)

    @classmethod
    def _set_position(cls, dvlc, position_dict):
        dvlc.DeleteAllItems()
        for position_list in position_dict.values():
            if position_list:
                if isinstance(position_list[0], ApiStruct.InvestorPosition):

                    dvlc.AppendItem([
                        position_list[0].InstrumentID,
                        common.desc_posi_direction(position_list[0].PosiDirection),
                        sum(position.Position for position in position_list),
                        sum(position.TodayPosition for position in position_list),
                        sum(position.OpenVolume for position in position_list),
                        sum(position.CloseVolume for position in position_list),
                        sum(position.PositionProfit for position in position_list),
                        sum(position.CloseProfit for position in position_list),
                    ])

    @classmethod
    def _set_account(cls, dvlc, account):
        dvlc.DeleteAllItems()
        dvlc.AppendItem([
            account.PreBalance,
            account.Balance,
            account.Available,
            account.CurrMargin,
            account.PositionProfit,
            account.CloseProfit,
            account.Commission,
        ])

    @classmethod
    def _set_trade(cls, dvlc, trade_dict):
        dvlc.DeleteAllItems()
        for trade in sorted(trade_dict.values(), key=attrgetter('TradeDate', 'TradeTime'), reverse=True):
            dvlc.AppendItem([
                trade.InstrumentID,
                common.desc_direction(trade.Direction, trade.OffsetFlag),
                trade.Price,
                trade.Volume,
                trade.TradeDate + ' ' + trade.TradeTime,
                trade.TradeID,
                trade.OrderSysID,
            ])

    @classmethod
    def _set_order(cls, dvlc, order_dict, no_trade=False):
        dvlc.DeleteAllItems()
        for order in sorted(order_dict.values(), key=attrgetter('InsertDate', 'InsertTime'), reverse=True):
            if no_trade and order.OrderStatus not in [ApiStruct.OST_NoTradeQueueing, ApiStruct.OST_NoTradeNotQueueing]:
                continue
            dvlc.AppendItem([
                order.InstrumentID,
                common.desc_direction(order.Direction, order.CombOffsetFlag),
                order.LimitPrice,
                order.VolumeTotalOriginal,
                order.VolumeTotal,
                order.InsertDate + ' ' + order.InsertTime,
                common.desc_order_status(order.OrderStatus),
                order.OrderSysID,
            ])

    @classmethod
    def _set_market_data(cls, dvlc, market_data_dict):
        dvlc.DeleteAllItems()
        for data in market_data_dict.values():
            dvlc.AppendItem([
                data.InstrumentID,
                data.LastPrice,
                data.BidPrice1,
                data.AskPrice1
            ])
            dvlc.AppendItem([
                '',
                '',
                data.BidVolume1,
                data.AskVolume1
            ])

    def on_market_data(self, evt):
        self.market_data_dlg.Show()

    def on_position(self, evt):
        self.position_dlg.Show()

    def on_trade(self, evt):
        self.trade_dlg.Show()

    def on_order(self, evt):
        self.order_dlg.Show()

    def on_statics(self, evt):
        instrument_id = self.instrument_id.GetValue()
        if not instrument_id:
            return
        instrument = self.trade_agent.instrument_dict.get(instrument_id)
        if not instrument:
            self.write_message(u'该合约数据未加载，无法开启策略')
            return
        if instrument_id not in self.tactics_dlg_dict:
            statics_dlg = TacticsDialog(None, -1, u'策略-' + instrument_id, self.broker_id, self.user_id, instrument, self, size=(200, 100))
            self.tactics_dlg_dict[instrument_id] = statics_dlg
        self.tactics_dlg_dict[instrument_id].Show()

    def write_message(self, msg):
        self.message.SetInsertionPoint(-1)
        self.message.WriteText(datetime.datetime.now().strftime('%H:%M:%S') + ' ' + msg)
        self.message.WriteText('\n')

    def process_trade_agent_data(self, data):
        if isinstance(data, ApiStruct.Order):
            self.process_tactics_order(data)
            self.write_message(data.StatusMsg)
            self.set_order(self.trade_agent.order_dict)
        elif isinstance(data, ApiStruct.Trade):
            self.process_tactics_trade(data)
            self.set_trade(self.trade_agent.trade_dict)
            self.trade_agent.query_position()
            self.set_position(self.trade_agent.position_dict)

    def process_tactics_order(self, data):
        instrument_id = data.InstrumentID
        if instrument_id and instrument_id in self.tactics_dlg_dict:
            self.tactics_dlg_dict[instrument_id].process_order(data)

    def process_tactics_trade(self, data):
        instrument_id = data.InstrumentID
        if instrument_id and instrument_id in self.tactics_dlg_dict:
            self.tactics_dlg_dict[instrument_id].process_trade(data)


class TraderApp(wx.App):
    def __init__(self, redirect=False, filename=None):
        wx.App.__init__(self, redirect, filename)
        self.login_dlg = LoginDialog(None, -1, u'登录', size=(600, 300))
        self.frame = wx.Frame(None, wx.ID_ANY, title='Main', size=(400, 300), style=wx.DEFAULT_FRAME_STYLE)
        self.panel = TraderPanel(self.frame)

if __name__ == '__main__':
    app = TraderApp()
    app.login_dlg.CenterOnScreen()
    # this does not return until the dialog is closed.
    val = app.login_dlg.ShowModal()
    if val == wx.ID_OK:
        td_front = app.login_dlg.t_td_front.GetValue()
        md_front = app.login_dlg.t_md_front.GetValue()
        broker_id = app.login_dlg.t_broker_id.GetValue()
        user_id = app.login_dlg.t_user_id.GetValue()
        password = app.login_dlg.t_password.GetValue()
        instrument_ids = app.login_dlg.t_instrument_ids.GetValue().split(',')
        instrument_ids = [inst_id.strip() for inst_id in instrument_ids]
        print td_front, md_front, broker_id, user_id, password, instrument_ids

        app.panel.init_layout(broker_id, user_id, instrument_ids)
        app.frame.Show()
        app.panel.init(td_front, md_front, broker_id, user_id, password, instrument_ids)
        app.MainLoop()

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


