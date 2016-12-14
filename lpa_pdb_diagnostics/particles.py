import cPickle as pickle
import numpy as np
import math
import sys
from scipy.constants import e, c
from scipy.signal import find_peaks_cwt
import pdb
from generics import gamma2Energy, leftRightFWHM, bilinearInterpolation, w2charge
import result_path as rp
from pylab import plt
from file_handling import FileWriting
import matplotlib
import pdb

try:
    import pandas as pd
except ImportError:
    print "If you wish to use pandas to manipulate your data,\
    please install the module follwing the instruction on this \
    website http://pandas.pydata.org/pandas-docs/stable/install.html"
    pass

class ParticleInstant():

    def __init__(self, filename,
            quantities = ["PID", "Weight", "Position", "Momentum", "E", "B"]):
        """
        Initialize an instant of particles.

        Parameters:
        -----------

        file: a string
            Name of the file including the path
        quantities: a 1D array
            Specify the particle quantities to be initialized

        """

        print "** Processing ** Particles: Initialisation of "+str(filename)+" **"

        with open( filename ) as pickle_file:
            tmp = pickle.load( pickle_file )

        self.quantities = quantities
        self.num_quantities = 0
        self.qdict = {}

        if "pandas" in sys.modules.keys():
            self.pandas = True
            frame = []

        for quantity in self.quantities:
            if quantity == "PID":
                self.ssn = np.array(tmp["ssnum"]).astype(int)
                self.qdict["PID"] = self.num_quantities
                self.num_quantities += 1
                if self.pandas:
                    PID = pd.DataFrame({"PID": self.ssn})
                    frame.append(PID)

            if quantity == "Weight":
                self.w = np.array(tmp["w"])#*tmp(sw)
                self.qdict["w"] = self.num_quantities
                self.num_quantities += 1
                if self.pandas:
                    w = pd.DataFrame({"Weight": self.w})
                    frame.append(w)

            if quantity == "Position":
                self.x = np.array(tmp["x"])
                self.y = np.array(tmp["y"])
                self.z = np.array(tmp["z"])

                self.qdict["x"] = self.num_quantities
                self.qdict["y"] = self.num_quantities + 1
                self.qdict["z"] = self.num_quantities + 2
                self.num_quantities += 3

                if self.pandas:
                    pos = pd.DataFrame({"x": self.x,
                                        "y": self.y,
                                        "z": self.z})
                    frame.append(pos)

            if quantity == "Momentum":
                self.ux = np.array(tmp["ux"])
                self.uy = np.array(tmp["uy"])
                self.uz = np.array(tmp["uz"])
                self.gamma = np.sqrt(1. + self.ux**2 + self.uy**2 + self.uz**2)

                self.qdict["ux"] = self.num_quantities
                self.qdict["uy"] = self.num_quantities + 1
                self.qdict["uz"] = self.num_quantities + 2
                self.qdict["gamma"] = self.num_quantities + 3
                self.num_quantities += 4

                if self.pandas:
                    momentum = pd.DataFrame({"ux": self.ux,
                                        "uy": self.uy,
                                        "uz": self.uz,
                                        "gamma": self.gamma})
                    frame.append(momentum)

            if quantity == "E":
                self.ex = np.array(tmp["ex"])
                self.ey = np.array(tmp["ey"])
                self.ez = np.array(tmp["ez"])

                self.qdict["ex"] = self.num_quantities
                self.qdict["ey"] = self.num_quantities + 1
                self.qdict["ez"] = self.num_quantities + 2
                self.num_quantities += 3

                if self.pandas:
                    Efield = pd.DataFrame({"ex": self.ex,
                                        "ey": self.ey,
                                        "ez": self.ez})
                    frame.append(Efield)

            if quantity == "B":
                self.bx = np.array(tmp["bx"])
                self.by = np.array(tmp["by"])
                self.bz = np.array(tmp["bz"])

                self.qdict["bx"] = self.num_quantities
                self.qdict["by"] = self.num_quantities + 1
                self.qdict["bz"] = self.num_quantities + 2
                self.num_quantities += 3

                if self.pandas:
                    Bfield = pd.DataFrame({"bx": self.bx,
                                        "by": self.by,
                                        "bz": self.bz})
                    frame.append(Bfield)

        if self.pandas:
            self.df = pd.concat(frame, axis = 1 )

    def get_qdict( self ):
        """
        returns qdict for reference purpose
        """

        return self.qdict

    def select( self, gamma_threshold = None, ROI = None ):
        """
        This method selects the particles according to the energy and
        region of interest
        Example of usage:
            Instant.filter(gamma = [50, 100], ROI = [2000e-6, 3000e-6])
            Particles that meet these cited conditions will be chosen.

        Parameters:
        -----------
        gamma: a 1D array of shape 2
            consists of the lower bound and the upper bound in gamma
        ROI : a 1D array of shape 2
            consists of the lower bound and the upper bound in terms of
            position

        Returns:
        --------
        selected: a dictionary of quantities
            Quantities of the chosen particles
        """
        #Check if there's any particle
        try:
            indexListGamma = set()
            indexListROI = set()
            n_array = np.arange(len(self.ssn))

            if gamma_threshold:
                #Test the gamma_threshold structure
                countValidAgg = 0

                if len(gamma_threshold)!=2:
                    raise "gamma_threshold should be a 1D array of size 2."

                for agg in gamma_threshold:
                    if agg is not None:
                        countValidAgg+=1

                if countValidAgg == 1:
                    indexListGamma = set(np.compress(self.gamma>gamma_threshold[0],
                    n_array))

                else:
                    indexListGamma = set(np.compress(
                    np.logical_and(self.gamma>gamma_threshold[0],
                    self.gamma<gamma_threshold[1]), n_array))

            if ROI:
                #Test the ROI structure
                countValidAgg = 0

                if len(ROI)!=2:
                    raise "ROI should be a 1D array of size at least 1."

                for agg in ROI:
                    if agg is not None:
                        countValidAgg+=1

                if countValidAgg == 1:
                    indexListROI = set(np.compress(self.z>ROI[0],
                    n_array))

                else:
                    indexListROI = set(np.compress(
                    np.logical_and(self.z>ROI[0],
                    self.z<ROI[1]), n_array))

            if gamma_threshold and ROI:
                indexList = list(indexListGamma.intersection(indexListROI))
            elif gamma_threshold:
                indexList = list(indexListGamma)
            elif ROI:
                indexList = list(indexListROI)
            else:
                indexList = list(n_array)

            return self.filterwithIndexList( indexList )

        except ValueError:
            print "No particles are detected"
            return

    def filterwithIndexList(self, indexList):
        """
        Return a dictionary of selected particles.

        Parameters:
        -----------
        indexList: a 1D array
            contains the index of chosen particles

        Returns:
        --------
        chosenParticles: a 2D Numpy Array
            contains the quantity of chosen particles

        """
        chosenParticles = [[] for i in xrange(self.num_quantities)]
        index = 0

        for quantity in self.quantities:
            if quantity == "PID":
                chosenParticles[index] = self.ssn[indexList].astype(int)

            if quantity == "Weight":
                index += 1
                chosenParticles[index] = self.w[indexList]

            if quantity == "Position":
                index += 3
                chosenParticles[index - 2] = self.x[indexList]
                chosenParticles[index - 1] = self.y[indexList]
                chosenParticles[index] = self.z[indexList]

            if quantity == "Momentum":
                index += 4
                chosenParticles[index - 3] = self.ux[indexList]
                chosenParticles[index - 2] = self.uy[indexList]
                chosenParticles[index - 1] = self.uz[indexList]
                chosenParticles[index] = self.gamma[indexList]

            if quantity == "E":
                index += 3
                chosenParticles[index - 2] = self.ex[indexList]
                chosenParticles[index - 1] = self.ey[indexList]
                chosenParticles[index ] = self.ez[indexList]

            if quantity == "B":
                index += 3
                chosenParticles[index - 2] = self.bx[indexList]
                chosenParticles[index - 1] = self.by[indexList]
                chosenParticles[index] = self.bz[indexList]

        return chosenParticles

