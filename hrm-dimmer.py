"""
    Code based on:
        https://github.com/mvillalba/python-ant/blob/develop/demos/ant.core/03-basicchannel.py
    in the python-ant repository and
        https://github.com/tomwardill/developerhealth
    by Tom Wardill
"""
import sys
import time
import serial
from ant.core import driver, node, event, message, log
from ant.core.constants import CHANNEL_TYPE_TWOWAY_RECEIVE, TIMEOUT_NEVER
import usb.core 


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
            print("%s heart rate on chan %d is %d" %(time.strftime("%Y-%m-%d %H:%M:%s"), _chan+1, _hr) )
            if (_chan==0):
                if (_hr != self.bpm1):
                  self.bpm1upd = time.time()
                self.bpm1 = _hr;
                
            if (_chan==1):
                if (_hr != self.bpm2):
                  self.bpm2upd = time.time()
                self.bpm2 = _hr;


def dimmer_set(channel, value):
    if channel>15:
        addr = 2;
        channel = channel-16;
    else:
        addr = 1;
        
    value = value & 0xFF

    crc = (0x0A + addr + value + channel) & 0xFF;

    data = chr(0x0A) + chr(addr) + chr(value) + chr(channel) + chr(0x00);
    data = chr(0xFF) + chr(0xFF) + data + chr(crc)

#    print '>> ' + data.encode('hex')
    ser.write(data)
    time.sleep(0.0050)
#    rep = ser.read(8)
#    time.sleep(0.0050)
#    print '<< ' + rep.encode('hex');

def trapezoid_level(t, dly, bright):
            dly_off = dly-t_pulse;
            dly_on  = t_pulse;

            level = -1

            #implement trapezoid pulse
            if (t < dly_off):	#not in pulse
              in_pulse = 0
              level = 0

            elif ((t > dly_off) and (t < dly)):	#in pulse on chan 1
              in_pulse = 1
              if (t < dly_off+t_ramp): #ramp
                  level = int( ( t - dly_off )/t_ramp * bright );
              elif (t > dly-t_decay):
                  level = int( (dly - t)/t_decay * bright );
              else:
                  level = bright
            
            return level



#hrm settings
SERIAL = '/dev/null'
NETKEY = 'B9A521FBBD72C345'.decode('hex')

print "usbreset device"
dev = usb.core.find(idVendor=0x0fcf, idProduct=0x1008)
if dev is None:
  raise DriverError('Could not open device (not found)')
  
dev.reset();
time.sleep(0.5);

#serial for dimmer
ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate=38400,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=0.1
)

ser.isOpen()
ser.read(10) 	# read end of buf with timeout

#options
t_pulse=0.200	# beat lenth
t_ramp=0.050
t_decay=0.050

cmdtime = 0.0054 #command length

#beat start time
t1=time.time(); #now
t2=t1;

bright1 = 64
bright2 = 64

level1 = 0
level2 = 0

#last output value and chan
chan=16+10
outlvl = -1

valid = 10 #time when not changing value is valid

with HRM(serial=SERIAL, netkey=NETKEY) as hrm:
    hrm.start()
    while True:
        try:
            now = time.time()
            if (hrm.bpm1 > 0 and hrm.bpm1upd + valid >= now):
              dly1 = 60.0/hrm.bpm1
              level1 = trapezoid_level(now-t1, dly1, bright1);
            else:
              level1 = 0
              dly1 = 60.0/85.0;
              

            if (hrm.bpm2 > 0 and hrm.bpm2upd + valid >= now):
              dly2 = 60.0/hrm.bpm2
              level2 = trapezoid_level(now-t2, dly2, bright1);  
            else:
              dly2 = 60.0/85.0;
              level2 = 0            
            

            lvl = max(level1,level2); #max

            if outlvl != lvl: 
              dimmer_set(chan, lvl);
              outlvl = lvl
            

            if (now-t1 > dly1):
              t1 = t1+dly1

            if (now-t2 > dly2):
              t2 = t2+dly2

            # fix time skew or fast forward
            if (now-t1 > 100 or now < t1):
              t1 = now

            if (now-t2 > 100 or now < t2):
              t2 = now

            time.sleep(0.002)
            
        except KeyboardInterrupt:
            sys.exit(0)
            