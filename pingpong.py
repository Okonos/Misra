import os
import pika
import logging
import time
import signal
from enum import IntEnum


class HasToken(IntEnum):
    NONE = 0
    PING = 1
    PONG = 2
    BOTH = 3


class TokenType(IntEnum):
    PING = 1
    PONG = 2


class Token:
    def __init__(self, type_: TokenType, value: int):
        if not isinstance(type_, TokenType):
            raise TypeError("Token type must be an instance of TokenType")
        self.type = type_
        self.value = value

    @classmethod
    def from_bytes(cls, values: bytes):
        type_, value = values.split(b' ')
        return cls(TokenType(int(type_)), int(value))

    def values(self):
        return '{} {}'.format(self.type.value, self.value)

    def __str__(self):
        return "Token ({}, {})".format(self.type.name, self.value)


class Node:
    def __init__(self):
        self.m = 0
        self.hasToken = HasToken.NONE
        self.ping_token = None
        self.pong_token = None
        self.tokens_to_lose = set()
        self.ID = int(os.uname().nodename[4:])
        self.logger = logging.getLogger(__file__)
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s:%(msecs)d - %(levelname)s - %(message)s',
            datefmt='%M:%S')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        with open('/etc/hosts', 'r') as f:
            nodes = [l.split(' ')[1] for l in f.readlines()
                     if l.startswith('192.168.10.')]

        neighbor = nodes[self.ID % len(nodes)]
        self.remote_conn = pika.BlockingConnection(
            pika.ConnectionParameters(host=neighbor))
        self.remote_channel = self.remote_conn.channel()

        self.local_conn = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost'))
        self.local_channel = self.local_conn.channel()
        self.local_channel.queue_declare(queue='token_queue', exclusive=True)

        self.local_channel.basic_consume(self.receive_token, no_ack=True,
                                         queue='token_queue')

    def pass_token(self, token: Token):
        self.m = token.value
        if token.type == TokenType.PONG:
            time.sleep(0.5)
            self.pong_token = None
        else:
            self.ping_token = None
        self.hasToken = HasToken(self.hasToken - token.type)

        if token.type in self.tokens_to_lose:
            self.logger.critical("Lost {} token!".format(token.type.name))
            self.tokens_to_lose.remove(token.type)
        else:
            self.remote_channel.publish(exchange='', routing_key='token_queue',
                                        body=token.values())

    def receive_token(self, ch, method, props, body):
        token = Token.from_bytes(body)
        self.handle_token(token)

    def try_receive_token(self):
        msg = self.local_channel.basic_get(queue='token_queue', no_ack=True)
        if msg[0] is None:
            return False
        self.handle_token(Token.from_bytes(msg[2]))
        return True

    def handle_token(self, token: Token):
        if abs(token.value) < self.m:  # old token
            self.logger.warning(
                "Received old token ({}); deleting".format(token))
            return

        self.logger.info("Received token: {}".format(token))

        assert self.hasToken not in (HasToken(token.type), HasToken.BOTH)
        self.hasToken = HasToken(self.hasToken + token.type)
        if token.type == TokenType.PING:
            self.ping_token = token
        else:  # PONG
            self.pong_token = token

        if self.hasToken == HasToken.BOTH:
            self.logger.warning("Tokens met, incarnating")
            self.incarnate(token.value)
        elif token.value == self.m:
            if token.type == TokenType.PING:  # PONG lost, regenerate it
                self.logger.critical("PONG Token lost, regenerating")
                self.pong_token = self.regenerate(TokenType.PONG, -token.value)
            else:  # PING lost
                self.logger.critical("PING Token lost, regenerating")
                self.ping_token = self.regenerate(TokenType.PING, -token.value)
            self.hasToken = HasToken.BOTH

    def regenerate(self, type_: TokenType, value: int):
        return Token(type_, value)

    def incarnate(self, value: int):
        self.ping_token = Token(TokenType.PING, abs(value)+1)
        self.pong_token = Token(TokenType.PONG, -(abs(value)+1))

    def loop(self):
        if self.ID == 1:
            self.logger.info("First node, initializing tokens")
            self.hasToken = HasToken.BOTH
            self.pass_token(Token(TokenType.PING, 1))
            self.pass_token(Token(TokenType.PONG, -1))

        try:
            while True:
                if self.hasToken == HasToken.NONE:
                    self.local_conn.process_data_events()

                if self.hasToken == HasToken.PING:
                    self.logger.warning("Entering critical section")
                    time.sleep(1)
                    self.logger.warning("Leaving critical section")
                    if self.try_receive_token():
                        continue
                    self.pass_token(self.ping_token)
                elif self.hasToken == HasToken.PONG:
                    self.pass_token(self.pong_token)
                elif self.hasToken == HasToken.BOTH:
                    self.pass_token(self.ping_token)
                    self.pass_token(self.pong_token)
        except KeyboardInterrupt:
            print("Cleaning up and exiting")
            self.remote_conn.close()
            self.local_conn.close()

    # TODO (jedna funkcja?)
    def lose_ping_token(self, signal, frame):
        self.tokens_to_lose.add(TokenType.PING)

    def lose_pong_token(self, signal, frame):
        self.tokens_to_lose.add(TokenType.PONG)


if __name__ == '__main__':
    node = Node()
    signal.signal(signal.SIGUSR1, node.lose_ping_token)
    signal.signal(signal.SIGUSR2, node.lose_pong_token)
    time.sleep(1)
    node.loop()
