#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''a ripple effect using vertex shader'''


import sys

import PySide
from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtOpenGL import *

from OpenGL.GL import *
from OpenGL.GL import shaders

import numpy as np

def shaderFromFile(shaderType, shaderFile):
    '''create shader from file'''
    shaderSrc = ''
    with open(shaderFile) as sf:
        shaderSrc = sf.read()
    return shaders.compileShader(shaderSrc, shaderType)

class FreeCamera(object):
    '''a free camera'''
    def __init__(self):
        self.__up = QVector3D(0, 1, 0) # Y axis
        self.__viewDirection = QVector3D(0, 0, -1) # Z axis
        self.__rightAxis = QVector3D() # X axis
        
        # camera position
        self.position = QVector3D()
        self.rotatetion = QVector3D()
        
        # check mouse position
        self.__oldMP = QPoint()
        
        # camera rotate speed
        self.rotateSpeed = .1
        
        self.projection = QMatrix4x4()
        
    def perspective(self, fov, aspect, nearPlane=0.1, farPlane=1000.):
        self.projection.setToIdentity()
        self.projection.perspective(fov, aspect, nearPlane, farPlane)
        
    def getWorldToViewMatrix(self):
        mat = QMatrix4x4()
        mat.lookAt(self.position, self.position + self.__viewDirection, self.__up)
        mat.rotate(self.rotatetion.x(), 1, 0, 0)
        mat.rotate(self.rotatetion.y(), 0, 1, 0)
        mat.rotate(self.rotatetion.z(), 0, 0, 1)
        
        return mat
    
    def updateMouse(self, pos, update=False):
        if update:
            mouseDelta = pos - self.__oldMP
            
            mat = QMatrix4x4()
            mat.rotate(-mouseDelta.x() * self.rotateSpeed, self.__up)
            
            self.__viewDirection = self.__viewDirection * mat
            self.__rightAxis = QVector3D.crossProduct(self.__viewDirection, self.__up)
            mat.setToIdentity()
            mat.rotate(-mouseDelta.y() * self.rotateSpeed, self.__rightAxis)
            self.__viewDirection = self.__viewDirection * mat
        
        self.__oldMP = pos
        
    def forward(self):
        self.position += self.__viewDirection
    
    def backward(self):
        self.position -= self.__viewDirection
        
    def liftUp(self):
        self.position += self.__up
        
    def liftDown(self):
        self.position -= self.__up
        
    def strafeLeft(self):
        self.position -= self.__rightAxis
        
    def strafeRight(self):
        self.position += self.__rightAxis


class MyGLWidget(QGLWidget):
    
    def __init__(self, gformat, parent=None):
        super(MyGLWidget, self).__init__(gformat, parent)
        
        # buffer object ids
        self.vaoID = None
        self.vboVerticesID = None
        self.vboIndicesID = None
        self.sprogram = None
        
        self.vertices = None
        self.indices = None
        
        # grid width and height
        self.gwidth = 20
        self.gheight = 20
        
        # camera
        self.camera = FreeCamera()
        self.state = False
        
        # set window size to the images size
        self.setGeometry(40, 40, 640, 480)
        # set window title
        self.setWindowTitle('Dispaly - ')
        self.setMouseTracking(True)
    
    def initializeGL(self):
        glClearColor(0, 0, 0, 0)
        
        # create shader from file
        vshader = shaderFromFile(GL_VERTEX_SHADER, 'shader.vert')
        fshader = shaderFromFile(GL_FRAGMENT_SHADER, 'shader.frag')
        # compile shaders
        self.sprogram = shaders.compileProgram(vshader, fshader)
        
        # get attribute and set uniform for shaders
        glUseProgram(self.sprogram)
        self.vertexAL = glGetAttribLocation(self.sprogram, 'pos')
        self.mvpUL = glGetUniformLocation(self.sprogram, 'MVP')
        self.tmUL = glGetUniformLocation(self.sprogram, 'time')
        glUniform1f(self.tmUL, 0.)
        glUseProgram(0)
        
        # create a grid
        gw2 = self.gwidth / 2
        gh2 = self.gheight / 2
        vertices = []
        for i in xrange(-gw2, gw2 + 1):
            vertices.append((i, 0, -gh2))
            vertices.append((i, 0, gh2))
            vertices.append((-gw2, 0, i))
            vertices.append((gw2, 0, i))
        self.vertices = np.array(vertices, dtype=np.float32)
        
        # grid indices
        indices = []
        for i in xrange(0, self.gwidth * self.gheight, 4):
            indices.append(i)
            indices.append(i + 1)
            indices.append(i + 2)
            indices.append(i + 3)
        self.indices = np.array(indices, dtype=np.ushort)
        
        # set up vertex array
        self.vaoID = glGenVertexArrays(1)
        self.vboVerticesID = glGenBuffers(1)
        self.vboIndicesID = glGenBuffers(1)
        
        glBindVertexArray(self.vaoID)
        glBindBuffer(GL_ARRAY_BUFFER, self.vboVerticesID)
        # copy vertices data from memery to gpu memery
        glBufferData(GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, GL_STATIC_DRAW)
        # tell opengl how to procces the vertices data
        glEnableVertexAttribArray(self.vertexAL)
        glVertexAttribPointer(self.vertexAL, 3, GL_FLOAT, GL_FALSE, 0, None)
        # send the indice data too
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.vboIndicesID)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.indices.nbytes, self.indices, GL_STATIC_DRAW)
        
        # set camera position
        self.camera.position = QVector3D(0, 2, 45)
        self.camera.rotatetion = QVector3D(30, 30, 0)
        
        print("Initialization successfull")
        
    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        self.camera.perspective(45., float(w) / h)
        
    def paintGL(self, *args, **kwargs):
        # clear the buffers
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        mvp = self.camera.projection * self.camera.getWorldToViewMatrix() #* modelMat
        mvp = np.array(mvp.copyDataTo(), dtype=np.float32)
        
        # active shader
        glUseProgram(self.sprogram)
        glUniformMatrix4fv(self.mvpUL, 1, GL_TRUE, mvp)
        # draw triangles
        glDrawElements(GL_LINES, self.indices.size, GL_UNSIGNED_SHORT, None)
        glUseProgram(0)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.state = True
            self.camera.updateMouse(event.pos(), self.state)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.state = False
            self.camera.updateMouse(event.pos(), self.state)
        
    def mouseMoveEvent(self, event):
        pos = event.pos()
        self.camera.updateMouse(pos, self.state)
        self.updateGL()
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_W:
            self.camera.forward()
        elif event.key() == Qt.Key_S:
            self.camera.backward()
        elif event.key() == Qt.Key_A:
            self.camera.strafeLeft()
        elif event.key() == Qt.Key_D:
            self.camera.strafeRight()
        elif event.key() == Qt.Key_Q:
            self.camera.liftUp()
        elif event.key() == Qt.Key_Z:
            self.camera.liftDown()
        self.updateGL()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gformat = QGLFormat()
    gformat.setVersion(4, 3)
    gformat.setProfile(QGLFormat.CoreProfile)
    mywidget = MyGLWidget(gformat)
    mywidget.show()
    
    # print information on screen
    sys.stdout.write("\tUsing PySide " + PySide.__version__)
    sys.stdout.write("\n\tVendor: " + glGetString(GL_VENDOR))
    sys.stdout.write("\n\tRenderer: " + glGetString(GL_RENDERER))
    sys.stdout.write("\n\tVersion: " + glGetString(GL_VERSION))
    sys.stdout.write("\n\tGLSL: " + glGetString(GL_SHADING_LANGUAGE_VERSION))
    
    sys.exit(app.exec_())
