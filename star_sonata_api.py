import asyncio
import struct

from .ss_socket import Message, Socket
from .message_types import *


class Account():
  def __init__(self, username, password):
    self.username = username
    self.password = password
    self.characters = []

  def addCharacter(self, character):
    self.characters.append(character)

  def get_hash(self):
    r1 = 0
    r2 = 666
    while r1 < len(self.username):
      r2 = r2 ^ ord(self.username[r1]) << (r1 & 4095)
      r1 += 1

    r1 = 0
    while r1 < len(self.password):
      r2 = r2 ^ ord(self.password[r1]) << ((len(self.password) - r1) & 4095)
      r1 += 1

    return r2 ^ (StarSonataAPI.SUBVERSION + (StarSonataAPI.SUBVERSION << 4) + StarSonataAPI.SUBVERSION + 15)

  def bufout(self):
    username = self.username
    password = self.password
    flags = 1

    payload = struct.pack('<BBBBHi%ssB%ssBBHI' % (len(username.encode('utf-8')), len(password.encode('utf-8'))),
      1, # uint8
      0, # uint8
      0, # uint8
      0, # uint8
      StarSonataAPI.VERSION, # (u)int16
      flags, # int32
      username.encode('utf-8'), # string
      0, # uint8
      password.encode('utf-8'), #string
      0, # uint8
      0, # uint8
      StarSonataAPI.SUBVERSION, # (u)int16
      self.get_hash(), # uint32
    )
    m = Message()
    m.payload = payload
    m.type = CS_CHATCLIENTLOGIN
    m.length = len(payload)
    return m


class Character():
  def __init__(self, character_id, name, class_name, level, money):
    self.character_id = character_id
    self.name = name
    self.class_name = class_name
    self.level = level
    self.money = money

  def __str__(self):
    return self.name

  def __eq__(self, other):
    if type(self) is type(other):
      return self.__dict__ == other.__dict__
    return False


class Team():
  def __init__(self, team_id, db_id, name, rank):
    self.team_id = team_id
    self.db_id = db_id
    self.name = name
    self.rank = rank
    self.members = []

  def __str__(self):
    return self.name

def extract_string(payload, start):
  offset = start
  while payload[offset] != 0:
    offset += 1
  return (''.join([chr(payload[x]) for x in range (start, offset)]), offset)

class TextMessage():
  def __init__(self, msgType=-1, message='', channel='', username=None):
    self.type = msgType
    self.message = message
    self.channel = channel
    self.username = username

  def buf_in(self, payload):
    offset = 0
    self.type = payload[offset]
    offset += 1
    self.message, offset = extract_string(payload, offset)
    offset += 1

    self.channel, offset = extract_string(payload, offset)
    offset += 1
    if offset < len(payload):
      self.username, offset = extract_string(payload, offset)

  def buf_out(self):
    payload = struct.pack('<B', self.type)
    payload += self.message.encode('utf-8')
    payload += b'\000'
    if self.username:
      payload += self.username.encode('utf-8')
      payload += b'\000'
    return payload

  @property
  def channel_name(self):
    types = {
      MSG_ERROR: 'Error',
      MSG_GLOBAL_LOGIN_MSG: 'Login',
      MSG_USER_CHATCLIENTONLY: 'Chat',
      MSG_USER_GALAXY: 'Galaxy',
      MSG_USER_GLOBAL: 'All',
      MSG_USER_GROUP: 'Squad',
      MSG_USER_HELP: 'Help',
      MSG_USER_MODERATOR: 'Moderator',
      MSG_USER_TEAM: 'Team',
      MSG_USER_TRADE: 'Trade',
      MSG_USER_USER: 'PM',
      MSG_USER_LFG: 'LFG'
    }
    if self.type in types:
      return types[self.type]
    return f'Unknown ({self.type})'

  @staticmethod
  def channel_to_send(ch):
    types = {
      'ALL': USER_TALK_GLOBAL,
      'GALAXY': USER_TALK_GALAXY,
      'TEAM': USER_TALK_TEAM,
      'TRADE': USER_TALK_TRADE,
      'SQUAD': USER_TALK_GROUP,
      'HELP': USER_TALK_HELP
    }
    return types[ch]

  @staticmethod
  def channel_to_recv(ch):
    types = {
      'ALL': MSG_USER_GLOBAL,
      'GALAXY': MSG_USER_GALAXY,
      'TEAM': MSG_USER_TEAM,
      'TRADE': MSG_USER_TRADE,
      'SQUAD': MSG_USER_GROUP,
      'HELP': MSG_USER_HELP
    }
    return types[ch]

  def __str__(self):
    if self.username:
      return f'#{self.channel_name} ({self.username}) {self.message}'
    return f'#{self.channel_name} {self.message}'


