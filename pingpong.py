import os
import pika
import time
import signal


class Node:
    def __init__(self):
        self.exit_flag = False

        with open('/etc/hosts', 'r') as f:
            lines = f.readlines()

        nodes = [l.split(' ')[1] for l in lines if l.startswith('192.168.10.')]

        hostname = os.uname().nodename
        hostnum = int(hostname[4:])
        neighbor = nodes[hostnum % len(nodes)]
        self.remote_conn = pika.BlockingConnection(
            pika.ConnectionParameters(host=neighbor))
        self.remote_channel = self.remote_conn.channel()

        self.local_conn = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost'))
        self.local_channel = self.local_conn.channel()
        self.local_channel.queue_declare(queue='token_queue', exclusive=True)

        self.local_channel.basic_consume(self.tokenReceived, no_ack=True,
                                         queue='token_queue')

        self.hasToken = True if hostnum == 1 else False

    def tokenReceived(self, ch, method, props, body):
        print("Received token: {}".format(body))
        self.hasToken = True

    def loop(self):
        while not self.exit_flag:
            while not self.hasToken:
                self.local_conn.process_data_events()

            for _ in range(3):
                print(".", end='', flush=True)
                time.sleep(1)
            print()
            self.remote_channel.basic_publish(exchange='',
                                              routing_key='token_queue',
                                              body='Hello!')
            print("Passed token")
            self.hasToken = False

        print("Cleaning up and exiting")
        self.remote_conn.close()
        self.local_conn.close()

    def set_flag(self, signal, frame):
        self.exit_flag = True


if __name__ == '__main__':
    node = Node()
    signal.signal(signal.SIGINT, node.exit_flag)
    time.sleep(3)
    node.loop()
