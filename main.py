import threading
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.widgets import Button
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

class LiveSurface(EClient, EWrapper):
    
    def __init__(self):
        EClient.__init__(self, self)
        self.iv_dict = {}
        self.id_map = {}
        self.expirations = []
        self.strikes = []
        self.spot_price = 0
        self.underlying_conID = 0
        self.resolved = threading.Event()
        self.chained_resolved = threading.Event()
    
    def connectAck(self):
        print("Connected to TWS")
    
    def error(self, reqId, errorCode, errorString):
        if errorCode not in [2104, 2106, 2158]:  # Ignore connection status messages
            print(f"Error {errorCode}: {errorString}"+f" (Request ID: {reqId})")
    
    def contractDetails(self, reqId, contractDetails):
        self.underlying_conID = contractDetails.contract.conId
        self.resolved.set()
    
    def tickPrice
        