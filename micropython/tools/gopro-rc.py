#!/usr/bin/micropython
# https://github.com/KonradIT/goprowifihack for the Short Command codes (Under HERO3)
# https://github.com/theContentMint/GoProRemote for RC simulator
from __future__ import print_function
from struct import pack, unpack
from binascii import hexlify
import getopt, sys, socket

debug = 0
endian = 'big'
packet_fmt = '>QBH2s'
min_return = 14
max_return = 640
dst_port   = 8484
rcv_time   = 1

cameras = {
  'HD3.10': {
	'BU': { 0: '3/1s', 1: '5/1s', 2: '10/1s' },
	'FS': { 3: 25, 4: 30, 6: 50, 7: 60, 8: 100, 9: 120 },
	'PR': { 3: '5mp M', 4: '7mp W', 8: '10mp W' }, # Hidden modes 5: '5mp W', 6: '5mp M',
#	'VR': { 2: '720p30', 3: '720p60', 6: '1080p30' }, # unrealiable command for Hero 3+ Silver
	'VV': { 0: 'WVGA', 1: '720p', 2: '960p', 3: '1080p' },
	'valid': (
	  ( # NTSC
		(0, 7, 0), # WVGA-60 W
		(0, 9, 0), # WVGA-120 W
		(1, 4, 0), # 720-30 W
		(1, 7, 0), # 720-60 W
		(1, 9, 0), # 720-120 W
		(1, 4, 1), # 720-30 M
		(1, 7, 1), # 720-60 M
		(1, 9, 1), # 720-120 M
		(1, 4, 2), # 720-30 N
		(1, 7, 2), # 720-60 N
		(1, 9, 2), # 720-120 N
		(2, 4, 0), # 960-30 W
		(2, 7, 0), # 960-60 W
		(3, 4, 0), # 1080-30 W
		(3, 7, 0), # 1080-60 W
		(3, 4, 1), # 1080-30 M
		(3, 7, 1), # 1080-60 M
		(3, 4, 2), # 1080-30 N
		(3, 7, 2), # 1080-60 N
	  ), ( # PAL
		(0, 6, 0), # WVGA-50 W
		(0, 8, 0), # WVGA-100 W
		(1, 3, 0), # 720-25 W
		(1, 6, 0), # 720-50 W
		(1, 8, 0), # 720-100 W
		(1, 3, 1), # 720-25 M
		(1, 6, 1), # 720-50 M
		(1, 8, 1), # 720-100 M
		(1, 3, 2), # 720-25 N
		(1, 6, 2), # 720-30 N
		(1, 8, 2), # 720-100 N
		(2, 3, 0), # 960-25 W
		(2, 6, 0), # 960-50 W
		(3, 3, 0), # 1080-25 W
		(3, 6, 0), # 1080-50 W
		(3, 3, 1), # 1080-25 M
		(3, 6, 1), # 1080-50 M
		(3, 3, 2), # 1080-25 N
		(3, 6, 2), # 1080-50 N
	  ),
	),
  },
}

