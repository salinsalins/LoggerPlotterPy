#s='s=%r;print(s%%s)';print(s%s)


file = "d:\\Your files\\Sanin\\Documents\\2022\\Мероприятие 1_1_4\\Отчет декабрь 2022\\Плотность газа в тракте.txt"
with open(file) as data:
    buf = data.readlines()
x = []
y = []
for line in buf:
    v = line.split('\t')
    z = []
    for f in v:
        if f:
            try:
                z.append(float(f.replace(',','.')))
            except:
                pass
    try:
        v1 = z[0]
        v2 = z[1]
        x.append(v1)
        y.append(v2)
    except:
        pass
    try:
        v1 = z[2]
        v2 = z[3]
        x.append(v1)
        y.append(v2)
    except:
        pass
import numpy as np

x = np.array(x)
y = np.array(y)
index = np.argsort(x)

import matplotlib.pyplot as plt

xs = x[index]
ys = y[index]

# fig.savefig("test.png")
# plt.show()

sigma = xs.copy()
sigma[xs <= 50] = 3.5e-16
i = np.logical_and(xs > 50, xs < 260)
sigma[i] = 3.5e-16 - xs[i]/250.*2.4e-16
sigma[xs >= 260] = 1.1e-16


xmin = xs.min()
print(-255-xmin, -xmin, 270-xmin)

from scipy import integrate
nl = integrate.cumtrapz(ys, xs, initial=0)
nsl = integrate.cumtrapz(ys*sigma, xs, initial=0) * 1e-6

fig, ax = plt.subplots()
# ax.plot(xs, ys)

ax.set(xlabel='Расстояние от источника [см]', ylabel='Обдирка пучка Н-',
       title='Обдирка пучка Н-')
ax.grid()

ax.set_facecolor("white")
#ax.set_xticks([0., .5*np.pi, np.pi, 1.5*np.pi, 2*np.pi])
# plt.plot(xs, sigma, 'r')
# plt.plot(xs, nl, 'y')
plt.plot(xs-xs.min(), 1.0 - np.exp(-nsl), 'r')
plt.show()