# Defines a class - DataCube - for storing / accessing / manipulating the 4D-STEM data
#
# Datacube objects can be generated by the reader() function, which accepts a filepath and outputs
# a Datacube.
# Datacube objects are saved as .h5 files. The writer() function accepts a Datacube, and spit out
# a .h5.
#
#
### A note on metadata ##
# Metadata exists in 3 different ways in the program.
# (1) At readtime, hyperspy reads in the file and stores metadata in the native hyperspy tree
# structure hyperspy.misc.utils.DictionaryTreeBrowser
# (2) Any metadata that is important to the py4DSTEM will be saved as an attribute in the 
# DataCube object.  The Datacube additionally keeps a copy of the original hyperspy metadata trees
# (3) When saved to a .h5, metadata is copied into a metadata group.  This includes, in separate
# subgroups, both the original hyperspy metadata (in an identical tree structure, written in .h5
# groups/attrs), and the metadata used by py4DSTEM


import hyperspy.api as hs
from hyperspy.misc.utils import DictionaryTreeBrowser
import numpy as np

class DataCube(object):

    def __init__(self, data, R_Ny, R_Nx, Q_Ny, Q_Nx, original_metadata_shortlist=None, original_metadata_all=None, filename=None):
        """
        Instantiate a datacube object. Set the data, scan dimensions, and metadata.
        """
        # Initialize datacube, set dimensions
        self.filename = filename
        self.data4D = data
        self.R_Ny, self.R_Nx = R_Ny, R_Nx
        self.Q_Ny, self.Q_Nx = Q_Ny, Q_Nx
        self.R_N = R_Ny*R_Nx
        self.set_scan_shape(self.R_Ny,self.R_Nx)

        # Handle metadata
        self.setup_metadata(original_metadata_shortlist, original_metadata_all)

    def set_scan_shape(self,R_Ny,R_Nx):
        """
        Reshape the data given the real space scan shape.
        """
        try:
            self.data4D = self.data4D.reshape(self.R_N,self.Q_Ny,self.Q_Nx).reshape(R_Ny,R_Nx,self.Q_Ny,self.Q_Nx)
            self.R_Ny,self.R_Nx = R_Ny, R_Nx
        except ValueError:
            pass

    def get_diffraction_space_view(self,y=0,x=0):
        """
        Returns the image in diffraction space, and a Bool indicating success or failure.
        """
        self.x,self.y = x,y
        try:
            return self.data4D[y,x,:,:].T, 1
        except IndexError:
            return 0, 0

    def get_real_space_view(self,slice_y,slice_x):
        """
        Returns the image in diffraction space.
        """
        return self.data4D[:,:,slice_y,slice_x].sum(axis=(2,3)).T, 1

    def cropAndBin(self, bin_r, bin_q, crop_r, crop_q, slice_ry, slice_rx, slice_qy, slice_qx):
        # If binning is being performed, edit crop window as neededd

        # Crop data

        # Bin data
        self.bin_diffraction(bin_q)
        self.bin_real(bin_r)
        pass


    def bin_diffraction(self,bin_q):
        """
        Performs binning by a factor of bin_q on data4D.
        """
        if bin_q<=1:
            return
        else:
            assert type(bin_q) is int, "Error: binning factor {} is not an int.".format(bin_q)
            R_Ny,R_Nx,Q_Ny,Q_Nx = self.data4D.shape
            # Ensure array is well-shaped for binning
            if ((Q_Ny%bin_q == 0) and (Q_Nx%bin_q == 0)):
                pass
            else:
                self.data4D = self.data4D[:,:,:-(Q_Ny%bin_q),:-(Q_Nx%bin_q)]
            self.data4D = self.data4D.reshape(R_Ny,R_Nx,int(Q_Ny/bin_q),bin_q,int(Q_Nx/bin_q),bin_q).sum(axis=(3,5))
            return

    def bin_real(self,bin_r):
        """
        Performs binning by a factor of bin_r on data4D.
        """
        if bin_r<=1:
            return
        else:
            assert type(bin_r) is int, "Error: binning factor {} is not an int.".format(bin_r)
            R_Ny,R_Nx,Q_Ny,Q_Nx = self.data4D.shape
            # Ensure array is well-shaped for binning
            if ((R_Ny%bin_r == 0) and (R_Nx%bin_r == 0)):
                pass
            else:
                self.data4D = self.data4D[:-(R_Ny%bin_r),:-(R_Nx%bin_r),:,:]
            self.data4D = self.data4D.reshape(int(R_Ny/bin_r),bin_r,int(R_Nx/bin_r),bin_r,Q_Ny,Q_Nx).sum(axis=(1,3))
            return


    ###################### METADATA HANDLING ########################

    def setup_metadata(self, original_metadata_shortlist=None, original_metadata_all=None):
        """
        Metadata is structured as follows:
        In datacube instance d = Datacube() contains an empty class called d.metadata.
        d.metadata contains:
            -an empty class called d.metadata.original, containing two
             hyperspy.misc.utils.DictionaryTreeBrowser objects with the original metadata.
            -five dictionary objects with all metadata which this program uses, either scraped
             from the original metadata or generated by other means
        """
        self.metadata = MetadataCollection('metadata')
        self.metadata.original = MetadataCollection('original')
        self.metadata.original.shortlist = original_metadata_shortlist
        self.metadata.original.all = original_metadata_all
        self.metadata.microscope = dict()
        self.metadata.sample = dict()
        self.metadata.user = dict()
        self.metadata.processing = dict()
        self.metadata.calibration = dict()
        self.metadata.comments = dict()

        self.setup_metadata_search_dicts()

        # Get metadata from original metadata. Search first the complete list, then the shortlist,
        # so any shortlist values present will overwrite the complete items.
        self.get_metadata_from_original_metadata(original_metadata_all, self.original_to_microscope_search_dict, self.metadata.microscope)
        self.get_metadata_from_original_metadata(original_metadata_all, self.original_to_sample_search_dict, self.metadata.sample)
        self.get_metadata_from_original_metadata(original_metadata_all, self.original_to_user_search_dict, self.metadata.user)
        self.get_metadata_from_original_metadata(original_metadata_all, self.original_to_processing_search_dict, self.metadata.processing)
        self.get_metadata_from_original_metadata(original_metadata_all, self.original_to_calibration_search_dict, self.metadata.calibration)
        self.get_metadata_from_original_metadata(original_metadata_all, self.original_to_comments_search_dict, self.metadata.comments)

        self.get_metadata_from_original_metadata(original_metadata_shortlist, self.original_to_microscope_search_dict, self.metadata.microscope)
        self.get_metadata_from_original_metadata(original_metadata_shortlist, self.original_to_sample_search_dict, self.metadata.sample)
        self.get_metadata_from_original_metadata(original_metadata_shortlist, self.original_to_user_search_dict, self.metadata.user)
        self.get_metadata_from_original_metadata(original_metadata_shortlist, self.original_to_processing_search_dict, self.metadata.processing)
        self.get_metadata_from_original_metadata(original_metadata_shortlist, self.original_to_calibration_search_dict, self.metadata.calibration)
        self.get_metadata_from_original_metadata(original_metadata_shortlist, self.original_to_comments_search_dict, self.metadata.comments)

    @staticmethod
    def get_metadata_from_original_metadata(hs_tree, metadata_search_dict, metadata_dict):
        """
        Finds the relavant metadata in the original_metadata objects and populates the
        corresponding DataCube instance attributes.
        Accepts:
            hs_tree -   a hyperspy.misc.utils.DictionaryTreeBrowser object
            metadata_search_dict -  a dictionary with the attributes to search and the keys
                                    under which to find them
            metadata_dict - a dictionary to put the found key:value pairs into
        """
        for attr, keys in metadata_search_dict.items():
            metadata_dict[attr]=""
            for key in keys:
                found, value = DataCube.search_hs_tree(key, hs_tree)
                if found:
                    metadata_dict[attr]=value
                    break

    @staticmethod
    def search_hs_tree(key, hs_tree):
        """
        Searchers heirachically through a hyperspy.misc.utils.DictionaryBrowserTree object for
        an attribute named 'key'.
        If found, returns True, Value.
        If not found, returns False, -1.
        """
        if hs_tree is None:
            return False, -1
        else:
            for hs_key in hs_tree.keys():
                if not DataCube.istree_hs(hs_tree[hs_key]):
                    if key==hs_key:
                        return True, hs_tree[hs_key]
                else:
                    found, val = DataCube.search_hs_tree(key, hs_tree[hs_key])
                    if found:
                        return found, val
            return False, -1

    @staticmethod
    def istree_hs(node):
        if type(node)==DictionaryTreeBrowser:
            return True
        else:
            return False

    def setup_metadata_search_dicts(self):
        """
        Make dictionaties for searching/scraping/populating the active metadata dictionaries
        from the original metadata.
        Keys become the keys in the final, active metadata dictioaries; values are lists
        containing the corresponding keys to find in the hyperspy trees of the original metadata.
        These objects live in the DataCube class scope.

        Note that items that are not found will still be stored as a key in the relevant metadata
        dictionary, with the empty string as its value.  This allows these fields to populate
        in the relevant places - i.e. the metadata editor dialog. Thus any desired fields which
        will not be in the original metadata should be entered as keys with an empty seach list.
        """
        self.original_to_microscope_search_dict = {
            'accelerating_voltage_kV' : [ 'beam_energy' ],
            'camera_length_mm' : [ 'camera_length' ],
            'C2_aperture' : [ '' ],
            'convergence_semiangle_mrad' : [ '' ],
            'spot_size' : [ '' ],
            'scan_rotation_degrees' : [ '' ],
            'dwell_time_ms' : [ '' ],
            'scan_size_Ny' : [ '' ],
            'scan_size_Nx' : [ '' ],
            'R_pix_size' : [ '' ],
            'R_units' : [ '' ],
            'K_pix_size' : [ '' ],
            'K_units' : [ '' ],
            'probe_FWHM_nm' : [ '' ]
        }

        self.original_to_sample_search_dict = {
            'sample_metadata_1' : [ '' ],
            'sample_metadata_2' : [ '' ],
            'sample_metadata_3' : [ '' ]
        }

        self.original_to_user_search_dict = {
            'user_metadata_1' : [ '' ],
            'user_metadata_2' : [ '' ],
            'user_metadata_3' : [ '' ]
        }

        self.original_to_processing_search_dict = {
            'original_filename' : [ 'original_filename' ]
        }

        self.original_to_calibration_search_dict = {
            'calibration_metadata_1' : [ '' ],
            'calibration_metadata_2' : [ '' ],
            'calibration_metadata_3' : [ '' ]
        }

        self.original_to_comments_search_dict = {
            'comments_metadata_1' : [ '' ],
            'comments_metadata_2' : [ '' ],
            'comments_metadata_3' : [ '' ]
        }

    @staticmethod
    def add_metadata_item(key,value,metadata_dict):
        """
        Adds a single item, given by the pair key:value, to the metadata dictionary metadata_dict
        """
        metadata_dict[key] = value

################## END OF DATACUBE OBJECT ################



class MetadataCollection(object):
    """
    Empty container for storing metadata.
    """
    def __init__(self,name):
        self.__name__ = name