cmd_check = {
  'cv': [ 0b11111110, 0b00000000, 0, {}, 'Camera Version' ],
  'lc': [ 0b00000001, 0b00000001, 0, { 5: 'reserved' }, 'Get on screen display' ], 
  'se': [ 0b11111110, 0b00000000, 0, {}, 'Session info' ],
  'st': [ 0b11111110, 0b00000000, 0, {}, 'Camera status' ],
  'sx': [ 0b11111110, 0b00000000, 0, {}, 'Settings' ],
  'wt': [ 0b11111110, 0b00000000, 0, {}, 'Wifi check' ],
#  'DA': [ 0b00000001, 0b00000000, 0, {}, 'Delete all - purposely excluded' ],
  'DL': [ 0b00000001, 0b00000000, 0, {}, 'Delete last' ],
#  'OO': [ 0b00000001, 0b00000000, 1, { 0: 'off', 1: 'on' }, 'Unknown acceptable command' ],
# Following set commands can be executed as get commands with no parameter when lower-cased 
  'AO': [ 0b00000001, 0b00000000, 1,
	  { 0: 'never', 1: '1m', 2: '2m', 3: '5m' }, 'Auto poweroff' ],
  'BS': [ 0b00000001, 0b00000000, 1, { 0: 'none', 1: '70%', 2: 'full' }, 'Set audible alert' ],
  'BU': [ 0b00000001, 0b00000000, 1, {}, 'Set burst rate' ],
  'CS': [ 0b00000001, 0b00000000, 1,
	  { 0: 'single', 3: '3/s', 5: '5/s', 10: '10/s' },
	  'Set continuous shot rate' ],
  'CM': [ 0b00000001, 0b00000000, 1,
	  { 0: 'video', 1: 'photo', 2: 'burst', 3: 'timelapse', 7: 'settings' }, 'Change mode' ],
  'DM': [ 0b00000001, 0b00000000, 1,
	  { 0: 'video', 1: 'photo', 2: 'burst', 3: 'timelapse' }, 'Default mode' ],
  'EX': [ 0b00000001, 0b00000000, 1, { 0: 'off', 1: 'on' }, 'Spot meter' ],
  'FS': [ 0b00000001, 0b00000000, 1, {}, 'Framerate' ],
  'FV': [ 0b00000001, 0b00000000, 1,
	  { 0: 'wide', 1: 'medium', 2: 'narrow' }, 'Set field of view' ],
  'LB': [ 0b00000001, 0b00000000, 1, { 0: '0', 1: '2', 2: '4' }, 'Set LED' ],
  'LL': [ 0b00000001, 0b00000000, 1, { 0: 'off', 1: 'on' }, 'Camera locator' ],
  'LO': [ 0b00000001, 0b00000000, 1,
	  { 0: 'none', 1: '5m', 2: '20m', 3: '1h', 4: '2h', 5: 'max' },
	  'Set loop interval' ],
  'OB': [ 0b00000001, 0b00000000, 1, { 0: 'off', 1: 'on' }, 'One button mode' ],
#  'OS': [ 0b00000001, 0b00000000, 1, { 0: 'off', 1: 'on' }, 'On screen display - no effect' ],
  'PR': [ 0b00000001, 0b00000000, 1, {}, 'Set photo resolution' ],
# Webserver not running in RC mode so preview images not accessible externally
  'PV': [ 0b00000001, 0b00000000, 1, { 0: 'off', 1: 'on', 2: 'rolling' }, 'Preview' ],
  'PW': [ 0b00000001, 0b00000001, 1, { 0: 'off', 1: 'on', 2: 'mode' }, 'Power/mode' ],
  'SH': [ 0b00000001, 0b00000000, 1, { 0: 'stop', 2: 'start' }, 'Shutter' ],
  'TI': [ 0b00000001, 0b00000000, 1,
	  { 0: '1/2s', 1: '1s', 2: '2s', 5: '5s', 10: '10s', 30: '30s', 60: '60s' },
	  'Set timelapse interval' ],
  'TM': [ 0b00000001, 0b00000000, 6, {}, 'Set date and time' ],
  'UP': [ 0b00000001, 0b00000000, 1, { 0: 'normal', 1: 'inverted' }, 'Set orientation' ],
  'VM': [ 0b00000001, 0b00000000, 1, { 0: 'ntsc', 1: 'pal' }, 'Video mode' ],
#  'VR': [ 0b00000001, 0b00000000, 1, {}, 'Video resolution' ],
  'VV': [ 0b00000001, 0b00000000, 1, {}, 'Vertical resolution' ],
}

def bytes2int(input):
  return int.from_bytes(input, endian)
#  fmt = 'B'
#  if 2 == len(input):
#    fmt = '>H'
#  elif 4 == len(input):
#    fmt = '>L'
#  elif 8 == len(input):
#    fmt = '>Q'
#  return unpack(fmt,input)[0]

def hexprt(input, sep=''):
  return hexlify(input, sep)
#  return sep.join('{:02x}'.format(ord(c)) for c in input)

