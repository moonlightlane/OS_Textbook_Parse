# -*- coding: utf-8 -*-
"""
Created on Fri Mar 17 10:53:30 2017

@author: jack
"""
import sys
sys.path.insert(0, '/home/jack/Documents/openstaxTextbook/API')
import Textbook as tb

BioText = tb.Textbook('biology', load=False)
BioText.to_csv()