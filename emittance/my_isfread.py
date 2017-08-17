#!/usr/bin/env python
#coding: utf-8

""" Python script to read data from binary ".ISF" file from TDS series Tektronix Oscilloscope. 
SCRIPT:
=======
It can be run as an script from the command line converting the ISF file into a
two columns ASCII file: 
    $python isfread.py blablabla.isf > outputfile.dat
PYTHON MODULE: 
==============
This module contains the function isfread which expect the name of the ISF file 
an unique input argument and retrieve a tuple with the x-y columns and a 
dictionary with the head information.
----------------------------------------------------------------------------
About ISF files and this code
=============================
This code is base on the similar code for Matlab isfread.m from John 
Lipp [Lipp]. Information on ISF-file is detailed in the Tektronix "Programmer 
Manual" [TekMan]. 
References:
[Lipp] John Lipp - isfread.m matlab code.
            www.mathworks.com/matlabcentral/fileexchange/6247
[TekMan] Tektronix Manuals, "Programmer Manual. TDS3000, TDS3000B, and  
            TDS3000C Series Digital Phosphor Oscilloscopes", 071-0381-03.
            www.tektronix.com
---------------------------------------------------------------------------
Contact: Gustavo Pasquevich, Universidad Nacional de La Plata - Argentina
         gpasquev@fisica.unlp.edu.ar
                                                                         """

import struct

__version__= '0.3'  
__author__= 'Gustavo Pasquevich (2011)'
__email__= 'gpasquev@fisica.unlp.edu.ar'

def _cmp(a, b):
    """Python 3 replacement for Python 2 cmp function."""
    return (a > b) - (a < b)

def my_isfread(filename):
    """ Read isf file and return x y and head information.
    
    input: 
        String with the ISF file name.
    output:
        Returns a tuple of three elements:
        x - list with the x values 
        y - list with the y values
        head - dictionary with the header information stored in the file."""

    FID = open(filename,'rb')

    hdata = FID.read(511);		# read first 511 bytes

    # Subroutines used to extract information from the head --------------------    
    def getnum(string,tag):
        """ Look into the string for the tag and extract the consequent number"""
        n1=string.find(tag)
        n2=string.find(b';',n1)
        
        s2=string[n1+len(tag):n2]    
        j=s2.find(b'.')
        if j==-1:
            return int(string[n1+len(tag):n2])
        else:
            return float(string[n1+len(tag):n2])

    def getstr(string,tag):
        """ Look into the string for the tag and extract the consequent string"""
        n1=string.find(tag)
        n2=string.find(b';',n1)
        return string[n1+len(tag):n2].lstrip()    

    def getquotedstr(string,tag):
        """ Look into the string for the tag and extract the consequent quoted 
        string"""
        n1=string.find(tag)
        n2=string.find(b'"',n1+1)
        n3=string.find(b'"',n2+1)
        return string[n2+1:n3]    
    #---------------------------------------------------------------------------

    head={'bytenum': getnum(hdata,b'BYT_NR'),
            'bitnum':  getnum(hdata,b'BIT_NR'),
            'encoding':  getstr(hdata,b'ENCDG'),
            'binformat': getstr(hdata,b'BN_FMT'),
            'byteorder': getstr(hdata,b'BYT_OR'),
            'wfid': getquotedstr(hdata,b'WFID'),
            'pointformat': getstr(hdata,b'PT_FMT'),
            'xunit': getquotedstr(hdata,b'XUNIT'),
            'yunit': getquotedstr(hdata,b'YUNIT'),
            'xzero': getnum(hdata,b'XZERO'),
            'xincr': getnum(hdata,b'XINCR'),
            'ptoff': getnum(hdata,b'PT_OFF'),
            'ymult': getnum(hdata,b'YMULT'),
            'yzero': getnum(hdata,b'YZERO'),
            'yoff': getnum(hdata,b'YOFF'),
            'npts': getnum(hdata,b'NR_PT')}

    # The only cases that this code (at this moment) not take into account.
    if ((head['bytenum'] != 2) or (head['bitnum'] != 16) or 
    _cmp(head['encoding'],b'BIN') or _cmp(head['binformat'],b'RI') or 
    _cmp(head['pointformat'],b'Y')):
        FID.close()
        print ('Unable to process IFS file.')
         
    # Reading the <Block> part corresponding to the "CURVe" command [TekMan]. 
    # <Block> = ":CURVE #<x><yy..y><data>"
    # <x> number of bytes defining <yy..y>
    # <yy..y> number of bytes to "transfer"/read in the data part.
    # <data>: the data in binary
    # 
    # Comment: It should be that: NR_PT times BYT_NR = <yy..y> 
  
    # Skipping the #<x><yy...y> part of the <Block> bytes
    ii = hdata.find(b':CURVE #')    
    FID.seek(ii+8)			
    skip = int(FID.read(1)) 
    n1 =  int(FID.read(skip))

    # information from the head needed to read and to convert the data
    npts = head['npts']
    yzero= head['yzero']
    ymult= head['ymult']
    xzero= head['xzero']
    xincr= head['xincr']
    ptoff= head['ptoff']
    yoff = head['yoff']
    
    dict_endian = {             # Dictionary to converts significant bit infor-  
               b'MSB': '>',      # mation to struct module definitions.
               b'LSB': '<' 
             }
    fmt = dict_endian[head['byteorder']] + str(npts) + 'h'
    n2=struct.calcsize(fmt)

    # "n1" is the number of bytes to be red directly from Tek-ISF-file.
    # Meanwhile "n2" is the number of bytes to be red calculated through:
    #                    NumOfPoints x BytePerPoint 
    if n1 != n2:  
        print ("WARNING: Something is not going as is was planned!!!")

    string_data=FID.read(n2)
    data=struct.unpack(fmt,string_data)

    # Absolute values of data obtained as is defined in [Tek-Man] WFMPre:PT_Fmt 
    # command description.  
    v=[yzero + ymult*(y-yoff) for y in data]
    x=[xzero + xincr*(i-ptoff) for i in range(npts)]

    FID.close()
    return x,v,head
    
if __name__ == "__main__":
    #filein = sys.argv[1]
    filein = 'd:\\eclipse\\workspace\\PyTest1\\test\\4\\TEK00001.isf'
    x,v,head = my_isfread(filein)
    #import isfread
    #x,v,head = isfread.isfread(filein)

    print (head)

    for i in range(len(x)):
        print ('%g %g'%(x[i],v[i]))

    import matplotlib.pyplot as plt
    plt.plot(x,v)
    plt.plot((min(x),max(x)),(0.0,0.0),)
    plt.show()