def usage():
  print ('Usage: %s [options] host [port]' % sys.argv[0], file=sys.stderr)
  print ('Default port is %d, specify no command to start interactive mode' % dst_port, file=sys.stderr)
  print ('   -h, --help', file=sys.stderr)
  print ('           Print this help', file=sys.stderr)
  print ('   -b, --bcast', file=sys.stderr)
  print ('           Enable broadcast mode', file=sys.stderr)
  print ('   -c, --cmd=CMD', file=sys.stderr)
  print ('           Set output command to CMD (default: cv)', file=sys.stderr)
  print ('   -d, --debug=LEVEL', file=sys.stderr)
  print ('           Set debugging level')
  print ('   -f, --flag', file=sys.stderr)
  print ('           Turn on output flag (default: off)', file=sys.stderr)
  print ('   -i, --id=MSGID', file=sys.stderr)
  print ('           Set output message ID to MSGID (default: 0)', file=sys.stderr)
  print ('   -v, --val=VAL', file=sys.stderr)
  print ('           Set command argument to VAL', file=sys.stderr)
  print ('   -w, --wait=VAL', file=sys.stderr)
  print ('           Set receive timeout to VAL in seconds (default: %d)' % rcv_time, file=sys.stderr)

def button_decode(msg, flag):
  return (bytes2int(msg),)

def datetime_decode(msg, flag):
  year = bytes2int(msg[0:1])
  month = bytes2int(msg[1:2])
  day = bytes2int(msg[2:3])
  hour = bytes2int(msg[3:4])
  minute = bytes2int(msg[4:5])
  second = bytes2int(msg[5:6])
  return (year, month, day, hour, minute, second)

# Hero 3+ Silver is only 60 pixels wide
def lcd_decode(msg, flag):
  recv = bytes2int(msg[0:1])
  msg = msg[1:]
  if not recv in cmd_check['lc'][3]:
    raise ValueError('Unsupported return value %d from command lc' % recv)
# BEGIN - Actual printing of LCD
  n = 8
  s = len(msg) - n
  while s > 0:
#    print (bytes2int(msg[s:s+n]).format('064b'))
    print ('{:03x} {:032b}{:016b}{:08b}{:04b}'.format(s-n,
	  bytes2int(msg[s:s+4]), bytes2int(msg[s+4:s+6]),
	  bytes2int(msg[s+6:s+7]), bytes2int(msg[s+7:s+n]) >> 4
	))
    s -= n
# END - Actual printing of LCD
  return (recv, )

def session_decode(msg, flag):
  if 0 == flag:
    return ( unpack('B',msg), unpack('3B',msg[11:14]), unpack('2B',msg[28:30]) )
  elif 1 == flag:
    return unpack('>B2H6BH2B', msg)
  else:
    return tuple()

def status_decode(msg, flag):
  return unpack('4B',msg)

def ver_decode(msg, flag):
  if 0 == flag:
    len_ver = bytes2int(msg[2:3])
    len_model = bytes2int(msg[3+len_ver:4+len_ver])
    return tuple( list(unpack('2B',msg[0:2])) +
	  [ msg[3:9].decode('us-ascii'),
	    msg[10:3+len_ver].decode('us-ascii'),
	    msg[4+len_ver:].decode('us-ascii') ]
	)
  elif 1 == flag:
    len_name = bytes2int(msg[17:18])
    return (hexprt(msg[10:17],' '), msg[18:].decode('us-ascii'))
  else:
    return tuple()

cmd_decode = {
  'cv': ( ver_decode, ver_decode ),
  'lc': ( None, lcd_decode ),
  'pw': ( None, button_decode ),
  'se': ( session_decode, session_decode ),
  'SH': ( button_decode, ),
  'st': ( status_decode, ),
  'tm': ( datetime_decode, ),
}

def validate_cmd(cmd, args, flag):
  cmd_key = cmd.upper()
  argReq = 0
  if not cmd_key in cmd_check:
    cmd_key = cmd

  if not cmd_key in cmd_check:
    raise ValueError('Command %s is unsupported' % cmd)

  if cmd_key == cmd:
    argReq = cmd_check[cmd_key][2]

  if debug < 3 and flag & cmd_check[cmd_key][0] != cmd_check[cmd_key][1]:
    raise ValueError('Flag %d for command %s is unsupported' % (flag, cmd))
  nArgs = len(args)
  if nArgs != argReq:
    raise ValueError('Command %s required %d arguments (got %d)' % (cmd, cmd_check[cmd_key][2], nArgs))
  if debug <2 and 1 == nArgs:
    if not args[0] in cmd_check[cmd_key][3]:
      raise ValueError('Argument %d for command %s is unsupported' % (args[0], cmd))

