# coding=utf-8
import copy
import hashlib, os, tempfile
from ctp import ApiStruct, TraderApi


class MyTraderApi(TraderApi):
    def __init__(self, broker_id, user_id, password, rsp_qry_queue, data_queue):
        self.broker_id = broker_id
        self.user_id = user_id
        self.password = password
        self.rsp_qry_queue = rsp_qry_queue
        self.data_queue = data_queue
        self.ready = False
        self.user_login = None
        self.Create(broker_id, user_id)

    def Create(self, broker_id, user_id):
        dir = ''.join(('ctp.futures', broker_id, user_id))
        dir = hashlib.md5(dir).hexdigest()
        dir = os.path.join(tempfile.gettempdir(), dir, 'Trd') + os.sep
        print dir
        if not os.path.isdir(dir):
            os.makedirs(dir)
        super(MyTraderApi, self).Create(dir)

    def OnFrontConnected(self):
        print('OnFrontConnected: Login...')
        req = ApiStruct.ReqUserLogin(
            BrokerID=self.broker_id, UserID=self.user_id, Password=self.password)
        self.ReqUserLogin(req, 1)

    def OnFrontDisconnected(self, nReason):
        print 'OnFrontDisconnected', nReason
        self.ready = False

    def OnRspAuthenticate(self, pRspAuthenticate, pRspInfo, nRequestID, bIsLast):
        print 'OnRspAuthenticate:', nRequestID, bIsLast

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        print 'OnRspUserLogin:', pRspUserLogin, nRequestID, bIsLast, pRspInfo
        if pRspInfo and pRspInfo.ErrorID == 0:  # Success
            print 'GetTradingDay:', self.GetTradingDay()
            if pRspUserLogin:
                self.user_login = copy.deepcopy(pRspUserLogin)
                self.ready = True

    def OnRspSettlementInfoConfirm(self, pSettlementInfoConfirm, pRspInfo, nRequestID, bIsLast):
        print 'OnRspSettlementInfoConfirm', nRequestID, bIsLast, pRspInfo
        if pRspInfo and pRspInfo.ErrorID == 0:  # Success
            self.rsp_qry_queue.put((nRequestID, copy.deepcopy(pSettlementInfoConfirm), bIsLast))

    def OnErrRtnOrderInsert(self, pInputOrder, pRspInfo):
        print 'OnErrRtnOrderInsert', pInputOrder, pRspInfo

    def OnRspOrderInsert(self, pInputOrder, pRspInfo, nRequestID, bIsLast):
        print 'OnRspOrderInsert', pInputOrder, pRspInfo, nRequestID, bIsLast

    def OnRtnOrder(self, pOrder):
        print 'OnRtnOrder', pOrder, pOrder.StatusMsg
        self.data_queue.put(copy.deepcopy(pOrder))

    def OnRtnTrade(self, pTrade):
        print 'OnRtnTrade', pTrade
        self.data_queue.put(copy.deepcopy(pTrade))

    def OnRspQrySettlementInfo(self, pSettlementInfo, pRspInfo, nRequestID, bIsLast):
        # print 'OnRspQrySettlementInfo:', nRequestID, bIsLast
        self.rsp_qry_queue.put((nRequestID, copy.deepcopy(pSettlementInfo), bIsLast))

    def OnRspQrySettlementInfoConfirm(self, pSettlementInfoConfirm, pRspInfo, nRequestID, bIsLast):
        # print 'OnRspQrySettlementInfoConfirm:', pRspInfo, bIsLast
        self.rsp_qry_queue.put((nRequestID, copy.deepcopy(pSettlementInfoConfirm), bIsLast))

    def OnRspQryOrder(self, pOrder, pRspInfo, nRequestID, bIsLast):
        # print 'OnRspQryOrder:', nRequestID, bIsLast
        self.rsp_qry_queue.put((nRequestID, copy.deepcopy(pOrder), bIsLast))

    def OnRspQryTrade(self, pTrade, pRspInfo, nRequestID, bIsLast):
        # print 'OnRspQryTrade:', nRequestID, bIsLast
        self.rsp_qry_queue.put((nRequestID, copy.deepcopy(pTrade), bIsLast))

    def OnRspQryInvestorPosition(self, pInvestorPosition, pRspInfo, nRequestID, bIsLast):
        # print 'OnRspQryInvestorPosition:', nRequestID, bIsLast
        self.rsp_qry_queue.put((nRequestID, copy.deepcopy(pInvestorPosition), bIsLast))

    def OnRspQryInvestorPositionDetail(self, pInvestorPositionDetail, pRspInfo, nRequestID, bIsLast):
        # print 'OnRspQryInvestorPositionDetail:', nRequestID, bIsLast, pRspInfo
        self.rsp_qry_queue.put((nRequestID, copy.deepcopy(pInvestorPositionDetail), bIsLast))

    def OnRspQryTradingAccount(self, pTradingAccount, pRspInfo, nRequestID, bIsLast):
        # print 'OnRspQryTradingAccount:', nRequestID, bIsLast
        self.rsp_qry_queue.put((nRequestID, copy.deepcopy(pTradingAccount), bIsLast))

    def OnRspQryInstrument(self, pInstrument, pRspInfo, nRequestID, bIsLast):
        # print 'OnRspQryInstrument:', pInstrument, pRspInfo, nRequestID, bIsLast
        self.rsp_qry_queue.put((nRequestID, copy.deepcopy(pInstrument), bIsLast))

    def OnRspQryDepthMarketData(self, pDepthMarketData, pRspInfo, nRequestID, bIsLast):
        # print 'OnRspQryInstrument:', pDepthMarketData, pRspInfo, nRequestID, bIsLast
        self.rsp_qry_queue.put((nRequestID, copy.deepcopy(pDepthMarketData), bIsLast))

    def OnRtnInstrumentStatus(self, pInstrumentStatus):
        print 'OnRtnInstrumentStatus', pInstrumentStatus

    def OnRtnTradingNotice(self, pTradingNoticeInfo):
        print 'OnRtnTradingNotice', pTradingNoticeInfo

