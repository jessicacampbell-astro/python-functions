import sys
import aplpy
import numpy as np
import astropy.wcs as wcs
from astropy.io import fits
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

def fPI(Q,U):
	'''
	Coomputes the polarized intensity.
	
	Input
	Q  : Stokes Q map
	U  : Stokes U map
	
	Output
	PI : polarized intensity
	'''
	
	# compute polarized intensity
	PI = np.sqrt(Q**2.+U**2.)
	
	return PI

def fPI_debiased(Q,U,Q_std,U_std):
	'''
	Compute the de-biased polarized intensity.
	
	Input
	Q     : Stokes Q map
	U     : Stokes U map
	Q_std : standard deviation of Stokes Q noise
	U_std : standard deviation of Stokes U noise

	Output
	PI_debiased : debiased polarized intensity
	'''

	# compute effective Q/U noise standard deviation
	std_QU = np.sqrt(Q_std**2. + U_std**2.)

	# compute polarized intensity
	PI = np.sqrt(Q**2.+U**2.)
	# compute de-biased polarized intensity
	PI_debiased = PI * np.sqrt( 1. - (std_QU/PI)**2. )
	
	return PI_debiased

def fpolgrad(Q,U):
	'''
	Computes the polarization gradient.
	See Equation 1 in Gaensler et al. (2011).
	
	Input
	Q : Stokes Q map
	U : Stokes U map

	Output
	polgrad : polarization gradient
	'''
	
	# compute Stokes spatial gradients
	Q_grad_x,Q_grad_y = np.gradient(Q)
	U_grad_x,U_grad_y = np.gradient(U)
	
	# compute spatial polarization gradient
	polgrad  = np.sqrt(Q_grad_x**2.+Q_grad_y**2.+U_grad_x**2.+U_grad_y**2.)
	
	return polgrad

def fpolgradnorm(Q,U):
	'''
	Computes the normalized polarization gradient.
	See Iacobelli et al. (2014).
	
	Input
	Q : Stokes Q map
	U : Stokes U map
	
	Output
	polgrad_norm : normalized polarization gradient
	'''
	
	# compute Stokes spatial gradients
	Q_grad_x,Q_grad_y = np.gradient(Q)
	U_grad_x,U_grad_y = np.gradient(U)
	
	# compute spatial polarization gradient
	polgrad  = np.sqrt(Q_grad_x**2.+Q_grad_y**2.+U_grad_x**2.+U_grad_y**2.)
	
	# compute the polarized intensity
	P = np.sqrt(Q**2.+U**2.)
	
	# compute normalized polarization gradient
	polgrad_norm = polgrad/P
	
	return polgrad_norm

def fpolgrad_crossterms(Q,U):
	'''
	Computes the polarization gradient with cross-terms.
	See Equation 15 in Herron et al. (2018).
	
	Input
	Q : Stokes Q data
	U : Stokes U data

	Output
	polgrad : polarization gradient with cross-terms
	'''
	
	# compute Stokes spatial gradients
	Q_grad_x,Q_grad_y = np.gradient(Q)
	U_grad_x,U_grad_y = np.gradient(U)
	
	# compute spatial polarization gradient
	a       = Q_grad_x**2.+Q_grad_y**2.+U_grad_x**2.+U_grad_y**2.
	b       = a**2. - 4.*(Q_grad_x*U_grad_y - Q_grad_y*U_grad_x)**2.
	
	# compute polarization gradient
	polgrad = np.sqrt(0.5*a + 0.5*np.sqrt(b))
	
	return polgrad

def fpolgradarg(Q,U,parallel=False,deg=True):
	'''
	Computes the argument of the polarization gradient.
	See the equation in the caption of Figure 2 in Gaensler et al. (2011).
	
	Input
	Q        : Stokes Q data
	U        : Stokes U data
	parallel : if True, compute angle parallel (rather then perpendicular) to polarization gradient structures (default=False)
	deg      : if True, converts the argument to degrees for output

	Output
	polgrad_arg : argument of polarization gradient
	'''
	
	# compute Stokes spatial gradients
	Q_grad_x,Q_grad_y = np.gradient(Q)
	U_grad_x,U_grad_y = np.gradient(U)

	# compute argument of polarization gradient
	a = np.sign(Q_grad_x*Q_grad_y + U_grad_x*U_grad_y)
	b = np.sqrt(Q_grad_y**2.+U_grad_y**2.)
	c = np.sqrt(Q_grad_x**2.+U_grad_x**2.)

	polgrad_arg = np.arctan(a*b/c) # angle measured from the x-axis on [-pi/2,+pi/2] in radians

	if parallel==True:
		# compute argument angle parallel to filaments from North (like the RHT)
		polgrad_arg += np.pi/2. # angle measured from the y-axis on [0,pi] in radians

	if deg==True:
		# convert to degrees
		polgrad_arg = np.degrees(polgrad_arg)

	return polgrad_arg

