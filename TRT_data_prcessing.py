import numpy
import numpy as np
import matplotlib
from matplotlib import pyplot as plt

fver = "1Q_220A"
dir = "d:\\Your files\\Sanin\\Documents\\2024\\TRT project\\COMSOL\\"
fname = dir + "Beam_Data_" + fver + ".txt"
data = np.loadtxt(fname, dtype=float, comments='%', delimiter=None, skiprows=0)
#print(data)

x = data[:, 1]
y = data[:, 2]
z = data[:, 3]
c = data[:, 7]

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
area = np.pi * 1.4 * 1.4 / 4. #[cm^2]
beamlet_current = curr_dens * area / 1000. #[A]
energy = 120.e3  # [eV]
zmin = 5779.
zmax = zmin + 1100.
index = np.where((z > zmin) & (z < zmax))
#index = np.where(c == 1)

x = x[index]
y = y[index]
z = z[index]

r = np.sqrt(x*x + y*y)
#print(min(r), max(r))
cf = x/r
sf = y/r
#y2 = np.pi * diam * cf[index]
#y2 = np.pi * radius * cf
y2 = radius * numpy.arccos(cf)
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
print("Bin area", bin_area, "[cm^2]")
norm = beamlet_current / n_particles * energy / bin_area # [W/cm^2]
print("Per particle", beamlet_current / n_particles * energy, "[W]")
print("Norm", norm, '[W/cm^2/particle]')

dens, _, _ = np.histogram2d(x, y, bins=bins)
print("Max particles", np.max(dens))
dens1 = dens.T * norm
print("Max density", np.max(dens1), '[W/cm^2]')

fig, ax = plt.subplots()

im = ax.imshow(dens1, cmap=matplotlib.cm.RdBu, vmin=0.0, vmax=np.max(dens1), extent=[np.min(x), np.max(x), -np.pi * radius, np.pi * radius])
#im.set_interpolation('bilinear')
im.set_interpolation('bicubic')

cb = fig.colorbar(im, ax=ax)

ax.set_title("Deposited Power Density [W/cm^2]", fontsize=14)
plt.xlabel("Z, mm", fontsize=14)
plt.ylabel("mm", fontsize=14)

ax.set_ylim((-np.pi * radius, np.pi * radius))
ax.set_xlim((np.min(x), np.max(x)))
#ax.scatter(x, y, marker='.', s=0.2, linewidths=0.1, color='g')
#ax.plot((400, 400), (600, -600))

x1 = np.linspace(np.min(x), np.max(x), bins)
y1 = np.linspace(np.min(y), np.max(y), bins)*np.pi
plt.contour(x1, y1, dens1, levels=[1000])

pfname = dir + "Beam_Data_" + fver + ".png"

pass
fig.savefig(pfname)
