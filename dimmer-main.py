import sys
import time
import serial
import redis

import serial.tools.list_ports;

# detect proper port
port_found=0
port_dev=''
while port_found==0:
  for port in serial.tools.list_ports.comports():
    if port[1] == 'FT232R USB UART':
      port_found=1
      port_dev=port[0];

  if port_found==0:
    print "Could not find port with FT232R. Will retry. Available ports are:"
    for port in serial.tools.list_ports.comports():
      print "%s %s %s" % (port[0],port[1],port[2]);

    time.sleep(10)

print "Found port: %s" % (port_dev)

#serial for dimmer
ser = serial.Serial(
    port=port_dev,
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
    time.sleep(0.0060)
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

def pulse_dual_level(t, dly, bright, t_pulse, t_ramp, t_decay):
            t_pulse = 4*t_ramp;
            dly_off = dly-t_pulse;
            dly_on  = t_pulse;

            level = -3

            #implement trapezoid pulse
            if (t < dly_off):	#not in pulse
              in_pulse = 0
              level = 0

            elif ((t > dly_off) and (t < dly)):	#in pulse on chan 1
              in_pulse = 1
              if (t < dly_off+t_ramp): #ramp up
                  level = int( ( t - dly_off )/t_ramp * bright );
              elif (t < dly_off+2*t_ramp): #ramp down
                  level = int( ( dly_off + 2*t_ramp - t )/t_ramp * bright );
              elif (t < dly_off+3*t_ramp): #ramp up
                  level = int( ( t - dly_off - 2*t_ramp )/t_ramp * bright );
              elif (t < dly_off+4*t_ramp): #ramp down
                  level = int( ( dly_off + 4*t_ramp - t )/t_ramp * bright );
#              elif (t > dly-t_decay):
#                  level = int( (dly - t)/t_decay * bright );
              else:
                  level = 0
            
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
t_pulse_idle=1.000
t_ramp_idle=0.200
t_decay_idle=0.300

#delay_idle not used for pulse_dual

#t_pulse_idle=3.000
#t_ramp_idle=1.000
#t_decay_idle=1.000

cmdtime = 0.0054 #command length

#beat start time
t1=time.time(); #now
t2=t1;
t_idle = t1;

bpm_idle = 24.0

level1 = 0
level2 = 0

#last output value and chan
chan_a=16+10
chan_b=10
outlvl = -1

valid = 5 #time when not changing value is valid

while True:
        try:
            # fetch from redis
            try:
              bpm1 = int(db.get('bpm.1.value'))
              bpm1upd = float(db.get('bpm.1.upd'))
            except:
              bpm1 = 0
              bpm1upd = 0
              
            try:
              bpm2 = int(db.get('bpm.2.value'))
              bpm2upd = float(db.get('bpm.2.upd'))
            except:
              bpm2 = 0
              bpm2upd = 0

            try:              
              bright1 = float(db.get('bright.1'))
            except:
              bright1 = 255.0
              
            try:
              bright2 = float(db.get('bright.2'))
            except:
              bright2 = 255.0

            try:
              brightA = float(db.get('bright.a'))
            except:
              brightA = 255.0

            try:
              brightB = float(db.get('bright.b'))
            except:
              brightB = 255.0

            try:
              bpm_idle = float(db.get('pulse.idle'))
            except:
              bpm_idle = 20.0

            if (bpm_idle<2.0):
              bpm_idle = 2.0

            try:
              bright_idle = float(db.get('bright.idle'))
            except:
              bright_idle = 255.0

            try:
              mode_a = int(db.get('mode.a'))
            except:
              mode_a = 0

            try:
              mode_b = int(db.get('mode.b'))
            except:
              mode_b = 0

            #go - hrm 1,2
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
            
            #idle chan
            dly_idle = 60.0/bpm_idle
            chan_idle = max(0,pulse_dual_level(now-t_idle, dly_idle, bright_idle, t_pulse_idle, t_ramp_idle, t_decay_idle));

            #idle if no hrm            
            if ( not (bpm2 > 0 and bpm2upd + valid >= now) and not (bpm1 > 0 and bpm1upd + valid >= now)):
              level_idle = chan_idle
            else:
              level_idle = 0

            #mix
            chan_hrm_idle = max(level1,level2,level_idle); #max
            chan_hrm = max(level1,level2);
            
            #channel modes
            if (mode_a == 0):
              chan_a_out = chan_hrm_idle;
            elif (mode_a == 1):
              chan_a_out = chan_idle;
            elif (mode_a == 2):
              chan_a_out = chan_hrm;
            elif (mode_a == 3):
              chan_a_out = 0;
            elif (mode_a == 4):
              chan_a_out = 255;

            if (mode_b == 0):
              chan_b_out = chan_hrm_idle;
            elif (mode_b == 1):
              chan_b_out = chan_idle;
            elif (mode_b == 2):
              chan_b_out = chan_hrm;
            elif (mode_b == 3):
              chan_b_out = 0;
            elif (mode_b == 4):
              chan_b_out = 255;
              
#            print "ma: %d, mb: %d, ba: %d, bb: %d, bi: %d, bpm1: %d (%f), bpm2: %d (%f), h1o: %d, h2o: %d, idle_out: %f, a: %d, b:%d, ci:%d" % (mode_a,mode_b,brightA,brightB,bright_idle,bpm1,bpm1upd,bpm2,bpm2upd,level1,level2,level_idle,chan_a_out,chan_b_out,chan_idle)

            #mix func
            #chan_hrm = max(level1,level2);

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

#            if outlvl != lvl: 
            dimmer_set(chan_a, int(chan_a_out*brightA/255.0));
            dimmer_set(chan_b, int(chan_b_out*brightB/255.0));
#            outlvl = lvl
            continue

            # 2ms
            time.sleep(0.002)
            
        except KeyboardInterrupt:
            sys.exit(0)
            