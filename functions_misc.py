import os
import numpy as np
import rht, RHT_tools
import astropy.wcs as wcs
from astropy.io import fits
from PyAstronomy import pyasl
from pytpm import tpm, convert
from astropy import units as u
import matplotlib.pyplot as plt
import montage_wrapper as montage
from scipy import signal, spatial
from reproject import reproject_interp
from astropy.coordinates import SkyCoord

from matplotlib import rc
rc("text", usetex=True)

def fconvolve(oldres_FWHM,newres_FWHM,data,header):
	'''
	Convolves data from oldres to newres using standard FFT convolution.
	
	oldres : native resolution in arcminutes (FWHM)
	newres : desired resolution in arcminutes (FWHM)
	data   : data to be convolved
	header : FITS header for data
	'''
	
	# convert FWHM to standard deviations
	oldres_sigma = oldres_FWHM/(2.*np.sqrt(2.*np.log(2.)))
	newres_sigma = newres_FWHM/(2.*np.sqrt(2.*np.log(2.)))
	# construct kernel
	kernel_arcmin = np.sqrt(newres_sigma**2.-oldres_sigma**2.) # convolution theorem
	pixelsize     = header["CDELT2"]*60.                       # in arcminutes
	kernelsize    = kernel_arcmin/pixelsize                    # in pixels
	data_size_x   = data.shape[0]
	data_size_y   = data.shape[1]
	kernel_x      = signal.gaussian(data_size_x,kernelsize)
	kernel_y      = signal.gaussian(data_size_y,kernelsize)
	kernel        = np.outer(kernel_x,kernel_y)
	# normalize convolution kernel
	kernel_norm   = kernel/np.sum(kernel)
	
	# convolve data using FFT
	data_smoothed = signal.fftconvolve(data,kernel_norm,mode="same")
	
	return data_smoothed

def fmask_snr(data,noise,snr):
	'''
	Creates a mask used to clip data based on SNR level.
	
	Inputs
	data  : data to be clipped
	noise : noise level in same units as data input
	snr   : SNR used for data clipping
	
	Outputs
	mask         : bitmask used for data clipping
	data_cleaned : masked data
	'''
	
	# calculate data SNR
	data_snr      = data/noise
	
	# create mask
	mask          = np.ones(shape=data.shape) # initialize mask
	low_snr       = np.where(data_snr<snr)    # find SNR less than input requirement
	mask[low_snr] = np.nan                    # set low SNR to nan
	
	# mask data
	data_clean    = data * mask
	
	return (mask,data_clean)

def fmaskinterp(image,mask):
	'''
	Masks and interpolates an image.

	Inputs
	image : 2D array
	mask  : 2D array of the same size as image whose masked values for invalid pixels are NaNs
	'''

	# create pixel grid
	x = np.arange(0, image.shape[1])
	y = np.arange(0, image.shape[0])
	xx, yy = np.meshgrid(x,y)

	# create boolean mask for invalid numbers
	mask_invalid = np.isnan(mask)

	#get only the valid values
	x1        = xx[~mask_invalid]
	y1        = yy[~mask_invalid]
	image_new = image[~mask_invalid]

	# interpolate 
	image_interp = interpolate.griddata((x1, y1), image_new.ravel(),(xx, yy),method="cubic")

	return image_interp

def fmaptheta_halfpolar_to_halfpolar(angles,deg=False):
	'''
	Maps angles from [-pi/2,pi/2) to [0,pi) or from [-90,90) to [0,180).

	Input
	angles : array of angles to be mapped
	deg    : boolean which specifies units of input angles (default unit is radian)
	'''

	if deg==False:
		# map angles within [pi,2*pi) to [0,pi)
		angles += np.pi/2.
	elif deg==True:
		# map angles within [-90,90) to [0,180)
		angles += 90.

	return angles

def fmaptheta_halfpolar(angles,deg=False):
	'''
	Maps angles from [0,2*pi) to [0,pi) or from [0,360) to [0,180).

	Input
	angles : array of angles to be mapped
	deg    : boolean which specifies units of input angles (default unit is radian)
	'''

	if deg==False:
		# map angles within [pi,2*pi) to [0,pi)
		angles[(angles>=1.) & (angles!=2.)] -= 1.
		# map 2*pi to 0
		angles[angles==2.] -= 2.
	elif deg==True:
		# map angles within [180,360) to [0,180)
		angles[(angles>=180.) & (angles!=360.)] -= 180.
		# map 360 to 0
		angles[angles==360.] -= 360.

	return angles

def fgradient(x):
	'''
	Constructs the spatial gradient.
	
	x : 2-dimensional input map
	'''
	
	# compute spatial gradients
	grad_xy = np.gradient(x)
	
	# define components of spatial gradient
	grad_x = grad_xy[0]
	grad_y = grad_xy[1]
	
	# compute total spatial gradient map
	grad = np.sqrt(grad_x**2. + grad_y**2.)
	
	return grad