def beam_charge( w ):
    """
    Returns the beam charge of the chosen particles.

    Parameters:
    -----------
    w : 1D array
        Weight of particles

    Returns:
    --------
    Charge: float value (in Coulomb)
    """
    try:
        s_charge = w2charge(w)
        charge = np.sum(s_charge)
    except ValueError:
        charge = 0.0

    return charge

def beam_spectrum( frame_num, gamma, w, lwrite = False,
                    bin_size = 0.5, density = False, lsavefig = True,
                    leg = None):
    """
    Returns the beam spectrum of the chosen particles.

    Parameters:
    -----------
    frame_num: int
        frame_num for writing purpose

    gamma: 2D numpy array
        gamma of particles for different species

    w: 2D numpy array
        Weight of particles for different species

    bin_size: int
        in MeV, default value 0.5 MeV

    density: boolean
        whether to normalize the spectrum, default value False

    lsavefig: boolean
        flag to save figure or not

    legend: 1D string list
        legend for the figure

    Returns:
    --------
    energy: float value
        binned energy in MeV

    dQdE: float value
        charge in Coulomb/MeV
    """
    try:
        num_species = len(gamma)
        energy = []
        dQdE = []

        for index in xrange(num_species):
            en = gamma2Energy(gamma[index])
            bins = int((np.max(en) - np.min(en))/bin_size)
            temp_dQdE, temp_energy = np.histogram( en, bins = bins,
                        weights = w[index] , density = density)
            temp_dQdE *= e
            temp_energy = np.delete( temp_energy, 0 ) # removing the first element
            dQdE.append(temp_dQdE)
            energy.append(temp_energy)

        index_largest_dynamics = np.argmax( map(lambda x: np.max(x) - np.min(x),
                                 energy))
        ref_energy = energy[index_largest_dynamics]

        dQdE_interp = []

        for index in xrange(num_species):
            dQdE_interp.append(np.interp(ref_energy, energy[index], dQdE[index]))

        #this is to store the contribution of all species to the spectrum
        dQdE.append(np.sum( dQdE_interp[0:num_species], axis = 0 ))
        energy.append(ref_energy)

        if 'inline' in matplotlib.get_backend():
            fig, ax = plt.subplots(dpi=150)
        else:
            fig, ax = plt.subplots( dpi = 500 )

        fig.patch.set_facecolor('white')
        c = [ "blue","red","black", "green", "magenta" ]

        for i in xrange(num_species + 1):
            if leg is not None:
                ax.plot( energy[i], dQdE[i], color = c[i%num_species],
                label = leg[i])
            else:
                ax.plot( energy[i], dQdE[i], color = c[i%num_species] )

        ax.set_xlabel(r"$\mathrm{Energy[MeV]}$")
        ax.set_ylabel(r"$\mathrm{dQdE[C/MeV]}$")
        font = {'family':'sans-serif'}
        plt.rc('font', **font)

        if leg is not None:
            # Now add the legend with some customizations.
            legend = plt.legend(loc='best', shadow=True)

            # Set the fontsize
            for label in legend.get_texts():
                label.set_fontsize('large')

            for label in legend.get_lines():
                label.set_linewidth(1.5)  # the legend line width

        if lwrite:
            gname = np.arange(num_species + 1).astype('str')
            qname = ["energy", "dQdE"]
            f = FileWriting( qname , "beam_spectrum_%d" %frame_num , groups = gname)
            stacked_data = np.stack( (energy, dQdE), axis = 1 )
            f.write( stacked_data, np.shape(stacked_data) , attrs = [ "MeV", "C" ])

        if lsavefig:
            dir_path = rp.ResultPath()
            fig.savefig( dir_path.result_path + "beam_spectrum_%d.png" %frame_num)

    except ValueError:
        print "Check if the particle arrays are empty."
        energy = []
        dQdE = []

    return energy, dQdE

