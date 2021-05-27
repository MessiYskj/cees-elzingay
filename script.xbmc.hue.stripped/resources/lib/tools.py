import urllib2
import time
import os
import socket
import json
import random
import hashlib
import xbmc
import xbmcaddon

__addon__      = xbmcaddon.Addon()
__cwd__        = __addon__.getAddonInfo('path')
__icon__       = os.path.join(__cwd__,"icon.png")
__settings__   = os.path.join(__cwd__,"resources","settings.xml")

def notify(title, msg=""):
  global __icon__
  xbmc.executebuiltin("XBMC.Notification(%s, %s, 3, %s)" % (title, msg, __icon__))

def start_autodisover():
  port = 1900
  ip = "239.255.255.250"

  address = (ip, port)
  data = """M-SEARCH * HTTP/1.1
  HOST: %s:%s
  MAN: ssdp:discover
  MX: 3
  ST: upnp:rootdevice""" % (ip, port)
  client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

  hue_ip = None
  num_retransmits = 0
  while(num_retransmits < 10) and hue_ip == None:
      num_retransmits += 1
      client_socket.sendto(data, address)
      recv_data, addr = client_socket.recvfrom(2048)
      if "IpBridge" in recv_data and "description.xml" in recv_data:
        hue_ip = recv_data.split("LOCATION: http://")[1].split(":")[0]
      time.sleep(1)
      
  return hue_ip

def register_user(hue_ip):
  username = hashlib.md5(str(random.random())).hexdigest()
  device = "xbmc-player"
  data = '{"username": "%s", "devicetype": "%s"}' % (username, device)

  # use urllib2 as it's included in Python
  response = urllib2.urlopen('http://%s/api' % hue_ip, data)
  response = response.read()
  while "link button not pressed" in response:
    notify("Bridge discovery", "press link button on bridge")
    response = urllib2.urlopen('http://%s/api' % hue_ip, data)
    response = response.read()  
    time.sleep(3)

  return username

class Light:
  start_setting = None

  def __init__(self, bridge_ip, bridge_user, light):
    self.bridge_ip = bridge_ip
    self.bridge_user = bridge_user
    self.light = light
    self.get_current_setting()

  def request_url_put(self, url, data):
    # Unfortunately, this request will take ~1s on the bridge,
    #  ruining the ambilight effect
    opener = urllib2.build_opener(urllib2.HTTPHandler)
    request = urllib2.Request(url, data=data)
    request.get_method = lambda: 'PUT'
    url = opener.open(request)

  def get_current_setting(self):
    r = urllib2.urlopen("http://%s/api/%s/lights/%s" % \
      (self.bridge_ip, self.bridge_user, self.light))
    j = json.loads(r.read())
    self.start_setting = {
      "on": j['state']['on'],
      "bri": j['state']['bri'],
      "hue": j['state']['hue'],
      "sat": j['state']['sat'],
    }

  def set_light(self, data):
    self.request_url_put("http://%s/api/%s/lights/%s/state" % \
      (self.bridge_ip, self.bridge_user, self.light), data=data)

  def flash_light(self):
    self.dim_light()
    self.brighter_light()

  def dim_light(self):
    dimmed = '{"on":true,"bri":0,"transitiontime":4}'
    self.set_light(dimmed)

  def brighter_light(self):
    on = '{"on":true,"bri":%d,"transitiontime":4}' % self.start_setting['bri']
    self.set_light(on)