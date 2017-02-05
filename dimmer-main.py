import sys
import time
import serial
import redis

#serial for dimmer
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

#    print '>> ' + data.encode('hex')
    ser.write(data)
    time.sleep(0.0050)
#    rep = ser.read(8)
#    time.sleep(0.0050)
#    print '<< ' + rep.encode('hex');

def trapezoid_level(t, dly, bright, t_pulse, t_ramp, t_decay):
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


#redis
db = redis.StrictRedis(host='localhost', port=6379, db=0)

ser.isOpen()
ser.read(10) 	# read end of buf with timeout

#options
t_pulse=0.200	# beat lenth
t_ramp=0.050
t_decay=0.050

#idle
t_pulse_idle=0.500
t_ramp_idle=0.100
t_decay_idle=0.100

cmdtime = 0.0054 #command length

#beat start time
t1=time.time(); #now
t2=t1;
t_idle = t1;

bpm_idle = 40


try:
  bright1 = int(db.get('bright.1'));
except: 
  bright1 = 64
  
try:
  bright2 = int(db.get('bright.2'));
except: 
  bright2 = 64
  
try:
  bright_idle = int(db.get('bright.idle'))
except:
  bright_idle = 64

level1 = 0
level2 = 0

#last output value and chan
chan=16+10
outlvl = -1

valid = 10 #time when not changing value is valid

while True:
        try:
            # fetch from redis
            try:
              bpm1 = int(db.get('bpm.1.value'))
              bpm1upd = int(db.get('bpm.1.upd'))
            except:
              bpm1 = 0
              bpm1upd = 0
              
            try:
              bpm2 = int(db.get('bpm.2.value'))
              bpm2upd = int(db.get('bpm.2.upd'))
            except:
              bpm2 = 0
              bpm2upd = 0

            try:              
              bright1 = int(db.get('bright.1'))
            except:
              bright1 = 64
              
            try:
              bright2 = int(db.get('bright.2'))
            except:
              bright2 = 64


            #go
            now = time.time()
            if (bpm1 > 0 and bpm1upd + valid >= now):
              dly1 = 60.0/bpm1
              level1 = trapezoid_level(now-t1, dly1, bright1, t_pulse, t_ramp, t_decay);
            else:
              level1 = 0
              dly1 = 60.0/85.0;
              

            if (bpm2 > 0 and bpm2upd + valid >= now):
              dly2 = 60.0/bpm2
              level2 = trapezoid_level(now-t2, dly2, bright2, t_pulse, t_ramp, t_decay);  
            else:
              dly2 = 60.0/85.0;
              level2 = 0            
            
            #idle - no info
            dly_idle = 60.0/bpm_idle
            if ( not (bpm2 > 0 and bpm2upd + valid >= now) and not (bpm1 > 0 and bpm1upd + valid >= now)):
              dly_idle = 60.0/bpm_idle
              level_idle = trapezoid_level(now-t_idle, dly_idle, bright_idle, t_pulse_idle, t_ramp_idle, t_decay_idle);  
            else:
              level_idle = 0

            #mix func
            lvl = max(level1,level2,level_idle); #max

            if (now-t1 > dly1):
              t1 = t1+dly1

            if (now-t2 > dly2):
              t2 = t2+dly2

            if (now-t_idle > dly_idle):
              t_idle = t_idle+dly_idle

            # fix time skew or fast forward
            if (now-t1 > 100 or now < t1):
              t1 = now

            if (now-t2 > 100 or now < t2):
              t2 = now

            if (now-t_idle > 100 or now < t_idle):
              t_idle = now

            if outlvl != lvl: 
              dimmer_set(chan, lvl);
              outlvl = lvl
              continue

            # 2ms
            time.sleep(0.002)
            
        except KeyboardInterrupt:
            sys.exit(0)
            