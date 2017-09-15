# coding: utf-8
'''
Created on 27 June 2017.

@author: Sanin
'''
from __future__ import print_function
from datetime import datetime

def printl(*args, **kwargs):
    # static variables
    if not hasattr(printl, "start"):
        printl.start = True  # it doesn't exist yet, so initialize it
    if not hasattr(printl, "fileName"):
        printl.fileName = 'logfile.log'
    if not hasattr(printl, "widget"):
        printl.widget = None
    
    if "widget" in kwargs:
        printl.widget = kwargs["widget"]

    if "fileName" in kwargs:
        printl.fileName = kwargs["fileName"]
 
    if "stamp" in kwargs:
        stamp = kwargs["stamp"]
    else:
        stamp = True

    if "delimiter" in kwargs:
        delim = str(kwargs["delimiter"])
    else:
        delim = " "
    
    if "print" in kwargs:
        prf = bool(kwargs["print"])
    else:
        prf = True

    if "endline" in kwargs:
        cr = str(kwargs["endline"])
    else:
        cr = '\n'

    if "write" in kwargs:
        wrf = bool(kwargs["write"])
    else:
        wrf = True

    now = datetime.now()    
    strnow = datetime.strftime(now, "%Y.%m.%d %H:%M:%S")
    
    f = open(printl.fileName, 'a')

    if printl.start:
        f.write('\nLog started at %s\n'%strnow)
        printl.start = False
    
    strout = ''
            
    for a in args :
        strout += delim
        strout += str(a)

    if prf:
        print(strout + cr, end='')

    if stamp :
        strout = strnow + delim + strout

    if wrf:
        f.write(strout + cr)
    f.close()

    if printl.widget is not None:
        printl.widget.appendPlainText(strout)
