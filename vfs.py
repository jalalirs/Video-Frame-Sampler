#!/usr/bin/env python

''' A basic GUi to use ImageViewer class to show its functionalities and use cases. '''

from PyQt5 import QtCore, QtGui, uic
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtGui import QPixmap
import cv2
import numpy as np
import glob
from PIL import Image
import matplotlib.pyplot as plt
import imageio
from viewer import ImageViewer
import sys, os
import json
DIR = os.path.dirname(os.path.realpath(__file__))
gui = uic.loadUiType(f"{DIR}/vfs.ui")[0]     # load UI file designed in Qt Designer
VALID_FORMAT = ('.BMP', '.GIF', '.JPG', '.JPEG', '.PNG', '.PBM', '.PGM', '.PPM', '.TIFF', '.XBM')  # Image formats supported by Qt

def getImages(folder):
    ''' Get the names and paths of all the images in a directory. '''
    image_list = []
    if os.path.isdir(folder):
        files = [f for f in os.listdir(folder) if f.upper().endswith(VALID_FORMAT)]
        files = sorted(files,key=lambda x: int(x.split(".")[0].split("_")[-1]))
        for i,file in enumerate(files):
            im_path = os.path.join(folder, file)
            name = file.split(".")[0]
            image_obj = {'name': name, 'path': im_path,"qitem":QtWidgets.QListWidgetItem(name)}
            image_list.append(image_obj)
    return sorted(image_list,key=lambda x: x["name"])

class QCustomQWidget (QtWidgets.QWidget):
    def __init__ (self, parent = None):
        super(QCustomQWidget, self).__init__(parent)
        self.lbl_name  = QtWidgets.QLabel()
        self.lbl_name.setMaximumWidth(160)
        self.allQHBoxLayout  = QtWidgets.QHBoxLayout()
        self.currentCount = 0
        self.currentCountLabel  = QtWidgets.QLabel()
        self.currentCountLabel.setText(str(self.currentCount))
        self.currentCountLabel.setMaximumWidth(30)

        self.currentAddText  = QtWidgets.QLineEdit()
        self.currentAddText.setText("0")
        self.currentAddText.setMaximumWidth(20)
        #self.iconQLabel      = QtWidgets.QPushButton()

        self.iconQLabel = QtWidgets.QLabel()
        pixmap = QPixmap('cat.jpg')

        self.allQHBoxLayout.addWidget(self.iconQLabel, 0)
        self.allQHBoxLayout.addWidget(self.lbl_name, 1)
        self.allQHBoxLayout.addWidget(self.currentCountLabel, 2)
        self.allQHBoxLayout.addWidget(self.currentAddText, 3)
        self.setLayout(self.allQHBoxLayout)
        # setStyleSheet
    
        self.lbl_name.setStyleSheet('''
            color: rgb(0, 0, 0);
        ''')
    def setTextDown (self, text):
        self.name = text
        self.lbl_name.setText(text)
    def setIcon (self, imagePath):
        img = QtGui.QPixmap(imagePath)
        img = img.scaledToWidth(64)
        self.iconQLabel.setPixmap(img)

