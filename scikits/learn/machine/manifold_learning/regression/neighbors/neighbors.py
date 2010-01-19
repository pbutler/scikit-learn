"""
k-Nearest Neighbor Algorithm
"""

# Last changes:
# Matthieu Brucher, 2008-04-15 10:55
# Fabian Pedregosa, Tue Jan 19 09:51:23 2010

from numpy.ctypeslib import ndpointer, load_library
from scipy.stats import mode
import math
import numpy as np
import sys
import ctypes

# Load the library
#if sys.platform == 'win32':
#  _neighbors = load_library('neighbors', "\\".join(__file__.split("\\")[:-1]) + "\\release")
#else:
_neighbors = load_library('_neighbors', __file__)

_neighbors.allocate_neighborer.restype = ctypes.c_void_p
_neighbors.allocate_neighborer.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]

_neighbors.delete_neighborer.restype = ctypes.c_int
_neighbors.delete_neighborer.argtypes = [ctypes.c_void_p]

CALLBACK = ctypes.CFUNCTYPE(ctypes.c_ulong, ctypes.c_double, ctypes.c_ulong)

_neighbors.find_kneighbors.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_double), ctypes.c_ulong, ctypes.c_ulong, CALLBACK]
_neighbors.find_parzen.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_double), ctypes.c_ulong, ctypes.c_double, CALLBACK]

class Neighbors:
  """
  Classifier implementing k-Nearest Neighbor Algorithm.

  Parameters
  ----------
  points : matrix
      A matrix representing the points int the population space.
  labels : array
      An array representing labels for the data (only arrays of
      integers are supported).
  k : int
      default number of neighbors.
  window_size : float
      the default window size.


  Examples
  --------
  >>> samples = [[0.,0.,1.], [1.,0.,0.], [2.,2.,2.], [2.,5.,4.]]
  >>> labels = [0,0,1,1]
  >>> neigh = Neighbors(samples, labels=labels)
  >>> print neigh.predict([[0,0,0]])
  [ 0.]

  Notes
  -----
  Core algorithm is written in C++, this class is a ctypes wrapper
  around the neighbors tree.
  """
  def __init__(self, samples, labels, k = 1, window_size = 1.):
    """
    Creates the tree, with a number of level depending on the log of
    the number of elements and the number of coordinates
    """
    self._k = k
    self.window_size = window_size
    self.points = np.ascontiguousarray(samples) # needed for saving the state
    self.labels = np.array(labels)
    self._neigh = _neighbors.allocate_neighborer(self.points.ctypes.data_as(ctypes.POINTER(ctypes.c_double)), self.points.shape[0], self.points.shape[1], int(math.log(self.points.shape[0]) / (self.points.shape[1] * math.log(2))))

  def __getinitargs__(self):
    """
    Returns the state of the neighboorhood
    """
    return (self.points, self._k, self.window_size)

  def __setstate__(self, state):
    pass

  def __getstate__(self):
    return {}

  def __del__(self, close_func = _neighbors.delete_neighborer):
    """
    Deletes the cost function
    """
    if not (self._neigh == 0):
      close_func(self._neigh)
      self._neigh = 0

  def kneighbors(self, point, k=None):
    """
    Finds the K-neighbors of a point.

    Parameters
    ----------
    point : array
        The new point.
    k : int
        Number of neighbors to get (default is the value
        passed to the constructor).

    Returns
    -------
    dist : array
        Array representing the lenghts to point.
    ind : array
        Array representing the indices of the nearest points in the
        population matrix.


    Examples
    --------
    In the following example, we construnct a Neighbors class from an
    array representing our data set and ask who's the closest point to
    [1,1,1]

    >>> import numpy as np
    >>> samples = [[0., 0., 0.], [0., .5, 0.], [1., 1., .5]]
    >>> neigh = Neighbors(samples, labels=[0,0,1], k=2)
    >>> print neigh.kneighbors([1., 1., 1.])
    ([0.5, 1.5], [2L, 1L])

    As you can see, it returns [0.5], and [2], which means that the
    element is at distance 0.5 and is the third element of samples
    (indexes start at 0).
    """
    if k is None: k = self._k
    point = np.asarray(point)

    self.dist, self.ind = [], []
    _neighbors.find_kneighbors(self._neigh, point.ctypes.data_as(ctypes.POINTER(ctypes.c_double)), len(point), k, CALLBACK(self.callback))
    return self.dist, self.ind


  def parzen(self, point, window_size=None):
    """
    Finds the neighbors of a point in a Parzen window
    Parameters :
      - point is a new point
      - window_size is the size of the window (default is the value passed to the constructor)
    """
    if window_size is None: window_size = self.window_size

    self.dist, self.ind = [], []
    _neighbors.find_parzen(self._neigh, point.ctypes.data_as(ctypes.POINTER(ctypes.c_double)), len(point), window_size, CALLBACK(self.callback))
    return self.dist, self.ind


  def callback(self, distance, indice):
    """
    Callback for the searchs, populates self.results.

    Parameters :
      - distance is the distance of the point to another point
      - indice is the indice of the other point
    """
    self.dist.append(distance)
    self.ind.append(indice)
    return len(self.dist)


  def predict(self, data):
    """
    Predict the class labels for the provided data.

    Parameters
    ----------
    data: matrix
        An array representing the test point.

    Returns
    -------
    labels: array
        List of class labels (one for each data sample).

    Examples
    --------

    >>> import numpy as np
    >>> labels = [0,0,1]
    >>> samples = [[0., 0., 0.], [0., .5, 0.], [1., 1., .5]]
    >>> neigh = Neighbors(samples, labels=labels)
    >>> print neigh.predict([[.2, .1, .2]])
    [ 0.]
    """
    data = np.asmatrix(data)
    res = np.zeros(len(data))
    for i, point in enumerate(data):
      dist, ind = self.kneighbors(point)
      res[i] = mode(self.labels[ind])[0]
    return res

class Kneighbors(Neighbors):
  """
  Wrapper for K-neighbors only
  """
  __call__ = Neighbors.kneighbors


class Parzen(Neighbors):
  """
  Wrapper for Parzen Window only
  """
  __call__ = Neighbors.parzen