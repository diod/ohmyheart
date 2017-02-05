import sys
import time
import serial

# configure the serial connections (the parameters differs on the device you are connecting to)
ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate=38400,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=0.1
)


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

    print '>> ' + data.encode('hex')
    ser.write(data)
    time.sleep(0.0050)
#    rep = ser.read(8)
#    time.sleep(0.0050)
#    print '<< ' + rep.encode('hex');


ser.isOpen()
ser.read(10) 	# read end of buf with timeout

print 'Enter your commands below.\nCtrl-C to leave the application.'


bpm1=79		# beats per minute
bpm2=95
dl=0.100	# beat lenth 50ms

dly1 = 60.0/bpm1
dly2 = 60.0/bpm2

cmdtime = 0.0054 #command length

print("bpm1 = %d, delay1=%0.3f, bpm2 = %d, delay2=%0.3f" %(bpm1,dly1,bpm2,dly2))

dly1a = dly1-dl-cmdtime;
dly1b = dl-cmdtime

dly2a = dly2-dl-cmdtime;
dly2b = dl-cmdtime


#beat start time
t1=time.time(); #now
t2=t1;

b1=0	# led off
b2=0

chan1=16+8
chan2=16+9

while True:
    try:
        #determine next event
        now = time.time()
        if (now-t1 < dly1a):
          if (b1==1):
              b1=0
              dimmer_set(chan1, 0);
        
        if (now-t2 < dly2a):
          if (b2==1):
              b2=0
              dimmer_set(chan2, 0);
     
        if ((now-t1 > dly1a) and (now-t1 < dly1)):	#in pulse on chan 1
          if (b1==0):
              b1=1
              dimmer_set(chan1, 255);

        if ((now-t2 > dly2a) and (now-t2 < dly2)):	#in pulse on chan 2
          if (b2==0):
              b2=1
              dimmer_set(chan2, 255);
            
        if (now-t1 > dly1):
            t1 = t1+dly1

        if (now-t2 > dly2):
            t2 = t2+dly2

        if (now-t1 > 100):
            t1 = now

        if (now-t2 > 100):
            t2 = now

        time.sleep(0.001)

#        print("sleep1: %0.4f, dimmer1: %0.4f, sleep2: %0.4f, dimmer2: %0.4f total: %0.4f, expected=%0.4f" % (t2-t1,t3-t2,t4-t3,t5-t4,t5-t1,dly))
            
#        time.sleep(0.5)
#        i=i+128
#        print "."        
    except KeyboardInterrupt:
        sys.exit(0);
        