def fpolgradarg_crossterms(Q,U,parallel=True,deg=True):
	'''
	Computes the argument of the polarization gradint with cross-terms.
	See Equations 13 and 14 in Herron et al. (2018).
	
	Input
	Q        : Stokes Q map
	U        : Stokes U map
	parallel : if True, compute angle parallel (rather then perpendicular) to polarization gradient structures
	deg      : if True, converts to degrees at the end
	
	Output
	polgrad_arg : argument of polarization gradient
	'''
	
	# compute Stokes spatial gradients
	Q_grad_x,Q_grad_y = np.gradient(Q)
	U_grad_x,U_grad_y = np.gradient(U)

	# compute the cos(2*theta) term
	cos2theta_num = -(Q_grad_y**2. - Q_grad_x**2. + U_grad_y**2. - U_grad_x**2.)
	cos2theta_den = np.sqrt((Q_grad_x**2. + Q_grad_y**2. + U_grad_x**2. + U_grad_y**2.)**2. - 4.*(Q_grad_x*U_grad_y - Q_grad_y*U_grad_x)**2.)
	cos2theta     = cos2theta_num/cos2theta_den

	# compute the sin(2*theta) term
	sin2theta_num = 2.*(Q_grad_x*Q_grad_y + U_grad_x*U_grad_y)
	sin2theta_den = np.sqrt((Q_grad_x**2. + Q_grad_y**2. + U_grad_x**2. + U_grad_y**2.)**2. - 4.*(Q_grad_x*U_grad_y - Q_grad_y*U_grad_x)**2.)
	sin2theta     = sin2theta_num/sin2theta_den

	# compute tan(theta)
	tantheta      = sin2theta/(1.+cos2theta)
	# take inverse tan tocompute argument
	polgrad_arg = np.arctan(tantheta) # angle measured from the x-axis on [-pi/2,+pi/2] in radians

	if parallel==True:
		# compute argument angle parallel to filaments from North (like the RHT)
		polgrad_arg += np.pi/2. # angle measures from the y-axis on [0,pi] in radians

	if deg==True:
		# convert to degrees
		polgrad_arg = np.degrees(polgrad_arg)

	return polgrad_arg

def fargmask(angles,min,max):
	'''
	Creates a mask for the argument of polarization gradient based on an input of angle range(s).

	Inputs
	angles : angle map
	min    : minimum of the range of angles to be masked (can be single-valued or a list/array)
	max    : maximum of the range of angles to be masked (can be single-valued or a list/array)

	Output
	mask : a mask the same size as the angle map
	'''

	# initialize mask
	mask = np.ones(shape=angles.shape)

	# fill in mask using input angles
	for i in range(len(min)):
		mask_i              = np.copy(mask)
		min_i               = min[i]
		max_i               = max[i]
		mask_angles         = np.where((angles>=min_i) & (angles<=max_i))
		mask_i[mask_angles] = np.nan
		mask               *=mask_i

	return mask

def fpolgradnorm_crossterms(Q,U):
	'''
	Computes the complete normalized polarization gradient with cross-terms.
	
	Input
	Q : Stokes Q data
	U : Stokes U data

	Output
	polgrad_norm : normalized polarization gradient with cross-terms
	'''
	
	# compute Stokes spatial gradients
	Q_grad_x,Q_grad_y = np.gradient(Q)
	U_grad_x,U_grad_y = np.gradient(U)
	
	# compute spatial polarization gradient
	a       = Q_grad_x**2.+Q_grad_y**2.+U_grad_x**2.+U_grad_y**2.
	b       = a**2. - 4.*(Q_grad_x*U_grad_y - Q_grad_y*U_grad_x)**2.
	polgrad = np.sqrt(0.5*a + 0.5*np.sqrt(b) )
	
	# compute the polarized intensity
	P = np.sqrt(Q**2.+U**2.)
	
	# compute the normalized polarization gradient
	polgrad_norm = polgrad/P
	
	return polgrad_norm

def fpolgrad_rad(Q,U):
	'''
	Computes the radial component of the polarization gradient.
	See Equation 22 in Herron et al. (2018).
	
	Input
	Q : Stokes Q map
	U : Stokes U map

	Output
	polgrad_rad : radial component of the polarization gradient
	'''
	
	# compute Stokes spatial gradients
	Q_grad_x,Q_grad_y = np.gradient(Q)
	U_grad_x,U_grad_y = np.gradient(U)
	
	polgrad_rad_num = (Q*Q_grad_x+U*U_grad_x)**2. + (Q*Q_grad_y+U*U_grad_y)**2.
	polgrad_rad_den = Q**2.+U**2.
	
	# compute radial component of polarization gradient
	polgrad_rad = np.sqrt(polgrad_rad_num/polgrad_rad_den)
	
	return polgrad_rad
    