def encode_cmd(cmd, seq, args = [], flag = 0):
  if debug < 4:
    validate_cmd(cmd, args, flag)
  msg = pack(packet_fmt, 0, flag, seq, cmd)
  if len(args):
    msg += pack('%dB' % len(args), *args)
  if debug > 0:
    print ('o[%d]: %s "%s" %s' % (len(msg),
	hexprt(msg[0:min_return-3],' '), cmd,
	hexprt(msg[min_return-1:],' '),
	 ), file=sys.stderr)
  return msg

def decode_cmd(msg):
  if debug > 0:
    print ('i[%d]: %s "%s" %s' % (len(msg),
	hexprt(msg[0:min_return-3],' '),
	msg[min_return-3:min_return-1].decode('us-ascii'),
#	unpack('2s', msg[min_return-3:min_return-1])[0],
	hexprt(msg[min_return-1:],' '),
	), file=sys.stderr)
  (flag, seq, cmd, failed) = unpack('%sB' % packet_fmt, msg[:min_return])[1:5]
  cmd = cmd.decode('us-ascii')
  cmd_key = cmd.upper()
  msg = msg[min_return:]
  if cmd in cmd_decode and len(msg) > 0:
    return (cmd, seq, flag, failed, cmd_decode[cmd][flag](msg, flag))

  val = bytes2int(msg[0:1])
  if cmd_key in cmd_check and val in cmd_check[cmd_key][3]:
    return (cmd, seq, flag, failed, (val, cmd_check[cmd_key][3][val]))
  else:
    return (cmd, seq, flag, failed, (msg,))

def setup_camera(sock, host, cam_type=''):
  global cmd_check

  if not cam_type in cameras:
    sock.sendto(encode_cmd('cv', 0), (host,dst_port))
    msg, cam_addr = sock.recvfrom(max_return)
    recv = decode_cmd(msg)
    if recv[3]:
      sock.sendto(encode_cmd('PW', 0, [ 1 ], 1), (host,dst_port))
      msg, cam_addr = sock.recvfrom(max_return)
      sock.sendto(encode_cmd('cv', 0, [], 1), (host,dst_port))
      msg, cam_addr = sock.recvfrom(max_return)
      recv = decode_cmd(msg)
    cam_type = recv[4][2]
  if not cam_type in cameras:
    return

  for cmd in cameras[cam_type].keys():
    if cmd in cmd_check:
      cmd_check[cmd][3] = cameras[cam_type][cmd]
  
def setup_socket(host, bcast = False):
  sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
#  sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO,
#    pack('!2I', rcv_time, 0) )
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  if bcast:
    sock.bind((host, 0))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
  else:
    sock.bind(('', 0))
  return sock

def main():
  global debug, dst_port, rcv_time
  bcast = False
  host = '127.0.0.1'
  seq = 0
  flag = 0
  cmd = None
  params = []
  try:
    opts, args = getopt.getopt(sys.argv[1:],
	'bc:d:i:v:w:fh', ['bcast', 'cmd=', 'debug=', 'id=', 'val=', 'wait=', 'flag', 'help'])
  except getoptGetOptError as err:
    print (str(err), file=sys.stderr)
    usage()
    return 2

  for o, a in opts:
    if o in ('-h', '--help'):
      usage()
      return 0
    elif o in ('-b', '--bcast'):
      bcast = True
    elif o in ('-c', '--cmd'):
      cmd = a
    elif o in ('-d', '--debug'):
      debug = int(a)
    elif o in ('-f', '--flag'):
      flag = 1
    elif o in ('-i', '--id'):
      seq = int(a)
    elif o in ('-v', '--val'):
      if 'TM' == cmd:
        params = [ 18, 8, 25, 23, 31, 00 ]
      else:
        params.append(int(a))
    elif o in ('-w', '--wait'):
      rcv_time = int(a)
    else:
      assert False, 'unhandled option'

  if 0 == len(args):
    usage()
    return 1
  else:
    host = args[0]
    if 2 == len(args):
      dst_port = int(args[1])

  sock = setup_socket(host, bcast)
  setup_camera(sock, host, 'HD3.10')
  if not cmd is None:
    sock.sendto(
    encode_cmd(cmd, seq, params, flag)
    , (host,dst_port))
    msg, cam_addr = sock.recvfrom(max_return)
    recv = decode_cmd(
#	pack('%sHQ'%packet_fmt,0,1,0,'lc',5,0)
	msg
    )
    print(recv)
    sock.close()
    return 0

# Interactive mode

if __name__ == '__main__':
  sys.exit(main())
