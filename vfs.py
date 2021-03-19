#!/usr/bin/env python

''' A basic GUi to use ImageViewer class to show its functionalities and use cases. '''

from PyQt5 import QtCore, QtGui, uic
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog
import cv2
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import imageio
from viewer import ImageViewer
import sys, os
DIR = os.path.dirname(os.path.realpath(__file__))
gui = uic.loadUiType(f"{DIR}/vfs.ui")[0]     # load UI file designed in Qt Designer
VALID_FORMAT = ('.BMP', '.GIF', '.JPG', '.JPEG', '.PNG', '.PBM', '.PGM', '.PPM', '.TIFF', '.XBM')  # Image formats supported by Qt

def getImages(folder):
    ''' Get the names and paths of all the images in a directory. '''
    image_list = []
    if os.path.isdir(folder):
        files = [f for f in os.listdir(folder) if f.upper().endswith(VALID_FORMAT)]
        files = sorted(files,key=lambda x: int(x.split("_")[0]))
        for i,file in enumerate(files):
            im_path = os.path.join(folder, file)
            name = file.split(".")[0]
            image_obj = {'name': name, 'path': im_path,"qitem":QtWidgets.QListWidgetItem(name)}
            image_list.append(image_obj)
    return image_list

class Iwindow(QtWidgets.QMainWindow, gui):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setupUi(self)

        self.cntr, self.numImages = -1, -1  # self.cntr have the info of which image is selected/displayed

        self.image_viewer = ImageViewer(self.qlabel_image)
        self.__connectEvents()
        self.showMaximized()
        self.videoFrameCount = -1
        self.videoLoaded = False
        self.vidlength = -1
        self.nameItemDict = {}

    def __connectEvents(self):
        self.open_folder.clicked.connect(self.selectDir)
        self.load_video.clicked.connect(self.loadVideo)
        self.next_im.clicked.connect(self.nextImg)
        self.prev_im.clicked.connect(self.prevImg)
        self.next_frame.clicked.connect(self.nextFrame)
        self.prev_frame.clicked.connect(self.prevFrame)
        self.prev_im.clicked.connect(self.prevImg)
        self.save_frame.clicked.connect(self.saveFrame)
        self.qlist_images.itemClicked.connect(self.itemClick)
        self.qlist_images.itemSelectionChanged.connect(self.changeImg)
        self.goFrame.clicked.connect(self.goToFrame)
    
    def delete_img(self):
        try:
            index = int(self.qlist_images.currentRow())
            path = self.imagesList[index]['path']
            os.remove(path)
            item = self.imagesList[index]["qitem"]
            item.setForeground(QtCore.Qt.red);
            self._changeImage()    
        except:
            pass
    
    def selectDir(self):
        ''' Select a directory, make list of images in it and display the first image in the list. '''
        # open 'select folder' dialog box
        self.folder = str(QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory"))
        if not self.folder:
            QtWidgets.QMessageBox.warning(self, 'No Folder Selected', 'Please select a valid Folder')
            return
        
        self.imagesList = getImages(self.folder)
        self.numImages = len(self.imagesList)

        # make qitems of the image names
        for i,img in enumerate(self.imagesList):
            self.qlist_images.addItem(img["qitem"])
            self.nameItemDict[img["name"]] = img["qitem"]


        # display first image and enable Pan 
        if self.numImages > 1:
            self.cntr = 0
            self.image_viewer.loadImage(self.imagesList[self.cntr]['path'])
            self.imagesList[self.cntr]["qitem"].setSelected(True)

        # enable the next image button on the gui if multiple images are loaded
        if self.numImages > 1:
            self.next_im.setEnabled(True)
    
    def loadVideo(self):
        self.videofile = str(QFileDialog.getOpenFileName(None, 'Open File', '.')[0])
        if not self.videofile:
            QtWidgets.QMessageBox.warning(self, 'No file selected', 'Please select a valid video file')
            return
        self.cap = cv2.VideoCapture(self.videofile)
        self.videoLoaded = True
        self.vidlength = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        if (self.cap.isOpened()== False):
            print("Error opening video stream or file")
        self.videoFrameCount = 0
        self.loadVideoFrame()
    
    def loadVideoFrame(self):
        if not self.videoLoaded:
            return

        self.cap.set(1,self.videoFrameCount)
        ret, frame = self.cap.read()
        if ret == True:
            frame = frame.astype(np.uint8)
            frame = cv2.cvtColor(frame,cv2.COLOR_BGRA2RGB)
            self.vidframe = frame
            self.image_viewer.loadImagePIL(Image.fromarray(frame))

    def nextFrame(self):
        if not self.videoLoaded:
            return
        jump = int(self.videoJump.text())
        if self.videoFrameCount + jump < self.vidlength:
            self.videoFrameCount += jump
            self.frameNum.setText(f"{self.videoFrameCount}/{self.vidlength}")
            self.loadVideoFrame()
    
    def prevFrame(self):
        if not self.videoLoaded:
            return
        jump = int(self.videoJump.text())
        if self.videoFrameCount - jump > 0:
            self.videoFrameCount -= jump
            self.loadVideoFrame()
    
    def nextImg(self):
        if self.cntr < self.numImages -1:
            self.cntr += 1
            self._changeImage()
        else:
            QtWidgets.QMessageBox.warning(self, 'Sorry', 'No more Images!')

    def prevImg(self):
        if self.cntr > 0:
            self.cntr -= 1
            self._changeImage()
        else:
            QtWidgets.QMessageBox.warning(self, 'Sorry', 'No previous Image!')
   
    def saveFrame(self):
        if not self.folder:
            self.selectDir()
        if not self.folder:
            return
        idx,fps = self.videoFrameCount, self.fps
        time = str(round(idx/fps,4)).replace(".","_")
        fname = f"{idx}_{time}"
        imageio.imwrite(f"{self.folder}/{fname}.jpg", self.vidframe)
        if fname not in self.nameItemDict.keys():
            item = QtWidgets.QListWidgetItem(fname)
            self.imagesList += [{"name":fname,"path":f"{self.folder}/{fname}.jpg","qitem": item}]
            self.nameItemDict[fname] = item
            self.qlist_images.addItem(item)
            self.numImages += 1
        else:
            self.nameItemDict[fname].setForeground(QtCore.Qt.black)
            self.nameItemDict[fname].setSelected(True)
            self.cntr = int(self.qlist_images.currentRow())
      
    def changeImg(self):
        index = int(self.qlist_images.currentRow())
        self.cntr = index
        self._changeImage()
    
    def itemClick(self, item):
        self.cntr = int(self.qlist_images.currentRow())
        self._changeImage()

    def _changeImage(self):
        if os.path.exists(self.imagesList[self.cntr]['path']):
            self.image_viewer.loadImage(self.imagesList[self.cntr]['path'])
        else:
            self.image_viewer.loadImage(f"{DIR}/icons/noShowDetails.png")

    def keyPressEvent(self, e):
        if e.key()  == QtCore.Qt.Key_Shift:
            self.delete_img()
        if e.key()  == QtCore.Qt.Key_Right:
            self.nextFrame()
        if e.key()  == QtCore.Qt.Key_Left:
            self.prevFrame()
        if e.key()  == QtCore.Qt.Key_S:
            self.saveFrame()

    def goToFrame(self):
        if not self.videoLoaded:
            return
        jumpTo = int(self.selectFrame.text())
        if jumpTo >= 0 and jumpTo < self.vidlength:
            self.videoFrameCount = jumpTo
            self.frameNum.setText(f"{self.videoFrameCount}/{self.vidlength}")
            self.loadVideoFrame()

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle(QtWidgets.QStyleFactory.create("Cleanlooks"))
    app.setPalette(QtWidgets.QApplication.style().standardPalette())
    parentWindow = Iwindow(None)
    sys.exit(app.exec_())

if __name__ == "__main__":
    print(__doc__)
    main()