import numpy as np

from fig_viewer.core.figplot import figplot


if __name__ == "__main__":

    x = np.linspace(0, 10, 65*8)
    y = np.sin(x)
    # window.plot(x, y)
    # window.plot(x, y, name="0")


    # window.plot(2*y, name="1")

    fig1 = figplot.figure()
    fig1.subplot(1, 1)
    fig1.plot(x, y, linewidth=5, color='r', linestyle='--', title="test", xlabel='s', ylabel='t', hold=True)
    fig1.subplot(1, 2)
    fig1.plot(x, -y+1, linewidth=5, color='b', linestyle='--', title="test", xlabel='s', ylabel='t', xlim=(0.2, 0.9))
    fig3 = figplot.figure()
    fig3.plot(3*x)

    # figplot.pause()
    # fig1.xlim(1, 2)
    fig2 = figplot.figure()
    fig2.plot(2*y, hold=True, label="2")
    fig2.plot(2*x, hold=True)
    # fig2.legend(["2", "x"])
    fig2.legend()
    figplot.show()

    figplot.close_all()