def beam_peak( energy, dQdE, peak_width = 50.0 ):
    """
    returns the index of a peak from a beam spectrum

    Parameters:
    -----------
    energy: a 1D numpy array
        binned energy

    dQdE: a 1D numpy array
        charge density from the beam spectrum

    peak_width: int
        estimated width of the peak, default value 20 MeV

    Returns:
    --------
    peakInd: 1D array
        Indices of the located peak(s)

    energy: 1D array
        Energy of the located peak(s)

    dQdE: 1D array
        Charge density of the located peak(s)

    """
    try:
        bin_size = energy[1] - energy[0]
        num_bin_peak_width = int(peak_width/bin_size)
        peakInd = find_peaks_cwt(dQdE, np.arange(1,num_bin_peak_width))

        return peakInd, energy[peakInd], dQdE[peakInd]

    except ValueError:
        print "No peak is found"

def beam_energy_spread( energy, dQdE, lfwhm = True, peak = None ):
    """
    Calculate the energy spread of the beam.

    Parameters:
    -----------
    energy: 1D array
        binned energy from the spectrum

    dQdE: 1D array
        binned energy from the spectrum

    lfwhm: boolean
        calculate either using FWHM or rsm definition. Default value True

    peak: tuple
        contains peakInd, energy[peakInd], dQdE[peakInd], corresponding to the
        output of beam_peak(...). Default peak None

    Returns:
    --------
    deltaE: float
        Energy spread in MeV
    deltaEE: float
        Energy spread in decimal value

    """
    try:
        if peak is None:
            average_energy = np.average( energy, weights = dQdE )
            variance = np.average( (energy - average_energy)**2, weights = dQdE )
            deltaE = np.sqrt( variance )
            deltaEE = deltaE/average_energy

        else:
            peakInd = peak[0]
            Epeak = peak[1]
            dQdEpeak = peak[2]
            y = np.std( dQdEpeak ) #y in RMS

            if lfwhm:
                y = 0.5*dQdEpeak #y in FWHM

            yleft = dQdE[ 0:peakInd ]
            xleft = energy[ 0:peakInd ]
            yright = dQdE[ peakInd+1:: ]
            xright = energy[ peakInd+1:: ]
            yleftleft, yleftright, yrightleft, yrightright,\
            xleftleft, xleftright, xrightleft, xrightright = \
            leftRightFWHM( yleft, yright, y, xleft, xright )

            #Bilinear interpolation for the left area
            x_left_exact = bilinearInterpolation( yleftleft, yleftright,
            xleftleft, xleftright, y)

            #Bilinear interpolation for the right area
            x_right_exact = bilinearInterpolation( yrightleft, yrightright,
            xrightleft, xrightright, y)

            #Evaluate energy spread, delta E (in MeV)
            deltaE = np.absolute( x_left_exact - x_right_exact )

            #Evaluate energy spread, delta E/Epeak (in decimal)
            deltaEE = deltaE/Epeak

    except ZeroDivisionError:
        print "Error in energy spread calculation"
        deltaE = None
        deltaEE = None

    return deltaE, deltaEE

