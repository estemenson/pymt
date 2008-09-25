from random import randint
from pyglet.gl import *

from pymt import drawLine



def drawVertex(x,y):
       glPushMatrix()
       glTranslated(x,y, 0)
       glColor3d(1.0,1.0,1.0)
       gluDisk(gluNewQuadric(), 0, 20, 32,1)
       glScaled(0.75,0.75,1.0)
       glColor3d(0.0,0.0,1.0)
       gluDisk(gluNewQuadric(), 0, 20, 32,1)
       glPopMatrix()



class Graph(object):
       def __init__(self, num_verts=12, displaySize=(640,480)):
              self.verts = []
              for i in range(num_verts):
                     x = randint(100,displaySize[0]-100)*1.0
                     y = randint(100,displaySize[1]-100)*1.0
                     self.verts.append([x,y])
              
              self.edges = [ [self.verts[i], self.verts[(i+1)%num_verts]] for i in range(num_verts) ]
     
       def draw(self):
              for e in self.edges:
                     drawLine([e[0], e[1]])
              for v in self.verts:
                     drawVertex(v[0],v[1])
                     
       #returns the vertex at the position, None if no vertex there
       def collideVerts(self, x,y, regionSize=35):
              for v in self.verts:
                     dx = abs(x - v[0])
                     dy = abs(y - v[1])
                     if (dx < regionSize and dy < regionSize):
                         print "collision"
                         return v
              return None


if __name__ == "__main__":
	print "this is an implementation file only used by untabgle.py"
