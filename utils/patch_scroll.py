#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Patch main.py to use ScrollableFrame in large tabs

import sys
import os
import tkinter as tk
from tkinter import ttk, scrolledtext

from utils.scrollable import ScrollableFrame

# Monkey-patch helper functions to wrap tab parents

def wrap_tab(parent):
    scroll = ScrollableFrame(parent)
    scroll.pack(fill=tk.BOTH, expand=True)
    return scroll.container