def beam_emittance( x, ux, w ):
    """
    Calculation on emittance based on statistical approach in J. Buon (LAL)
    Beam phase space and Emittance. We first calculate the covariance, and
    the emittance is epsilon=sqrt(det(covariance matrix)).
    Covariance is calculated with the weighted variance based on
    http://www.itl.nist.gov/div898/software/dataplot/refman2/ch2/weightsd.pdf

    Parameters:
    -----------
    x: 1D array of floats
        coordinates of the beam

    ux: 1D array of floats
        momentum of the beam

    w : 1D array of floats
        weight of the beam

    Return:
    --------
    weighted_emittance: float
        beam emittance
    """

    try:
        w_x = np.mean(x)
        w_ux = np.mean(ux)
        z_array = np.arange(np.shape(x)[0])
        selected_array = np.compress(w != 0., z_array )
        nz_w = np.take(w, selected_array)
        xux = np.sum(x*ux)/(np.shape(x)[0])
        variance_x = np.var(x)
        variance_ux = np.var(ux)
        covariance_xux = xux - w_x*w_ux
        xuxw = [[variance_x,covariance_xux],[covariance_xux,variance_ux]]
        weighted_emittance = np.sqrt(np.linalg.det(xuxw))

        if math.isnan(weighted_emittance):
            weighted_emittance = 0.0

    except ZeroDivisionError:
        weighted_emittance = 0

    return weighted_emittance
