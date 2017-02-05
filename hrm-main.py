"""
    Code based on:
        https://github.com/mvillalba/python-ant/blob/develop/demos/ant.core/03-basicchannel.py
    in the python-ant repository and
        https://github.com/tomwardill/developerhealth
    by Tom Wardill
"""
import sys
import time
from ant.core import driver, node, event, message, log
from ant.core.constants import CHANNEL_TYPE_TWOWAY_RECEIVE, TIMEOUT_NEVER
import usb.core
import redis


class HRM(event.EventCallback):

    def __init__(self, serial, netkey):
        self.serial = serial
        self.netkey = netkey
        self.antnode = None

        self.channel1 = None
        self.channel2 = None

        self.bpm1 = 0
        self.bpm2 = 0
        
        self.bpm1upd = 0
        self.bpm2upd = 0


    def start(self):
        print("starting node")
        self._start_antnode()
        self._setup_channels()
        self.channel1.registerCallback(self)
        self.channel2.registerCallback(self)
        print("start listening for hr events")

    def stop(self):
        print("Stopping channels and node")
        if self.channel2:
            self.channel2.close()
            self.channel2.unassign()
        if self.channel1:
            self.channel1.close()
            self.channel1.unassign()
        if self.antnode:
            self.antnode.stop()

    def __enter__(self):
        return self

    def __exit__(self, type_, value, traceback):
        self.stop()

    def _start_antnode(self):
        stick = driver.USB2Driver(self.serial)
        self.antnode = node.Node(stick)
        self.antnode.start()

    def _setup_channels(self):
        key = node.NetworkKey('N:ANT+', self.netkey)
        self.antnode.setNetworkKey(0, key)

        self.channel1 = self.antnode.getFreeChannel()
        self.channel1.name = 'C:HRM'
        self.channel1.assign('N:ANT+', CHANNEL_TYPE_TWOWAY_RECEIVE)
        self.channel1.setID(120, 0, 0)
        self.channel1.setSearchTimeout(TIMEOUT_NEVER)
        self.channel1.setPeriod(8070)
        self.channel1.setFrequency(57)
        self.channel1.open()

#        print "channel1 open"

        self.channel2 = self.antnode.getFreeChannel()
        self.channel2.name = 'C:HRM'
        self.channel2.assign('N:ANT+', CHANNEL_TYPE_TWOWAY_RECEIVE)
        self.channel2.setID(120, 0, 0)
        self.channel2.setSearchTimeout(TIMEOUT_NEVER)
        self.channel2.setPeriod(8070)
        self.channel2.setFrequency(57)
        self.channel2.open()
        
#        print "channel2 open"

    def process(self, msg):
        if isinstance(msg, message.ChannelBroadcastDataMessage):
            _chan = msg.getChannelNumber()
            _hr = ord(msg.payload[-1])
            print("%s heart rate on chan %d is %d" %(time.strftime("%Y-%m-%d %H:%M:%S"), _chan+1, _hr) )
            if (_chan==0):
                if (_hr != self.bpm1):
                  db.set('bpm.1.upd', time.time())
                  db.set('bpm.1.value', _hr);
                self.bpm1 = _hr;
                
            if (_chan==1):
                if (_hr != self.bpm2):
                  db.set('bpm.2.upd', time.time())
                  db.set('bpm.2.value', _hr);
                self.bpm2 = _hr;


#hrm settings
SERIAL = '/dev/null'
NETKEY = 'B9A521FBBD72C345'.decode('hex')

print "usbreset device"
dev = usb.core.find(idVendor=0x0fcf, idProduct=0x1008)
if dev is None:
  raise DriverError('Could not open device (not found)')
  
dev.reset();
time.sleep(0.5);

#redis
db = redis.StrictRedis(host='localhost', port=6379, db=0)

valid = 10 #time when not changing value is valid

with HRM(serial=SERIAL, netkey=NETKEY) as hrm:
    hrm.start()
    hrm.db = db
    while True:
        try:
            time.sleep(1)            
        except KeyboardInterrupt:
            sys.exit(0)
            