class StarSonataAPI():
  # chat client version, will need updating if the chat client ever gets updated
  VERSION = 100
  SUBVERSION = 2

  # default server info
  HOST = 'liberty.starsonata.com'
  PORT = 3030

  def __init__(self):
    self.events = {}

    self.socket = Socket()

    self.account = None
    self.character = None
    self.team = None

  def on_event(self, event):
    def wrapper(func):
      self.events[event] = func
      return func
    return wrapper

  def post_event(self, event, *args, **kwargs):
    func = self.events.get(event, None)
    if func:
      func(*args, **kwargs)

  async def connect(self, **kwargs):
    host = kwargs.get('host', self.HOST)
    port = kwargs.get('port', self.PORT)

    print(f'Connecting to {host}:{port}')
    await self.socket.connect(host, port)
    return self.socket

  def disconnect(self):
    self.socket.close()
    self.socket = Socket()

  async def __ping(self, message):
    (sec, usec) = struct.unpack('<ii', message.payload)

    # response, pong
    resp = struct.pack('<hBiihbhhhb', 18, 1, sec, usec, 30, 65, 32, 1024, 768, 65)
    await self.socket.send_raw(resp)

  async def __hello(self, message):
    (persona, special) = struct.unpack('<ib', message.payload)
    print(f'{persona} is {special}')

  async def __disconnect(self, message):
    reason = ''.join([chr(b) for b in message.payload])
    print(f'Disconnected: {reason}')

    self.socket.close()
    raise SystemExit

  async def __updateclient(self, message):
    print('API version outdated')
    raise NotImplementedError

  async def __loginfail(self, message):
    error = ''.join([chr(b) for b in message.payload])
    print(error)
    raise NotImplementedError

  async def __team(self, message):
    data = message.payload
    (tid, dbid) = struct.unpack('<ii', data[:8])
    name = ''
    offset = 8
    while data[offset] != 0:
      name += chr(data[offset])
      offset += 1
    offset += 1
    rank = struct.unpack('<h', data[offset:])[0]
    self.team = Team(tid, dbid, name, rank)

  async def __team_member(self, message):
    data = message.payload
    offset = 0
    (persona,) = struct.unpack('<i', data[offset:offset+4])
    offset += 4
    name = ''
    while data[offset] != 0:
      name += chr(data[offset])
      offset += 1
    offset += 1
    (rank, lastOn) = struct.unpack('<hi', data[offset:offset+6])
    if self.team:
      member = next((m for m in self.team.members if m['persona'] == persona), None)
      if member:
        member['rank'] = rank
        member['lastOn'] = lastOn
      else:
        self.team.members.append({'persona': persona, 'name': name, 'rank': rank, 'lastOn': lastOn})

  async def character_select(self, character_id):
    m = Message()
    m.type = CS_SELECTCHARACTER
    m.payload = struct.pack('<i', character_id)
    m.length = len(m.payload)
    await self.socket.send(m)

  async def send_message(self, tm):
    m = Message(CS_TEXTMESSAGE, tm.buf_out())
    await self.socket.send(m)

  async def _connect(self):
    self.socket = await self.connect()
    await self.socket.send(self.account.bufout())

  async def run(self, account, **kwargs):
    self.account = account
    try:
      await self._connect()

      while True:
        try:
          message = await self.socket.recv()

          # events we handle internally, e.g., ping
          system_events = {
            SC_PING: self.__ping,
            SC_HELLO: self.__hello,
            SC_TEAM: self.__team,
            SC_TEAMMEMBER: self.__team_member,
            SC_LOGINFAIL: self.__loginfail,
            SC_UPDATECLIENT: self.__updateclient
          }

          handled = False
          if message.type in system_events:
            await system_events[message.type](message)
            handled = True
          if message.type in self.events:
            await self.events[message.type](message)
            handled = True

          if not handled:
            print('Unknown message type: %s\n%s' % (message.type, ', '.join([str(b) for b in message.payload])))
        except ConnectionResetError:
          self.disconnect()
          await self._connect()
        except asyncio.IncompleteReadError:
            self.disconnect()
            await self._connect()
    except KeyboardInterrupt:
      pass
    finally:
      self.disconnect()
