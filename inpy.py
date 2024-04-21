import sys
from PyQt5.QtWidgets import QApplication, QWidget, QDesktopWidget, QSystemTrayIcon, QMainWindow, QMenu, QAction
from PyQt5.QtGui import QPainter, QPixmap, QImage, QCursor
from PyQt5.QtCore import Qt, QTimer
import PyQt5.QtCore as QtCore
import numpy as np
import cv2
import time
import os
import pathlib


#https://github.com/adryd325/oneko.js/blob/main/oneko.js
def qmap2np(qim):
    q = qim.toImage()
    return np.array(q.convertToFormat(QImage.Format_RGBA8888))

def np2qmap(cv_img):
    height, width, channel = cv_img.shape
    bytesPerLine = channel * width
    #print(cv_img.shape)
    qImg = QImage(cv_img.astype(np.uint8).tobytes(), width, height, bytesPerLine, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qImg)

cat_W = 32
cat_H = 32
sprite_sets = {
    'idle': [[3, 3]],
    'alert': [[7, 3]],
    'scratchSelf': [
        [5, 0],
        [6, 0],
        [7, 0],
    ],
    'scratchWallN': [
        [0, 0],
        [0, 1],
    ],
    'scratchWallS': [
        [7, 1],
        [6, 2],
    ],
    'scratchWallE': [
        [2, 2],
        [2, 3],
    ],
    'scratchWallW': [
        [4, 0],
        [4, 1],
    ],
    'tired': [[3, 2]],
    'sleeping': [
        [2, 0],
        [2, 1],
    ],
    'N': [
        [1, 2],
        [1, 3],
    ],
    'NE': [
        [0, 2],
        [0, 3],
    ],
    'E': [
        [3, 0],
        [3, 1],
    ],
    'SE': [
        [5, 1],
        [5, 2],
    ],
    'S': [
        [6, 3],
        [7, 2],
    ],
    'SW': [
        [5, 3],
        [6, 1],
    ],
    'W': [
        [4, 2],
        [4, 3],
    ],
    'NW': [
        [1, 0],
        [1, 1],
    ],
}
nekoSpeed = 10
fps = 32

def lerp(a, b, t):
    return a * (1-t) + b * t

def clamp(v, m, x):
    return min(x, max(m, v))

class Canvas(QWidget):
    def __init__(self, dim=None):
        super().__init__()
        if not dim:
            screen = QDesktopWidget().screenGeometry()
            dim = [screen.width(), screen.height()]
        self.modmode = False
        self.dim = dim
        self.setWindowTitle("It's a cat... on your screen...")
        self.setGeometry(0, 0, dim[0], dim[1])
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowTransparentForInput | QtCore.Qt.Tool) 
        self.setAttribute(Qt.WA_TranslucentBackground)

        path = str(pathlib.Path().resolve())+"/sprite.png"
        print(path)
        self.src = cv2.imread(path, cv2.IMREAD_UNCHANGED)

        self.spriteSetBake = {}
        print("Baking...")
        for key, frames in sprite_sets.items():
            self.spriteSetBake[key] = []
            print(f" {key}")
            for frame in frames:
                coord = frame
                data = self.src[coord[1] * cat_H: (coord[1]+1) * cat_H, coord[0] * cat_W: (coord[0]+1) * cat_W, :]
                self.spriteSetBake[key].append(data)
                print(f"  {len(self.spriteSetBake[key])}")
        

        
        self.catpos = [128, 128]
        self.frameId = 0
        self.painter = QPainter(self)
        self.timer = QTimer(self)

        self.timer.timeout.connect(self.update)
        self.timer.start(int((1/fps)*1000))

        self.lastMouseAct = 0

        self.modeMem = ""
        self.modeMemT = time.time()
    def update(self):
        self.repaint()
    def paintEvent(self, event):
        #print(event)
        mousepos = QCursor.pos()
        mousepos = [mousepos.x(), mousepos.y()]
        if not self.modmode:
            mousepos = [clamp(mousepos[0], 0, self.dim[0]), clamp(mousepos[1], 0, self.dim[1])]
        dx = mousepos[0] - self.catpos[0]
        dy = mousepos[1] - self.catpos[1]
        dist = (dx**2 + dy**2) ** .5
        normx = 0
        normy = 0
        if dist > 0:
            normx = dx / dist
            normy = dy / dist
        mode = "idle"
        """"""
        # mess begin
        if dist > 48:
            # follow mode
            if time.time() - self.modeMemT > 5 and self.modeMem == "idle":
                mode = "alert"
            elif self.modeMem != "alert" or (self.modeMem == "alert" and time.time() - self.modeMemT > 1):
                
                direction = ""
                direction = "S" if dy / dist > 0.5 else ""
                direction += "N" if dy / dist < -0.5 else ""
                direction += "E" if dx / dist > 0.5 else ""
                direction += "W" if dx / dist < -0.5 else ""
                mode = direction
 
                if self.modmode:
                    self.catpos = [(int(self.catpos[0] + normx * nekoSpeed)) % self.dim[0], (int(self.catpos[1] + normy * nekoSpeed)) % self.dim[1]]
                else:
                    self.catpos = [clamp(int(self.catpos[0] + normx * nekoSpeed), cat_W, self.dim[0] - cat_W), clamp(int(self.catpos[1] + normy * nekoSpeed), cat_H, self.dim[1] - cat_H)]

        if self.modeMem == "alert" and time.time() - self.modeMemT < .6:
            mode = "alert"
   
        if mode == self.modeMem:
            self.frameId += 1/fps * (nekoSpeed if mode != "idle" else nekoSpeed/4)
        else:
            self.modeMem = mode
            self.modeMemT = time.time()
            self.frameId = 0

        if mode == "idle" and time.time() - self.modeMemT > 5:
            if time.time() - self.lastMouseAct < 1:
                self.modeMemT = time.time()
                self.frameId = 0
                mode = "alert"
            elif time.time() - self.modeMemT > 6:
                mode = "sleeping"
            else:
                mode = "tired"
        # mess end
        # will make this more readable later :3 

        #self.catpos = [random.randrange(0, self.dim[0]), random.randrange(0, self.dim[1])]
        self.painter.begin(self)
        self.setFrame(mode, int(self.frameId))
        self.painter.end()

    def setFrame(self, name, frame):
        
        data = self.spriteSetBake[name][frame % len(sprite_sets[name])]
        #data = self.src[coord[1] * cat_H: (coord[1]+1) * cat_H, coord[0] * cat_W: (coord[0]+1) * cat_W, :] # this is slow af
        self.painter.drawPixmap(self.catpos[0]-16, self.catpos[1]-16, np2qmap(data))

        
        


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Canvas()
    window.show()
    #window.hide()
    print("Whatever man")
    sys.exit(app.exec_())
