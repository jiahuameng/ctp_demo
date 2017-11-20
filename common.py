# coding=utf-8
from ctp import ApiStruct


def desc_posi_direction(direction):
    posi_direction_dict = {
        ApiStruct.PD_Net: u'净',
        ApiStruct.PD_Long: u'多头',
        ApiStruct.PD_Short: u'空头',
    }
    return posi_direction_dict.get(direction, u'')


def desc_direction(direction, offset_flag):
    if direction == ApiStruct.D_Buy:
        if offset_flag in [ApiStruct.OF_Open]:
            return u'买开仓'
        elif offset_flag in [ApiStruct.OF_Close, ApiStruct.OF_CloseToday, ApiStruct.OF_CloseYesterday]:
            return u'买平仓'
        elif offset_flag in [ApiStruct.OF_ForceClose]:
            return u'买强平'
    elif direction == ApiStruct.D_Sell:
        if offset_flag in [ApiStruct.OF_Open]:
            return u'卖开仓'
        elif offset_flag in [ApiStruct.OF_Close, ApiStruct.OF_CloseToday, ApiStruct.OF_CloseYesterday]:
            return u'卖平仓'
        elif offset_flag in [ApiStruct.OF_ForceClose]:
            return u'卖强平'

    return u''


def desc_order_status(order_status):
    order_status_dict = {
        ApiStruct.OST_AllTraded: u'全部成交',
        ApiStruct.OST_PartTradedQueueing: u'部分成交',
        ApiStruct.OST_PartTradedNotQueueing: u'部分成交',
        ApiStruct.OST_NoTradeQueueing: u'未成交',
        ApiStruct.OST_NoTradeNotQueueing: u'未成交',
        ApiStruct.OST_Canceled: u'撤单',
        ApiStruct.OST_Unknown: u'未知',
        ApiStruct.OST_NotTouched: u'尚未触发',
        ApiStruct.OST_Touched: u'已触发',
    }
    return order_status_dict.get(order_status, u'')
