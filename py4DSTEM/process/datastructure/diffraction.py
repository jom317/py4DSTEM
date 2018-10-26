# Defines a class - DiffractionSlice - for storing / accessing / manipulating data that lives in
# diffraction space.
#
# DiffractionSlice objects are generated from parent DataCube objects with various processing
# functions, and must contain a reference to their parent DataCube instance.

class DiffractionSlice(object):

    def __init__(self, parentDataCube, data):
        """
        Instantiate a DiffractionSlice object.  Set the parent datacube, dimensions, and data.
        Confirms that the data shape agrees with diffraction space of the parent datacube.
        """
        self.parentDataCube = parentDataCube
        self.Q_Ny, self.Q_Nx = self.parentDataCube.Q_Ny, self.Q_Nx
        assert data.shape == (self.Q_Ny,self.Q_Nx), "Shape of data is {}, but shape of diffraction space in parent DataCube is ({},{}).".format(data.shape,self.Q_Ny,self.Q_Nx)
        self.data2D = data


