import time

###############################################################################

import subprocess
import shlex

import cv2

####################################################i###########################

def FFPlayer(PlayCmd):

    # if PlayerProc:
    #     # PlayerProc.terminate()
    #     PlayerProc.kill()
    #     subprocess.run(["/usr/bin/killall", "ffplay"])
    # else:
    # PlayerProc = subprocess.Popen(WrapPlayCmd)
    PlayerProc = subprocess.Popen(shlex.split(PlayCmd),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL
    )

def openCvPlay(fifo = './fifo_file'):
    cap = cv2.VideoCapture()
    ret = cap.open(fifo)

    while True:
        try:
            _, img = cap.read()
            # img = cv2.imread(fifo)
            #tag =pass(img)
            # img = tag +img
            cv2.imshow('img', img)

            if cv2.waitKey(1) & 0xff == ord('q'):
                break
        except KeyboardInterrupt:
            return


if __name__ == '__main__':
    # cmd = "/usr/bin/ffplay -fs -i ./fifo_file -analyzeduration 1 -probesize 32 -sync ext"
    # FFPlayer(cmd)
    # while True:
    #     pass
    openCvPlay()