class Dataset:
    def __init__(self,keys):
        self.keys = {k:0 for k in keys}
        self._keys = keys
        self.frames = {}
        self.nlabels = len(keys)
    
    def get_ordered(self):
        return [self.keys[k] for k in self._keys]
    def get_frames_for_label(self,label):
        lst = []
        for k,v in self.frames.items():
            if label in v:
                lst.append(k)
        return lst

    def add_frame(self,name,labels):
        if name in self.frames:
            currentLabels = self.frames[name]
            for k,v in currentLabels.items():
                self.keys[k] -= v

        for k,v in labels.items():
            self.keys[k] += v
        print(name,labels)
        self.frames[name] = labels
    def remove_frame(self,name):
        for k,v in self.frames[name].items():
            self.keys[k] -= v
        self.frames.pop(name)
    @classmethod
    def load(cls,folder,names):
        f = f"{folder}/data.json"
        dataset = Dataset(names)
        if os.path.exists(f):
            with open(f"{folder}/data.json") as f:
                dd = json.load(f)
            dataset.frames = dd["frames"]
            dataset.nlabels = dd["nlabels"]
            dataset.keys = dd["keys"]
            dataset._keys = dd["keys_list"]
        return dataset
    def save(self,folder):
        dataset = {
            "keys": self.keys,
            "frames": self.frames,
            "keys_list": self._keys,
            "nlabels": self.nlabels
        }
        keys = {}
        for f,v in self.frames.items():
            for k,v2 in v.items():
                if k in keys:
                    keys[k] += v2
                else:
                    keys[k] = v2
        for k in self._keys:
            if k not in keys:
                keys[k] = 0
        dataset["keys"] = keys
        
        with open(f"{folder}/data.json","w") as f:
            f.write(json.dumps(dataset,indent=4))


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
        self.dataset = None
        self.refreshLabels()
        self.imagesList = {}
        self.locked = True
        
    def __connectEvents(self):
        self.open_folder.clicked.connect(self.selectDir)
        self.load_video.clicked.connect(self.loadVideo)
        self.next_im.clicked.connect(self.nextImg)
        self.prev_im.clicked.connect(self.prevImg)
        self.next_frame.clicked.connect(self.nextFrame)
        self.prev_frame.clicked.connect(self.prevFrame)
        self.prev_im.clicked.connect(self.prevImg)
        self.save_frame.clicked.connect(self.saveFrame)
        self.pb_refresh.clicked.connect(self.refreshLabels)
        self.qlist_images.itemClicked.connect(self.itemClick)
        self.qlist_images.itemSelectionChanged.connect(self.changeImg)
        self.ls_labels.itemSelectionChanged.connect(self.update_data_for_label)
        self.goFrame.clicked.connect(self.goToFrame)
        self.pb_lockUnlock.clicked.connect(self.lockUnlock)
    
    def on_ln_search_key_textChanged(self):
        t = self.ln_search_key.text()
        ls = self.ls_labels
        if t.strip() == "":
            for index in range(self.ls_labels.count()):
                ls.setRowHidden(index, False)
            return
        for index in range(ls.count()):
            item = ls.item(index)
            itemWidget = self.ls_labels.itemWidget(item)
            name = itemWidget.name
            if t not in name:
                ls.setRowHidden(index, True)
            else:
                ls.setRowHidden(index, False)

    def lockUnlock(self):
        if self.pb_lockUnlock.isChecked():
            self.pb_lockUnlock.setText("Unlock")
            self.ls_labels.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
            self.ls_labels.selectionModel().clear()
            self.updateImageList(label=None,reload=False)
            self.locked = True
        else:
            self.pb_lockUnlock.setText("lock")
            self.ls_labels.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            self.ls_labels.setCurrentRow(0)
            self.locked = False
            
    def refreshLabels(self):
        path = "/Users/jalalirs/Documents/projects/iOcean/NEOM/dataset/keys/"
        labels = sorted(glob.glob(f"{path}/*"))
        self.names = sorted([os.path.basename(f).replace(".png","").replace(".jpeg","") for f in labels])
        self.ls_labels.clear()
        if not self.dataset:
            self.dataset = Dataset(self.names)
        else:
            for n in self.names:
                if n not in self.dataset._keys:
                    self.dataset._keys.append(n)
                    self.dataset._keys = sorted(self.dataset._keys)
                    self.dataset.nlabels += 1
                    self.dataset.keys[n] = 0
            self.dataset.save(self.folder)
        for index, name, icon in zip(range(len(labels)),self.names,labels):
                # Create QCustomQWidget
                myQCustomQWidget = QCustomQWidget()
                myQCustomQWidget.setTextDown(name)
                myQCustomQWidget.setIcon(icon)
                # 
                myQCustomQWidget.currentCountLabel.setText(str(self.dataset.keys[name]))
                myQCustomQWidget.currentCount = self.dataset.keys[name]
                # Create QListWidgetItem
                myQListWidgetItem = QtWidgets.QListWidgetItem(self.ls_labels)
                # Set size hint
                myQListWidgetItem.setSizeHint(myQCustomQWidget.sizeHint())
                # Add QListWidgetItem into QListWidget
                self.ls_labels.addItem(myQListWidgetItem)
                self.ls_labels.setItemWidget(myQListWidgetItem, myQCustomQWidget)
       
    def delete_img(self):
        try:
            index = int(self.qlist_images.currentRow())
            path = self.imagesList[index]['path']
            os.remove(path)
            item = self.imagesList[index]["qitem"]
            fname = self.qlist_images.currentItem().text()
            self.dataset.remove_frame(fname)
            for i,v in zip(range(self.dataset.nlabels),self.dataset.get_ordered()):
                lblitem = self.ls_labels.itemWidget(self.ls_labels.item(i))
                lblitem.currentCountLabel.setText(str(v))
            item.setForeground(QtCore.Qt.red)
            self._changeImage()    
        except:
            pass
        self.dataset.save(self.folder)
    
    def updateImageList(self,label=None,reload=False):
        if self.dataset is None:
            return
        for i in range(self.qlist_images.count()):
            self.qlist_images.takeItem(0)

        if reload:
            self.imagesList = getImages(self.folder) 
        
        if label is None:
            currentImgs = self.imagesList        
            print(len(currentImgs))    
        else:
            currentImgsFrames = self.dataset.get_frames_for_label(label)
            currentImgs = [img for img in self.imagesList if img["name"] in currentImgsFrames]
        
        self.numImages = len(currentImgs)
        self.currentImgs = currentImgs
        # make qitems of the image names
        for i,img in enumerate(self.currentImgs):
            self.qlist_images.addItem(img["qitem"])
            self.nameItemDict[img["name"]] = img["qitem"]

        self.cntr = 0
        # display first image and enable Pan 
        if self.numImages > 1: 
            self.image_viewer.loadImage(currentImgs[self.cntr]['path'])
            self.imagesList[self.cntr]["qitem"].setSelected(True)

        # enable the next image button on the gui if multiple images are loaded
        if self.numImages > 1:
            self.next_im.setEnabled(True)

    def selectDir(self):
        ''' Select a directory, make list of images in it and display the first image in the list. '''
        # open 'select folder' dialog box
        self.folder = str(QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory"))
        if not self.folder:
            QtWidgets.QMessageBox.warning(self, 'No Folder Selected', 'Please select a valid Folder')
            return
        
        self.dataset = Dataset.load(self.folder,self.names)
        self.updateImageList(label=None,reload=True)
        
        for i,v in zip(range(self.dataset.nlabels),self.dataset.get_ordered()):
                lblitem = self.ls_labels.itemWidget(self.ls_labels.item(i))
                lblitem.currentCountLabel.setText(str(v))
        self.qlist_images.setCurrentRow(0)
        self.changeImg()
        
    def loadVideo(self):
        self.videofile = str(QFileDialog.getOpenFileName(None, 'Open File', '.')[0])
        
        if not self.videofile:
            QtWidgets.QMessageBox.warning(self, 'No file selected', 'Please select a valid video file')
            return
        self.videoName = os.path.basename(self.videofile).split(".")[0]
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
            self.update_labels()
    
    def prevFrame(self):
        if not self.videoLoaded:
            return
        jump = int(self.videoJump.text())
        if self.videoFrameCount - jump >= 0:
            self.videoFrameCount -= jump
            self.frameNum.setText(f"{self.videoFrameCount}/{self.vidlength}")
            self.loadVideoFrame()
            self.update_labels()
    
    def nextImg(self):
        if self.cntr < self.numImages -1:
            self.cntr += 1
            self._changeImage()
        else:
            QtWidgets.QMessageBox.warning(self, 'Sorry', 'No more Images!')

    def prevImg(self):
        if self.cntr >= 0:
            self.cntr -= 1
            self._changeImage()
        else:
            QtWidgets.QMessageBox.warning(self, 'Sorry', 'No previous Image!')

    def update_label_list(self,name):
        labels = {}
        for i in range(self.dataset.nlabels):
            item = self.ls_labels.itemWidget(self.ls_labels.item(i))
            v = item.currentAddText.text().strip()
            if v == "" or v == "0":
                continue
            try:
                v = int(v)
                labels[item.name] = v
            except:
                continue
        self.dataset.add_frame(name,labels)
        for i in range(self.dataset.nlabels):
            item = self.ls_labels.itemWidget(self.ls_labels.item(i))
            item.currentCountLabel.setText(str(self.dataset.keys[item.name]))
            
    def saveFrame(self):
        if not self.folder:
            self.selectDir()
        if not self.folder:
            return
        idx,fps = self.videoFrameCount, self.fps
        time = str(round(idx/fps,4)).replace(".","_")
        fname = f"{self.videoName}_{str(idx)}"
        imageio.imwrite(f"{self.folder}/{fname}.jpg", self.vidframe)
        if fname not in self.nameItemDict.keys():
            item = QtWidgets.QListWidgetItem(fname)
            self.imagesList += [{"name":fname,"path":f"{self.folder}/{fname}.jpg","qitem": item}]
            self.nameItemDict[fname] = item
            self.qlist_images.addItem(item)
            self.numImages += 1
        else:
            self.nameItemDict[fname].setForeground(QtCore.Qt.black)
            #self.nameItemDict[fname].setSelected(True)
            self.frameNum.setText(f"{self.videoFrameCount}/{self.vidlength}")
            self.cntr = int(self.qlist_images.currentRow())
        self.update_label_list(fname)
        print("Saving")
        self.dataset.save(self.folder)

    def changeImg(self):
        index = int(self.qlist_images.currentRow())
        self.cntr = index
        self._changeImage()
        
        if self.qlist_images.currentItem() is None:
            return
        name = self.qlist_images.currentItem().text()
        #frameN = int(name.split("frame",""))
        #self.videoFrameCount = frameN
        #self.frameNum.setText(f"{self.videoFrameCount}/{self.vidlength}")

        labels = {}
        if name in self.dataset.frames:
            labels = self.dataset.frames[name]
        for i in range(self.dataset.nlabels):
            item = self.ls_labels.itemWidget(self.ls_labels.item(i))
            if item.name in labels:
                item.currentAddText.setText(str(labels[item.name])) 
            else:
                item.currentAddText.setText("0") 

    def update_data_for_label(self):
        if self.ls_labels.currentItem() is None:
            return
        
        idx = int(self.ls_labels.currentRow())
        item = self.ls_labels.itemWidget(self.ls_labels.item(idx))
        label = item.name
        
        self.updateImageList(label=label,reload=False)
        
    def itemClick(self, item):
        self.cntr = int(self.qlist_images.currentRow())
        self._changeImage()

    def _changeImage(self):
        if len(self.currentImgs) <= 0:
            return
        if os.path.exists(self.currentImgs[self.cntr]['path']):
            self.image_viewer.loadImage(self.currentImgs[self.cntr]['path'])
        else:
            self.image_viewer.loadImage(f"{DIR}/icons/noShowDetails.png")

    def keyPressEvent(self, e):
        if e.key()  == QtCore.Qt.Key_P:
            self.delete_img()
        if e.key()  == QtCore.Qt.Key_Right:
            self.nextFrame()
        if e.key()  == QtCore.Qt.Key_Left:
            self.prevFrame()
        if e.key()  == QtCore.Qt.Key_S and self.locked:
            self.saveFrame()

    def goToFrame(self):
        if not self.videoLoaded:
            return
        jumpTo = int(self.selectFrame.text())
        if jumpTo >= 0 and jumpTo < self.vidlength:
            self.videoFrameCount = jumpTo
            self.frameNum.setText(f"{self.videoFrameCount}/{self.vidlength}")
            self.loadVideoFrame()
            self.update_labels()

    def update_labels(self):
        idx = self.videoFrameCount
        fname = "frame"+str(idx)
        labels = {}
        if fname in self.dataset.frames.keys():
            labels = self.dataset.frames[fname]
        for i in range(self.dataset.nlabels):
            item = self.ls_labels.itemWidget(self.ls_labels.item(i))
            
            if item.name in labels:
                item.currentAddText.setText(str(labels[item.name]))
            else:
                item.currentAddText.setText("0")
def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle(QtWidgets.QStyleFactory.create("Cleanlooks"))
    app.setPalette(QtWidgets.QApplication.style().standardPalette())
    parentWindow = Iwindow(None)
    sys.exit(app.exec_())

if __name__ == "__main__":
    print(__doc__)
    main()
