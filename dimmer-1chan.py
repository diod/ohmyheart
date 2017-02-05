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

#initial
bpm1=79		# beats per minute
bpm2=95

t_pulse=0.200	# beat lenth
t_ramp=0.050
t_decay=0.050

dly1 = 60.0/bpm1
dly2 = 60.0/bpm2

cmdtime = 0.0054 #command length

print("bpm1 = %d, delay1=%0.3f, bpm2 = %d, delay2=%0.3f" %(bpm1,dly1,bpm2,dly2))

dly1a = dly1-t_pulse;
dly1b = t_pulse-cmdtime

dly2a = dly2-t_pulse;
dly2b = t_pulse-cmdtime


#beat start time
t1=time.time(); #now
t2=t1;

in_pulse1 = 0
in_pulse2 = 0

bright1 = 64
bright2 = 64

level1 = 0
level2 = 0

chan=16+10

outlvl = -1

while True:
    try:
        #update delays
        dly1 = 60.0/bpm1
        dly2 = 60.0/bpm2
        
        dly1a = dly1-t_pulse;
        dly1b = t_pulse-cmdtime

        dly2a = dly2-t_pulse;
        dly2b = t_pulse-cmdtime

        #implement trapezoid pulse
        now = time.time()
        if (now-t1 < dly1a):
          in_pulse1 = 0
          level1 = 0
        
        if (now-t2 < dly2a):
          in_pulse2 = 0
          level2 = 0

        if ((now-t1 > dly1a) and (now-t1 < dly1)):	#in pulse on chan 1
          in_pulse1 = 1
          if (now-t1 < dly1a+t_ramp): #ramp
            level1 = int( ( (now-t1) - dly1a )/t_ramp * bright1 );
          elif (now-t1 > dly1-t_decay):
            level1 = int( (dly1 - (now-t1))/t_decay * bright1 );
          else:
            level1 = bright1


        if ((now-t2 > dly2a) and (now-t2 < dly2)):	#in pulse on chan 2
          in_pulse2 = 2
          if (now-t2 < dly2a+t_ramp): #ramp
            level2 = int( ( (now-t2) - dly2a )/t_ramp * bright2 );
          elif (now-t2 > dly2-t_decay):
            level2 = int( (dly2 - (now-t2))/t_decay * bright2 );
          else:
            level2 = bright2
            

        lvl = max(level1,level2); #max

        if outlvl != lvl: 
          dimmer_set(chan, lvl);
          outlvl = lvl
            

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
        