def fpolgrad_tan(Q,U):
	'''
	Computes the radial component of the polarization gradient.
	See Equation 25 in Herron et al. (2018).
	
	Input
	Q : Stokes Q map
	U : Stokes U map

	Output
	polgrad_tan : tangential component of the polarization gradient
	'''
	
	# compute Stokes spatial gradients
	Q_grad_x,Q_grad_y = np.gradient(Q)
	U_grad_x,U_grad_y = np.gradient(U)
	
	polgrad_tan_num = (Q*U_grad_x+U*Q_grad_x)**2. + (Q*U_grad_y-U*Q_grad_y)**2.
	polgrad_tan_den = Q**2.+U**2.
	
	# compute tangential component of polarization gradient
	polgrad_tan = np.sqrt(polgrad_tan_num/polgrad_tan_den)
	
	return polgrad_tan

def fplotvectors(imagefile,anglefile,deltapix=5,scale=2.,angleunit="deg",coords="wcs",figsize=(20,10)):
	'''
	Plots an image with pseudovectors.
	
	Input
	imagefile : image directory
	anglefile : angle map directory
	deltapix  : the spacing of image pixels to draw pseudovectors
	scale     : a scalefactor for the length of the pseudovectors
	angleunit : the unit of the input angle map (can be deg/degree/degrees or rad/radian/radians)

	Output
	Saves the image in the same directory as imagefile with "_angles.pdf" as the filename extension
	'''

	degree_units   = ["deg","degree","degrees"]
	radian_units   = ["rad","radian","radians"]

	wcs_units      = ["wcs","WCS","world"]
	pixel_units    = ["pix","pixel","pixels"]

	if coords in wcs_units:
		# extract image data and WCS header
		image,header   = fits.getdata(imagefile,header=True)
		NAXIS1,NAXIS2  = header["NAXIS1"],header["NAXIS2"]
		w              = wcs.WCS(header)
	elif coords in pixel_units:
		# extract image data
		image          = fits.getdata(imagefile)
		NAXIS2,NAXIS1  = image.shape
	# extract angle data
	angles         = fits.getdata(anglefile)

	linelist_pix   = []
	linelist_wcs   = []

	for y in range(0,NAXIS2,deltapix):
		# iterate through y pixels
		for x in range(0,NAXIS1,deltapix):
			# iterate through x pixels
			image_xy = image[y,x]
			if np.isnan(image_xy)==False:
				# do not plot angle if image data is NaN
				if angleunit in degree_units:
					# convert angles to radians
					angles_deg = np.copy(angles)
					angles_rad = np.radians(angles)
				elif angleunit in radian_units:
					# convert angles to degrees
					angles_deg = np.degrees(angles)
					angles_rad = np.copy(angles)
				else:
					# raise error
					print "Input angleunit is not defined."
					sys.exit()
				angle_rad = angles_rad[y,x]
				angle_deg = angles_deg[y,x]
				# create line segment in pixel coordinates
				(x1_pix,y1_pix) = (x-scale*np.cos(angle_rad),y-scale*np.sin(angle_rad))
				(x2_pix,y2_pix) = (x+scale*np.cos(angle_rad),y+scale*np.sin(angle_rad))
				line_pix        = np.array([(x1_pix,y1_pix),(x2_pix,y2_pix)])
				if coords in pixel_units:
					linelist_pix.append(line_pix)
				elif coords in wcs_units:
					# create line segment in WCS coordinates (units of degrees)
					x1_wcs,y1_wcs   = w.wcs_pix2world(x1_pix,y1_pix,0)
					x2_wcs,y2_wcs   = w.wcs_pix2world(x2_pix,y2_pix,0)
					line_wcs        = np.array([(x1_wcs,x2_wcs),(y1_wcs,y2_wcs)])
					linelist_wcs.append(line_wcs)

	# plot figure
	if coords in pixel_units:
		fig = plt.figure(figsize=figsize)
		ax = fig.add_subplot(111)
		im = ax.imshow(image,vmax=0.05,cmap="Greys_r",origin="lower")
		plt.xlabel("pixels")
		plt.ylabel("pixels")
		lc = LineCollection(linelist_pix,color="red")
		plt.gca().add_collection(lc)
		plt.colorbar(im, ax=ax, orientation="vertical")
		plt.show()
		plt.savefig(imagefile.split(".fits")[0]+"_angles.pdf")

	elif coords in wcs_units:
		fig = plt.figure(figsize=figsize)
		f = aplpy.FITSFigure(imagefile,figure=fig)
		f.show_grayscale()
		f.show_lines(linelist_wcs,layer="vectors",color="red")
		f.add_scalebar(1.)
		f.scalebar.set_corner("top left")
		f.scalebar.set_color("white")
		f.scalebar.set_label("1 degree")
		f.add_colorbar()
		fig.canvas.draw()
		f.save(imagefile.split(".fits")[0]+"_angles.pdf")
