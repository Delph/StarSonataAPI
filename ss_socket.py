import asyncio
import socket
import struct

BUF_SIZE = 4096

class Message():
  def __init__(self, mtype=-1, payload=b''):
    self.length = len(payload)
    self.type = mtype
    self.payload = payload

  def buf_out(self):
    return struct.pack('<hB', self.length, self.type) + self.payload

  def buf_in(self, data):
    (self.length, self.type) = struct.unpack('<hB', data[:3])
    self.payload = data[3:]


class Socket():
  """
  A specialized socket wrapper which does some stuff for us for communicating with the game server
  """
  def __init__(self):
    self.buf = b''

  async def connect(self, host, port):
    self.__reader, self.__writer = await asyncio.open_connection(host, port)

  async def recv(self):
    m = Message()
    m.length = struct.unpack('<h', await self.__reader.readexactly(2))[0]
    m.type = struct.unpack('<B', await self.__reader.readexactly(1))[0]
    m.payload = await self.__reader.readexactly(m.length)
    return m

  async def send(self, message):
    self.__writer.write(message.buf_out())
    await self.__writer.drain()
  async def send_raw(self, buf):
    self.__writer.write(buf)
    await self.__writer.drain()

  def close(self):
    self.__writer.close()
