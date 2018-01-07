import keyboard
import subprocess
import signal


def sendSignal(nodeNum, signalNum):
    signalToToken = {
        '1': "PING",
        '2': "PONG",
    }
    print("Commanding node{} to lose {} token".format(
        nodeNum, signalToToken[signalNum]))

    # way faster than 'vagrant ssh'
    sshCmd = 'ssh -i ./.vagrant/machines/node{}/virtualbox/private_key' + \
        ' ubuntu@192.168.10.{}'
    sshCmd = sshCmd.format(nodeNum, int(nodeNum)+1)
    cmd = 'ps aux | grep [p]ingpong | awk \'{print $2}\' | \
        xargs kill -s SIGUSR' + signalNum
    subprocess.call(sshCmd.split(' ') + [cmd])

    print(40*"=")


with open('./hosts', 'r') as f:
    nodesNum = len(f.readlines())

print("CTRL + node number - lose PING\n ALT + node number - lose PONG\n"
      "There are {} nodes".format(nodesNum))

for i in range(1, nodesNum+1):
    n = str(i)
    keyboard.add_hotkey('ctrl+'+n, sendSignal, (n, '1'))
    keyboard.add_hotkey('alt+'+n, sendSignal, (n, '2'))

try:
    signal.signal(signal.SIGQUIT, signal.SIG_IGN)  # ignore SIGQUIT (^4)
    signal.pause()
except KeyboardInterrupt:
    print("Quitting")
