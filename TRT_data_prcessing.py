import numpy
import numpy as np
import matplotlib
from matplotlib import pyplot as plt

fver = "110A"
dir = "d:\\Your files\\Sanin\\Documents\\2024\\TRT project\\COMSOL\\"
fname = dir + "Beam_Data_" + fver + ".txt"
data = np.loadtxt(fname, dtype=float, comments='%', delimiter=None, skiprows=0)
#print(data)

x = data[:, 1]
y = data[:, 2]
z = data[:, 3]
c = data[:, 4]

plt.rcParams["figure.figsize"] = [7.00, 7.00]
plt.rcParams["figure.autolayout"] = True
#fig = plt.figure()
#ax = fig.add_subplot(111, projection='3d')
#ax.scatter(x, y, z, c=c, alpha=1)
#plt.show()

diam = 400.0 # [mm]
radius = diam / 2.
n_particles = 500.
curr_dens = 35.0 # [mA/cm^2]
energy = 120.e3  # [eV]
zmin = 5779.
zmax = zmin + 600.
index = np.where((z >= zmin) & (z <= zmax))

r = np.sqrt(x*x + y*y)
sf = x/r
cf = y/r
#y2 = np.pi * diam * cf[index]
#y2 = np.pi * radius * cf
y2 = np.pi * radius * numpy.arccos(sf)
#x2 = z[index] - zmin
x2 = z - zmin

zmax = z.max()
#ax = fig.add_subplot(111)
#ax.scatter([x2, x2], [y2, -y2])
#plt.show()

x = np.concatenate((x2, x2))
y = np.concatenate((y2, -y2))

bins = 20
bin_area = (np.max(x) - np.min(x))/bins * (np.max(y) - np.min(y))/bins * 1e-2 # [cm^2]
norm = curr_dens / 1000.0 / n_particles * energy / bin_area # [W/cm^2]

dens, _, _ = np.histogram2d(np.concatenate((x2, x2)), np.concatenate((y2, -y2)), bins=20)
dens = dens.T * norm

fig, ax = plt.subplots()

im = ax.imshow(dens, cmap=matplotlib.cm.RdBu, vmin=0.0, vmax=np.max(dens), extent=[0, zmax - zmin, 0, np.pi * radius])
#im.set_interpolation('bilinear')
im.set_interpolation('bicubic')

cb = fig.colorbar(im, ax=ax)

pfname = dir + "Beam_Data_" + fver + ".png"

fig.savefig(pfname)
