import copy
import hashlib, os, sys, tempfile, time
from ctp import ApiStruct, MdApi


class MyMdApi(MdApi):
    def __init__(self, broker_id, user_id, password, data_queue):
        self.broker_id = broker_id
        self.user_id = user_id
        self.password = password
        self.data_queue = data_queue
        self.ready = False
        self.Create(broker_id, user_id)

    def Create(self, broker_id, user_id):
        dir = ''.join(('ctp.futures', broker_id, user_id))
        dir = hashlib.md5(dir).hexdigest()
        dir = os.path.join(tempfile.gettempdir(), dir, 'Md') + os.sep
        print dir
        if not os.path.isdir(dir):
            os.makedirs(dir)
        super(MyMdApi, self).Create(dir)

    def OnFrontConnected(self):
        print('OnFrontConnected: Login...')
        req = ApiStruct.ReqUserLogin(
            BrokerID=self.broker_id, UserID=self.user_id, Password=self.password)
        self.ReqUserLogin(req, 1)

    def OnFrontDisconnected(self, nReason):
        print('OnFrontDisconnected:', nReason)

    def OnHeartBeatWarning(self, nTimeLapse):
        print('OnHeartBeatWarning:', nTimeLapse)

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        print 'OnRspUserLogin:', nRequestID, bIsLast, pRspInfo
        if pRspInfo and pRspInfo.ErrorID == 0:  # Success
            print 'GetTradingDay:', self.GetTradingDay()
            self.ready = True
        # print('OnRspUserLogin:', pRspInfo)
        # if pRspInfo.ErrorID == 0: # Success
        #     print('GetTradingDay:', self.GetTradingDay())
        #     self.SubscribeMarketData(self.instrumentIDs)

    def OnRspSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
        print('OnRspSubMarketData:', pRspInfo)

    def OnRspUnSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
        print('OnRspUnSubMarketData:', pRspInfo)

    def OnRspError(self, pRspInfo, nRequestID, bIsLast):
        print('OnRspError:', pRspInfo)

    def OnRspUserLogout(self, pUserLogout, pRspInfo, nRequestID, bIsLast):
        print('OnRspUserLogout:', pRspInfo)

    def OnRtnDepthMarketData(self, pDepthMarketData):
        # print('OnRtnDepthMarketData:', pDepthMarketData)
        if pDepthMarketData:
            self.data_queue.put(copy.deepcopy(pDepthMarketData))


if __name__ == '__main__':
    broker_id = '9999'
    # user_id = '081458'
    # password = '8210213146'
    user_id = '081471'
    password = '135246'
    instrument_ids = ['rb1705', 'ag1702', 'm1705']
    md_front = 'tcp://180.168.146.187:10010'

    md = MyMdApi(broker_id, user_id, password, instrument_ids, None)
    md.RegisterFront(md_front)
    md.Init()
    md.Join()
